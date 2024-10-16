# -----------------------------------------------------------------------------
# Author: doodlebunnyhops
# Date: 10-07-2024
# Description: Database Utility to support Discord bot.
# License: This file is part of a project licensed under the MIT License.
# Attribution: If you reuse or modify this code, please attribute the original
# creator, doodlebunnyhops, by referencing the source repository at 
# https://github.com/doodlebunnyhops.
# -----------------------------------------------------------------------------
import asyncio
import os
import discord
from discord.ext import commands
from discord import app_commands
import context_menu.player
from db_utils import initialize_database, get_game_join_msg_settings,is_player_active,create_player_data
from cogs.mod import Mod
from utils.messages import MessageLoader
import settings
import context_menu
from modals.player import Treat

print(discord.__version__)
print(discord.__file__)

# logger.basicConfig(level=logger.DEBUG)
logger = settings.logging.getLogger("bot")

#For development as commands sync faster for guilds than globally

class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.guild_id = settings.GUILDS_ID
        # self.tree = discord.app_commands.CommandTree(self)
        self.message_loader = None

    async def setup_hook(self):
        self.guild_id = settings.GUILDS_ID
        print("Initializing database...")
        initialize_database()  

        
        print("Loading spooky messages...")
        self.message_loader = MessageLoader('utils/messages.json')

        #Set Context Menus callback
        join_cm = app_commands.ContextMenu(name="Join Game", callback=context_menu.player.join)
        trick_cm = app_commands.ContextMenu(name="Trick Player", callback=context_menu.player.trick)
        # treat_cm = app_commands.ContextMenu(name="Treat Player", callback=context_menu.player.treat)

        @bot.tree.context_menu(name="Treat Player")
        async def treat_modal(interaction: discord.Interaction, user: discord.Member):
            # Show the modal for user input
            modal = Treat(target_user=user)
            await interaction.response.send_modal(modal)
            
        # @self.tree.context_menu(name="Join Game")
        # @checks.must_target_self()
        # async def join(interaction: discord.Interaction, user: discord.Member):
        #     await interaction.response.send_message(f"{user.display_name} you are trying to join!", ephemeral=True)
        
        # Load cogs and cm's
        print("Loading group commands...")
        #the additional options were the trick to force guild update
        self.tree.add_command(Mod.cmds_group,guild=self.guild_id,override=True)
        self.tree.add_command(join_cm,guild=self.guild_id,override=True)
        self.tree.add_command(trick_cm,guild=self.guild_id,override=True)
        self.tree.add_command(treat_modal,guild=self.guild_id,override=True)
        await self.load_extension("cogs.player")
        await self.load_extension("cogs.toggle")
        
        print("Syncing tree...")
        try:
            # Sync the commands
            logger.info(f"Attempting to sync commands for guild ID: {self.guild_id.id}")
            self.tree.copy_global_to(guild=self.guild_id) #this is what loaded in my slash command to the guild i wanted
            synced = await self.tree.sync(guild=self.guild_id)

            # Log detailed info about synced commands
            logger.info(f"Successfully synced {len(synced)} commands for guild ID: {self.guild_id.id}")
            for command in synced:
                logger.info(f"Command synced: {command.name} - {command.description}")
                if hasattr(command, 'options'):
                    for option in command.options:
                        logger.info(f" - Option: {option.name} ({option.type}) - {option.description}")

        except Exception as e:
            logger.error(f"Error syncing commands for guild ID {self.guild_id}: {str(e)}")

    async def on_ready(self):
        print(f'Logged in as {self.user} and bot is ready!')

intents = discord.Intents.all()
# intents = discord.Intents.default()
# intents.message_content = True
# intents.guilds = True
# intents.members = True
# bot = MyBot(intents=intents)
bot = MyBot(command_prefix="!", intents=intents)


@bot.event
async def on_raw_reaction_add(payload):
    try:
        # Ensure the event is from the correct guild and channel
        if payload.guild_id is None:
            return

        guild = bot.get_guild(payload.guild_id)
        channel = bot.get_channel(payload.channel_id)
        member = guild.get_member(payload.user_id)

        join_emoji = '🎃'

        # Fetch the game invite message ID from the database for the current guild
        try:
            result = get_game_join_msg_settings(guild.id)
            if result is None:
                logger.warning(f"No invite message ID found for guild {guild.id}")
                return
        except Exception as e:
            logger.error(f"Error fetching invite message ID: {str(e)}")
            return

        game_invite_message_id = result[0]

        # Check if the reaction is on the correct message and with the right emoji
        if payload.message_id == game_invite_message_id and str(payload.emoji) == join_emoji:
            player_id = member.id
            guild_id = guild.id

            try:
                if is_player_active(player_id, guild_id):
                    await channel.send(f"{member.mention}, you are already in the game! Use `/return` if you previously opted out.", delete_after=15)
                else:
                    # Create new player data
                    try:
                        create_player_data(player_id, guild_id)
                        message = bot.message_loader.get_message(
                            "join", "messages", user=member.mention
                        )
                        await channel.send(message, delete_after=30)
                    except Exception as e:
                        logger.error(f"Error creating player data for {member.id} in guild {guild_id}: {str(e)}")
                        await channel.send(f"Error occurred while adding you to the game, {member.mention}. Please try again later.", delete_after=15)
            except Exception as e:
                logger.error(f"Error checking or adding player for {member.id} in guild {guild_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in on_raw_reaction_add: {str(e)}")


@bot.event
async def on_error(event, *args, **kwargs):
    if isinstance(args[0], discord.HTTPException) and args[0].status == 429:
        # Rate limit encountered
        retry_after = args[0].headers.get("Retry-After")
        if retry_after:
            await asyncio.sleep(int(retry_after) + 1)  # Wait for the suggested time before retrying
        else:
            await asyncio.sleep(5)  # Fallback to a reasonable delay if Retry-After is not provided
    else:
        # Handle errors if they occur
        print(f"An error occurred: {args[0]}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    # Check if the error is due to the user missing the 'mod' role
    if isinstance(error, app_commands.MissingRole):
        if interaction.response.is_done():
            await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
        else:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
    elif isinstance(error, app_commands.CheckFailure):
        if interaction.response.is_done():
            await interaction.followup.send(f"{error}", ephemeral=True)
        else:
            await interaction.response.send_message(f"{error}", ephemeral=True)
    else:
        # For any other errors, you can handle them here or raise the default error
        print(f"An error occurred while processing:\n\tError: {error}")
        logger.info(f"{interaction.user.name} attempted '/{interaction.command.qualified_name}': Error\t{error}")
        if interaction.response.is_done():
            await interaction.followup.send("An error occurred while processing the command.", ephemeral=True)
        else:
            print(f"An error occurred while processing:\n\tError: {error}")
            await interaction.response.send_message("An error occurred while processing the command.", ephemeral=True)
        # await utils.post_admin_message(bot, interaction.guild.id, f"An error occurred while processing:\n\tError: {error}.\n\tInvoked by: {interaction.user.name}\n\tAttempted: {interaction.command.name}")

bot.run(settings.DISCORD_API_SECRET, root_logger=True)