

import discord
from db_utils import get_game_settings, get_player_data, update_player_field


async def buy_potion(interaction: discord.Interaction, user: discord.Member, amount: int):
    guild_id = interaction.guild.id
    game_disabled, potion_price, _ = get_game_settings(guild_id)

    if game_disabled:
        await interaction.response.send_message("The game is currently paused.", ephemeral=True)
        return False

    player_data = get_player_data(user.id, guild_id)

    # Ensure player_data exists and the player is active
    if not player_data or player_data['active'] == 0:
        await interaction.response.send_message(f"{user.mention}, you must join the game to participate! /join", ephemeral=True)
        return False

    # Ensure the amount is valid
    if amount <= 0:
        await interaction.response.send_message(f"{user.mention}, you can't buy a negative or zero amount of potions!", ephemeral=True)
        return False

    candy_cost = potion_price * amount

    if player_data["candy_in_bucket"] < candy_cost:
        await interaction.response.send_message(
            f"{user.mention}, you need at least {candy_cost} candy to buy {amount} {'potions' if amount > 1 else 'potion'}. You currently have {player_data['candy_in_bucket']}...",
            ephemeral=True
        )
        return False

    # Update player data
    update_player_field(user.id, guild_id, 'candy_in_bucket', player_data["candy_in_bucket"] - candy_cost)
    update_player_field(user.id, guild_id, 'potions_purchased', player_data["potions_purchased"] + amount)

    await interaction.response.send_message(
        f"{user.mention}, you have bought {amount} {'potions' if amount > 1 else 'potion'}! Good luck with the cauldron event!",
        ephemeral=True
    )
    return True

async def view_prices(interaction: discord.Interaction):
    """
    Handles the interaction for viewing the prices of items in the shop.
    Parameters:
        interaction (discord.Interaction): The interaction object from Discord.
    Returns:
        None
    Behavior:
        - Checks if the game is disabled for the guild. If disabled, sends a message indicating the game is paused.
        - Retrieves the potion price from the game settings.
        - Sends a message to the user with the current prices of items in the shop.
    """
    guild_id = interaction.guild.id
    game_disabled, potion_price,_ = get_game_settings(guild_id)
    if game_disabled:
        print(f"Game is disabled for guild {guild_id}")
        await interaction.response.send_message("The game is currently paused.", ephemeral=True)
        return

    await interaction.response.send_message(f"Current Shop Prices:\nPotion: {potion_price} candy")