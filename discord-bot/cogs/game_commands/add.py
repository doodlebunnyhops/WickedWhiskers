import discord
from discord import app_commands
from db_utils import add_player_to_game
import utils.checks as checks
from modals.settings import Bot

# Subcommand group for setting (used within the server group)
add_group = app_commands.Group(name="add", description="Add commands")

@add_group.command(name="player", description="Add a player to the game.")
@app_commands.describe(
    user="The player to be added"
)
@checks.check_if_has_permission_or_role()
async def add_player(interaction: discord.Interaction, user: discord.Member):
    guild_id = interaction.guild.id
    #check if player is already in the game
    
    #if false player is already in the game
    if not add_player_to_game(user.id, guild_id):
        await interaction.response.send_message(f"Player {user.display_name} is already in the game.", ephemeral=True)
        return
    await interaction.response.send_message(f"Added player {user.display_name} to the game.", ephemeral=True)

