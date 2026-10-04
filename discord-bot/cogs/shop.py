import discord
from discord import app_commands
from discord.ext import commands
import potions
from utils.artwork import icon_embed
from modals.shop import open_shop, show_inventory, UsePotionModal, ManageView, ShopEntrance, tell


@app_commands.guild_only()
class Shop(commands.GroupCog, group_name="shop", group_description="Luna & Raven's Potion Shop"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="browse", description="Open the potion shop modal")
    async def browse(self, interaction: discord.Interaction):
        await open_shop(interaction)

    @app_commands.command(name="protection", description="Buy timed protection, check its timer, or end it early")
    async def protection(self,interaction:discord.Interaction):
        from modals.protection import open_protection
        await open_protection(interaction)

    @app_commands.command(name="manage", description="Manage this server's potion prices and availability")
    async def manage(self, interaction: discord.Interaction):
        if not potions.can_manage(interaction.user, interaction.guild_id):
            await tell(interaction, "Manage Server or the designated shop-manager role is required.")
            return
        lines = [f"{p.name}: {potions.offer(interaction.guild_id, key)[0]} candy ({'on sale' if potions.offer(interaction.guild_id, key)[1] else 'disabled'})" for key, p in potions.CATALOG.items()]
        await interaction.response.send_message("\n".join(lines), view=ManageView(interaction.user.id, interaction.guild_id), ephemeral=True)

    @app_commands.command(name="manager_role", description="Set or clear the shop-manager role")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def manager_role(self, interaction: discord.Interaction, role: discord.Role = None):
        if role and (role.is_default() or role.managed):
            await tell(interaction, "Choose a regular role other than @everyone.")
            return
        potions.set_manager_role(interaction.guild_id, interaction.user.id, role.id if role else None)
        await tell(interaction, f"Shop-manager role: {role.name if role else 'none'}. Manage Server always retains access.")

    @app_commands.command(name="post", description="Post a permanent Open Shop button")
    async def post(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not potions.can_manage(interaction.user, interaction.guild_id):
            await tell(interaction, "Shop management permission is required.")
            return
        await interaction.response.defer(ephemeral=True)
        message = interaction.client.message_loader.get_message
        await channel.send(embed=icon_embed(message('artwork_messages', 'shop_description'), 'potion_shop', title=message('artwork_messages', 'shop_title')), view=ShopEntrance())
        await tell(interaction, f"Shop entrance posted in {channel.mention}.")


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
