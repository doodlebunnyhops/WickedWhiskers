import discord
from discord import app_commands
from discord.ext import commands
import potions
from admin_settings import text
from utils.artwork import icon_embed
from modals.shop import open_shop, show_inventory, UsePotionModal, ManageView, ShopEntrance, tell


@app_commands.guild_only()
class Shop(commands.GroupCog, group_name="shop", group_description="Luna & Raven's Potion Shop"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="browse", description="Open the potion shop modal")
    async def browse(self, interaction: discord.Interaction):
        await open_shop(interaction)



class PotionInventory(commands.Cog):
    @app_commands.command(name="inventory", description="View your potion bottles and active effects")
    @app_commands.guild_only()
    async def inventory(self, interaction: discord.Interaction):
        await show_inventory(interaction)

    @app_commands.command(name="use", description="Open the potion activation modal")
    @app_commands.guild_only()
    async def use(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_modal(UsePotionModal(interaction.user.id, interaction.guild_id))
        except potions.PotionError as error:
            await tell(interaction, str(error))


async def setup(bot):
    await bot.add_cog(Shop(bot))
    await bot.add_cog(PotionInventory())
    bot.add_view(ShopEntrance())
