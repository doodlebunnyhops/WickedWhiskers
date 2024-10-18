
import discord
from discord import app_commands
import utils.checks as checks
from db_utils import get_game_settings, set_game_disabled,get_cauldron_pool,is_player_active,update_player_field,set_cauldron_pool,set_game_setting

from modals.settings import Game

# Subcommand group for setting (used within the server group)
set_group = app_commands.Group(name="set", description="Set commands")

@set_group.command(name="settings", description="Update the game settings.")
@checks.check_if_has_permission_or_role()
async def set_game_settings_cmd(interaction: discord.Interaction, potion_price: int, trick_success_rate: float,game_enabled: bool = False):
    guild_id = interaction.guild.id

    # Validate the input values
    if potion_price < 0 or trick_success_rate < 0 or trick_success_rate > 300:
        await interaction.response.send_message("Invalid values provided. Please ensure the potion price is a positive integer and the trick success rate is a percentage between 0 and 100.", ephemeral=True)
        return

    # Update the game settings in the database
    set_game_setting(guild_id, game_enabled, potion_price, trick_success_rate)

    await interaction.response.send_message("Game settings updated successfully.", ephemeral=True)

@set_group.command(name="cauldron", description="Set the amount of candy in the cauldron.")
@checks.check_if_has_permission_or_role()
async def set_cauldron_pool_amount(interaction: discord.Interaction, amount: int):
    guild_id = interaction.guild.id

    # Validate the input value
    if amount < 0:
        await interaction.response.send_message("Invalid value provided. Please ensure the amount is a positive integer.", ephemeral=True)
        return

    # Update the cauldron pool in the database
    set_cauldron_pool(guild_id, amount)

    await interaction.response.send_message(f"The cauldron pool has been updated to {amount} candy.", ephemeral=True)

@set_group.command(name="player_stat", description="Set Player stat")
@checks.check_if_has_permission_or_role()
@app_commands.choices(stat=[
    app_commands.Choice(name="Candy", value="candy_in_bucket"),
    app_commands.Choice(name="Successful Tricks", value="successful_tricks"),
    app_commands.Choice(name="Failed Tricks", value="failed_tricks"),
    app_commands.Choice(name="Treats Given", value="treats_given"),
    app_commands.Choice(name="Potions Purchased", value="potions_purchased")
])
@app_commands.describe(
    user="The player you want to modify",
    stat="The stat you want to change (e.g., candy_in_bucket)",
    number="The value you want to set for the stat"
)
async def set_player_stat(interaction: discord.Interaction, user: discord.Member, stat: str, number: int):    
    guild_id = interaction.guild.id

    #check if player exits
    if not is_player_active(user.id, guild_id):
        await interaction.response.send_message(f"{user.display_name} has not joined the game!", ephemeral=True)
        return
    else:
        # Update the player's stat in the database
        update_player_field(user.id,guild_id, stat, number)
        await interaction.response.send_message(f"{user.display_name}'s {stat.replace('_', ' ')} has been updated to {number}.", ephemeral=True)


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
        get_cauldron_pool(guild_id) #init pool  
        await interaction.response.send_message("The game commands have been disabled.", ephemeral=True)
