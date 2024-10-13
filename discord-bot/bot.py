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
from discord import app_commands
import logging
import db_utils
from cogs.server import RoleAccess
from cogs.player import PlayerCommands
from utils.messages import MessageLoader

print(discord.__version__)
print(discord.__file__)

logging.basicConfig(level=logging.DEBUG)

#For development as commands sync faster for guilds than globally
guild_ID = os.getenv("DISCORD_GUILD_ID")

class MyBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.guild_id = guild_ID  
        self.tree = discord.app_commands.CommandTree(self)
        self.message_loader = None # IT WAS YOU!!!!

    async def setup_hook(self):
        guild = discord.Object(id=self.guild_id)
        print("Initializing database...")
        db_utils.initialize_database()  

        
        print("Loading spooky messages...")
        self.message_loader = MessageLoader('utils/messages.json')
        
        # Load all cogs
        print("Loading group commands...")
        #the additional options were the trick to force guild update
        self.tree.add_command(RoleAccess.server,guild=guild,override=True)

        # Player commands are not playing well with subcommands, I suspect due to several limitations
        # documented in discord.py's docs, nothing outright that I found that correlates to what I've 
        # seen but enough that I'm going to strip subcommands from player to top level.
     
        # self.tree.add_command(PlayerCommands.player,guild=guild,override=True)
        
        print("Syncing tree...")
        try:
            # Sync the commands
            logging.info(f"Attempting to sync commands for guild ID: {guild.id}")
            synced = await self.tree.sync(guild=guild)
            # self.tree._guild_commands.update() #for global also need to remove guild specific on add_command.
            # synced = await self.tree.sync()

            # Log detailed info about synced commands
            logging.info(f"Successfully synced {len(synced)} commands for guild ID: {guild_ID}")
            for command in synced:
                logging.info(f"Command synced: {command.name} - {command.description}")
                if hasattr(command, 'options'):
                    for option in command.options:
                        logging.info(f" - Option: {option.name} ({option.type}) - {option.description}")

        except Exception as e:
            logging.error(f"Error syncing commands for guild ID {guild_ID}: {str(e)}")

    async def on_ready(self):
        print(f'Logged in as {self.user} and bot is ready!')


# @bot.event
# async def on_raw_reaction_add(payload):
#     # Ensure the event is from a guild
#     if payload.guild_id is None:
#         return

#     guild = bot.get_guild(payload.guild_id)
#     member = guild.get_member(payload.user_id)
#     channel = bot.get_channel(payload.channel_id)
    
#     # Define the emoji that will trigger joining the game
#     join_emoji = '🎃'

#     # Fetch the game invite message ID from the database for the current guild
#     result = db_utils.get_game_join_msg_id(guild.id)

#     if result is None:
#         return  # No invite message ID found, do nothing

#     game_invite_message_id = result[0]  # Get the invite message ID

#     # Check if the reaction is on the correct invite message and is the right emoji
#     if payload.message_id == game_invite_message_id and str(payload.emoji) == join_emoji:
#         player_id = member.id
#         guild_id = guild.id

#         if db_utils.is_player_active(player_id,guild_id):
#             # Player is already in the game
#             await channel.send(f"{member.mention}, you are already in the game! Use /return if you previously opted out.", delete_after=20)
#         else:
#             db_utils.create_player_data(player_id,guild_id)

#             # Welcome the new player
#             await channel.send(f"Welcome {member.mention}! You have joined the candy game with 50 candy. Get ready to trick or treat! 🎃", delete_after=10)


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = MyBot(intents=intents)

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
        logging.info(f"{interaction.user.name} attempted '/{interaction.command.qualified_name}': Error\t{error}")
        if interaction.response.is_done():
            await interaction.followup.send("An error occurred while processing the command.", ephemeral=True)
        else:
            await interaction.response.send_message("An error occurred while processing the command.", ephemeral=True)
        # await utils.post_admin_message(bot, interaction.guild.id, f"An error occurred while processing:\n\tError: {error}.\n\tInvoked by: {interaction.user.name}\n\tAttempted: {interaction.command.name}")
bot_token = os.getenv("DISCORD_BOT_TOKEN")
bot.run(bot_token)