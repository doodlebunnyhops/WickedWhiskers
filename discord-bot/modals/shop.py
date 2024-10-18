import discord
from db_utils import get_game_settings, get_player_data, update_player_field

from utils import shop

class BuyPotion(discord.ui.Modal, title="Purchase Potion"):
    amount = discord.ui.TextInput(label="How many?", placeholder="e.g., 1", required=True)

    def __init__(self, target_user: discord.Member):
        super().__init__()
        self.target_user = target_user
        self.guild_id = target_user.guild.id
        self.title = f"Purchase Potion: {self.potion_price()} candy each"

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount.value)
            if not isinstance(amount, int):
                raise ValueError("Amount must be an integer.")
            await shop.buy_potion(interaction, self.target_user, amount)

        except ValueError:
            await interaction.response.send_message("Please enter a valid number.", ephemeral=True)

    def potion_price(self) -> int:
        game_settings = get_game_settings(self.guild_id)
        _, potion_price, _ = game_settings
        return potion_price
