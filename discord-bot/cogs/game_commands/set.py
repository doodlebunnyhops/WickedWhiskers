
import discord
from discord import app_commands
import utils.checks as checks
from db_utils import get_game_settings, set_game_disabled

from modals.settings import Game

# Subcommand group for setting (used within the server group)
set_group = app_commands.Group(name="set", description="Set commands")

@set_group.command(name="settings", description="Update the game settings.")
@checks.check_if_has_permission_or_role()
async def set_game_settings(interaction: discord.Interaction):
    modal = Game()
    await interaction.response.send_modal(modal)


@set_group.command(name="state", description="Enable or disable the game.")
@app_commands.describe(
    state="Enable or disable the game."
)
@app_commands.choices(state=[
    app_commands.Choice(name="Enable", value="enable"),
    app_commands.Choice(name="Disable", value="disable")
])
@checks.check_if_has_permission_or_role()
async def set_game_state( interaction: discord.Interaction, state: app_commands.Choice[str]):
    guild_id = interaction.guild.id

    # Fetch current settings from the db using db_utils
    game_disabled, _, _ = get_game_settings(guild_id)

    # Logic based on the selected option and current game state
    if state.value == "enable":
        if not game_disabled:
            await interaction.response.send_message("The game commands are already enabled.", ephemeral=True)
            return
        set_game_disabled(guild_id, False)
        await interaction.response.send_message("The game commands have been enabled.", ephemeral=True)

    elif state.value == "disable":
        if game_disabled:
            await interaction.response.send_message("The game commands are already disabled.", ephemeral=True)
            return
        set_game_disabled(guild_id, True)
        await interaction.response.send_message("The game commands have been disabled.", ephemeral=True)
