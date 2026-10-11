import discord
from discord import app_commands
import potions
from admin_settings import text
from utils.artwork import icon_embed
from modals.shop import ManageView, ShopEntrance, tell

from cogs.mod_commands.set import set_group
from cogs.mod_commands.send import send_group
manage_group = app_commands.Group(name="manage", description="Manage game mechanics")

@manage_group.command(name="shop", description="Manage this server's potion prices and availability")
async def manage( interaction: discord.Interaction):
    if not potions.can_manage(interaction.user, interaction.guild_id):
        await tell(interaction, text('shop_denied'))
        return
    lines = [text('shop_offer',name=p.name,price=potions.offer(interaction.guild_id,key)[0],availability=text('on_sale' if potions.offer(interaction.guild_id,key)[1] else 'off_sale')) for key, p in potions.CATALOG.items()]
    await interaction.response.send_message("\n".join(lines), view=ManageView(interaction.user.id, interaction.guild_id), ephemeral=True)

@set_group.command(name="shop_manager_role", description="Set or clear the shop-manager role")
@app_commands.checks.has_permissions(manage_guild=True)
async def manager_role( interaction: discord.Interaction, role: discord.Role = None):
    from admin_settings import set_shop_manager
    try:set_shop_manager(interaction,role)
    except ValueError as error:
        await tell(interaction,str(error))
        return
    await tell(interaction, text('shop_role',role=role.name if role else text('none')))

@send_group.command(name="shop", description="Post a permanent Open Shop button")
async def post( interaction: discord.Interaction, channel: discord.TextChannel):
    if not potions.can_manage(interaction.user, interaction.guild_id):
        await tell(interaction, text('shop_denied'))
        return
    await interaction.response.defer(ephemeral=True)
    message = interaction.client.message_loader.get_message
    await channel.send(embed=icon_embed(message('artwork_messages', 'shop_description'), 'potion_shop', title=message('artwork_messages', 'shop_title')), view=ShopEntrance())
    await tell(interaction, text('shop_posted',channel=channel.mention))

