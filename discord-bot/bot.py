# -----------------------------------------------------------------------------
# Author: doodlebunnyhops
# Date: 10-07-2024
# Description: Database Utility to support Discord bot.
# License: This file is part of a project licensed under the MIT License.
# Attribution: If you reuse or modify this code, please attribute the original
# creator, doodlebunnyhops, by referencing the source repository at 
# https://github.com/doodlebunnyhops.
# -----------------------------------------------------------------------------
import discord
from discord import app_commands
import logging
import db_utils
from cogs.server import RoleAccess

print(discord.__version__)
print(discord.__file__)

logging.basicConfig(level=logging.DEBUG)

class MyBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self):
        print("Initializing database...")
        db_utils.initialize_database()  # Initialize database before loading extensions
        
        # Load all cogs
        print("Loading Extensions...")
        # await self.load_extension("cogs.server")
        self.tree.add_command(RoleAccess.server)

        
        print("Syncing tree...")
        await self.tree.sync()  # Sync the commands with the server

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

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    # Check if the error is due to the user missing the 'mod' role
    if isinstance(error, app_commands.MissingRole):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
    elif isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(f"{error}", ephemeral=True)
    else:
        # For any other errors, you can handle them here or raise the default error
        print(f"An error occurred while processing:\n\tError: {error}")
        logging.info(f"{interaction.user.name} attempted '/{interaction.command.qualified_name}': Error\t{error}")
        await interaction.response.send_message("An error occurred while processing the command.", ephemeral=True)
        # await utils.post_admin_message(bot, interaction.guild.id, f"An error occurred while processing:\n\tError: {error}.\n\tInvoked by: {interaction.user.name}\n\tAttempted: {interaction.command.name}")

bot.run('BOT_TOKEN')