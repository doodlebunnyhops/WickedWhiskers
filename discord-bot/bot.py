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
from discord.ext import commands
from discord import app_commands
import logging
import db_utils

print(discord.__version__)
print(discord.__file__)

logging.basicConfig(level=logging.DEBUG)

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Initialize the database before loading extensions
        db_utils.initialize_database()  # Ensures the database is ready
        # Load all cogs
        await self.load_extension("cogs.server")
        # await self.load_extension("cogs.moderation")
        # Add more cogs as needed

    async def on_ready(self):
        await self.tree.sync()  # Sync the commands with the server
        print(f'Logged in as {self.user}!')

    # Event listener for reaction adds
    # @commands.Cog.listener()  # If inside a cog, otherwise use @bot.event if in bot.py
    # async def on_reaction_add(self, reaction, user):
    #     # Make sure the reaction wasn't added by the bot itself
    #     if user.bot:
    #         return

    #     # Example: Check if the message is a specific message you are tracking
    #     if reaction.message.id == 123456789012345678:  # Replace with your message ID
    #         if str(reaction.emoji) == "🎃":  # Check if the reaction emoji is 🎃
    #             # Example: Add a role to the user
    #             guild = reaction.message.guild
    #             role = discord.utils.get(guild.roles, name="Pumpkin Player")  # Replace with your role name
    #             if role:
    #                 await user.add_roles(role)
    #                 await reaction.message.channel.send(f"{user.name} has been given the {role.name} role!")


bot = MyBot()

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    # Check if the error is due to the user missing the 'mod' role
    if isinstance(error, app_commands.MissingRole):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
    elif isinstance(error, commands.CommandOnCooldown):
        await interaction.response.send_message(f"This command is on cooldown. Try again in {round(error.retry_after, 1)} seconds.", ephemeral=True)
    elif isinstance(error, commands.MissingRequiredArgument):
        await interaction.response.send_message("Missing required arguments. Please provide all necessary information.", ephemeral=True)
    elif isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(f"{error}", ephemeral=True)
    else:
        # For any other errors, you can handle them here or raise the default error
        print(f"An error occurred while processing:\n\tError: {error}")
        logging.info(f"{interaction.user.name} attempted '/{interaction.command.qualified_name}': Error\t{error}")
        await interaction.response.send_message("An error occurred while processing the command.", ephemeral=True)
        # await utils.post_admin_message(bot, interaction.guild.id, f"An error occurred while processing:\n\tError: {error}.\n\tInvoked by: {interaction.user.name}\n\tAttempted: {interaction.command.name}")


bot.run('TOKEN')
