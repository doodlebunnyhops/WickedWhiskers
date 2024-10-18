import logging
import discord
from discord import app_commands
import db_utils
import utils.checks as checks
from utils.player import calculate_thief_success_rate

get_group = app_commands.Group(name="get", description="get commands")


@get_group.command(name="settings", description="View the game settings.")
@checks.check_if_has_permission_or_role()
async def get_game_settings(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    # Fetch the game settings from the database
    game_disabled, potion_price, trick_success_rate = db_utils.get_game_settings(guild_id)

    # Prepare the response message
    trick_success_rate = round(trick_success_rate, 2)
    response_message = (
        f"Player Game Commands: {'Disabled' if game_disabled == 1 else 'Enabled'}\n"
        f"Potion Price: {potion_price} candy for 1 potion\n"
        f"Trick Success Rate: {trick_success_rate}%"
    )
    await interaction.response.send_message(response_message, ephemeral=True)

@get_group.command(name="cauldron", description="View how much is in the cauldron.")
@checks.check_if_has_permission_or_role()
async def get_cauldron_pool(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    # Fetch the cauldron pool from the database
    cauldron_pool = db_utils.get_cauldron_pool(guild_id)
    response_message = f"The cauldron currently has {cauldron_pool} candy."
    await interaction.response.send_message(response_message, ephemeral=True)


@get_group.command(name="player", description="View a player's stats.")
@checks.check_if_has_permission_or_role()
@app_commands.choices(get=[
    app_commands.Choice(name="Stats", value="stats"),
    app_commands.Choice(name="Hidden Values", value="hidden_values"),
    app_commands.Choice(name="All", value="all")
])
@app_commands.describe(
    user="The user whose stats you want to view",
    get="The details you want to view (stats, hidden values, or both)"
)
async def get_player_stats(interaction: discord.Interaction, user: discord.Member, get: app_commands.Choice[str]):
    guild_id = interaction.guild.id
    # Fetch the player's stats from the database
    player_data = db_utils.get_player_data(user.id, guild_id)

    if player_data:
        try:
            candy_in_bucket = player_data.get('candy_in_bucket', 0)
            successful_tricks = player_data.get('successful_tricks', 0)
            failed_tricks = player_data.get('failed_tricks', 0)
            treats_given = player_data.get('treats_given', 0)
            potions_purchased = player_data.get('potions_purchased', 0)
            active = player_data.get('active', 0)
            
            active_status = "Active" if active == 1 else "Inactive"

            # Prepare the response based on the selected details option
            response_message = ""

            if get.value == "stats" or get.value == "all":
                # Standard player stats
                response_message += (
                    f"{user.display_name} has {candy_in_bucket} candy.\n"
                    f"Potions In Stock: {potions_purchased}\n"
                    f"Successful steals: {successful_tricks}\n"
                    f"Failed steals: {failed_tricks}\n"
                    f"Candy given: {treats_given}\n"
                    f"Status: {active_status}\n"
                )
            
            if get.value == "hidden_values" or get.value == "all":
                # Hidden values
                # evilness, sweetness, trick_success_rate = hidden_values
                trick_success_rate = calculate_thief_success_rate(candy_in_bucket)
                response_message += (
                    f"Hidden Values:\n"
                    # f"Evilness: {evilness}\n"
                    # f"Sweetness: {sweetness}\n"
                    f"Trick Success Rate: {trick_success_rate*100}%\n"
                )

            await interaction.response.send_message(response_message, ephemeral=True)
        
        except Exception as e:
            logging.error(f"Error fetching player stats: {str(e)}")
            await interaction.response.send_message("An error occurred while fetching player stats.", ephemeral=True)
    
    else:
        await interaction.response.send_message(f"{user.display_name} has not joined the game yet.", ephemeral=True)
