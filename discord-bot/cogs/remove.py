import discord
from discord import app_commands
import db_utils
import utils.checks as checks

remove_group = app_commands.Group(name="remove", description="Remove commands")

@remove_group.command(name="role", description="Remove a role from the guild")
@checks.check_if_has_permission_or_role()
async def remove_role(interaction: discord.Interaction, role: discord.Role):
    guild_id = interaction.guild.id
    db_utils.remove_role_by_guild(role.id,guild_id)
    await interaction.response.send_message(f"Role {role.name} has been removed from accessing restricted commands.",ephemeral=True)
