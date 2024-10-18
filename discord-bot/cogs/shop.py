from discord import app_commands
from discord.ext import commands
import discord
from utils import shop
from modals.shop import BuyPotion
# from slashcmds.subgroup import subgroup
# from cogs.subgroup import subgroup

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    buy_group = app_commands.Group(name="buy",description="Buy items from the shop")
    shop_group = app_commands.Group(name="shop",description="Buy items from the shop")

    @buy_group.command(name="potion", description="Buy Potion for a chance to win a prize from the cauldron!")
    async def potion(self, interaction: discord.Interaction,amount:int):
        await shop.buy_potion(interaction, interaction.user, amount)
    
    @shop_group.command(name="prices", description="View the prices of items in the shop")
    async def prices(self, interaction: discord.Interaction):
        await shop.view_prices(interaction)

async def setup(bot):
    await bot.add_cog(Shop(bot))