import discord
import utils.checks as checks
from discord.ext import commands
from discord import app_commands
import db_utils
import logging

from cogs.set import set_group
from cogs.get import get_group
from cogs.remove import remove_group

# importlib.reload(utils)
# importlib.reload(db_utils)

class RoleAccess(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Top-level group
    server = app_commands.Group(name="server", description="Moderator Commands")

    # Import and add the other groups
    server.add_command(set_group)
    server.add_command(get_group)
    server.add_command(remove_group)

    # Subgroup under manage
    get = app_commands.Group(name="get", description="Manage roles for the guild")
    remove = app_commands.Group(name="remove", description="Manage roles for the guild")

    # Subcommand in the parent group (manage)
    @server.command(name="list", description="List the saved roles")
    async def list_roles(self, interaction: discord.Interaction):
        await interaction.response.send_message("Listing ...")



    # @remove.command(name="role", description="Remove a role from the guild")
    # @checks.check_if_has_permission_or_role()
    # async def remove_role(self, interaction: discord.Interaction, role: discord.Role):
    #     guild_id = interaction.guild.id
    #     db_utils.remove_role_by_guild(role.id,guild_id)
    #     await interaction.response.send_message(f"Role {role.name} has been removed from accessing restricted commands.",ephemeral=True)

    server.add_command(get)
    server.add_command(remove)
# Setup function to add the cog and the group
async def setup(bot):
    cog = RoleAccess(bot)
    # Register the command group in the tree (this is enough)
    bot.tree.add_command(cog.server)
