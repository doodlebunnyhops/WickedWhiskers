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
    import player_state as state
    if user.bot:
        await interaction.response.send_message(state.text('bots_cannot_join'), ephemeral=True)
        return
    try:
        state.join(interaction.guild.id, user.id)
    except state.StateError as error:
        await interaction.response.send_message(str(error), ephemeral=True)
        return
    await interaction.response.send_message(state.text('admin_joined', player=user.mention), ephemeral=True)
