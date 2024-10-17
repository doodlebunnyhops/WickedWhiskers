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
import context_menu.player as player
from db_utils import initialize_database, get_game_join_msg_settings,is_player_active,create_player_data
from cogs.mod import Mod
from cogs.game import Game
from utils.messages import MessageLoader
import settings
# import context_menu
from modals.player import Treat

print(discord.__version__)
print(discord.__file__)

# logger.basicConfig(level=logger.DEBUG)
logger = settings.logging.getLogger("bot")

#For development as commands sync faster for guilds than globally

class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if settings.GUILDS_ID is not None:
            self.guild_id = settings.GUILDS_ID
        else:
            self.guild_id = None
        # self.tree = discord.app_commands.CommandTree(self)
        self.message_loader = None

    async def setup_hook(self):
        self.guild_id = settings.GUILDS_ID
        print("Initializing database...")
        initialize_database()  

        
        print("Loading spooky messages...")
        self.message_loader = MessageLoader('utils/messages.json')

        #Set Context Menus callback
        join_cm = app_commands.ContextMenu(name="Join Game", callback=player.join)
        trick_cm = app_commands.ContextMenu(name="Trick Player", callback=player.trick)
        bucket_cm = app_commands.ContextMenu(name="Check Bucket", callback=player.bucket)

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
        if self.guild_id is None:
            self.tree.add_command(Mod.cmds_group,override=True)
            self.tree.add_command(Game.game_group,override=True)
            self.tree.add_command(join_cm,override=True)
            self.tree.add_command(trick_cm,override=True)
            self.tree.add_command(bucket_cm,override=True)
            self.tree.add_command(treat_modal,override=True)
            await self.load_extension("cogs.player")
            # await self.load_extension("cogs.game")
        else:
            self.tree.add_command(Mod.cmds_group,guild=self.guild_id,override=True)
            self.tree.add_command(Game.game_group,guild=self.guild_id,override=True)
            self.tree.add_command(join_cm,guild=self.guild_id,override=True)
            self.tree.add_command(trick_cm,guild=self.guild_id,override=True)
            self.tree.add_command(bucket_cm,guild=self.guild_id,override=True)
            self.tree.add_command(treat_modal,guild=self.guild_id,override=True)
            await self.load_extension("cogs.player")
            # await self.load_extension("cogs.game")
        
        print("Syncing tree...")
        try:
            # Sync the commands
            if self.guild_id is None:
                # self.tree.copy_global_to()
                synced = await self.tree.sync()
                logger.info(f"Attempting to sync commands globally")
            else:
                self.tree.copy_global_to(guild=self.guild_id)
                synced = await self.tree.sync(guild=self.guild_id)
                logger.info(f"Attempting to sync commands for guild ID: {self.guild_id.id}")

                # Log detailed info about synced commands
                logger.info(f"Successfully synced {len(synced)} commands for guild ID: {self.guild_id.id}")

            for i, command in enumerate(synced):
                is_last_command = i == len(synced) - 1
                log_command(command, is_last=is_last_command)

        except Exception as e:
            logger.error(f"Error syncing commands for guild ID {self.guild_id}: {str(e)}")

    async def on_ready(self):
        print(f'Logged in as {self.user} and bot is ready!')


def log_command(command, depth=0, parent_cmd=None, is_last=False, parent_has_args=False):
    if depth > 0:
        indent = "│   " * (depth - 1) + ("└── " if is_last else "├── ")
    else:
        indent = ""

    full_command = f"{parent_cmd} {command.name}" if parent_cmd else f"/{command.name}"

    # Display the command or subcommand description
    if depth == 0:
        logger.info(f"{full_command} : {command.description}")
    else:
        logger.info(f"{indent}{command.name} : {command.description}")

    # Handle subcommands and options
    if hasattr(command, 'options') and command.options:
        subcommand_found = False
        for i, option in enumerate(command.options):
            is_last_option = i == len(command.options) - 1
            if option.type in (discord.AppCommandOptionType.subcommand, discord.AppCommandOptionType.subcommand_group):
                log_command(option, depth + 1, full_command, is_last=is_last_option, parent_has_args=False)
                subcommand_found = True

        # Display options with properly connected lines if no subcommands were found
        if not subcommand_found:
            args_indent = "│   " * depth if not is_last else "    " * depth
            logger.info(f"{args_indent}Arguments:")
            for i, opt in enumerate(command.options):
                is_last_arg = i == len(command.options) - 1
                opt_indent = "│   " * depth + ("└── " if is_last_arg else "├── ")
                
                # Log option name, description, and the type of option
                opt_type = opt.type.name if hasattr(opt.type, 'name') else str(opt.type)
                logger.info(f"{opt_indent}{opt.name} : {opt.description} (Type: {opt_type})")


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