import discord
from discord import app_commands
import db_utils
import utils.checks as checks

delete_group = app_commands.Group(name="delete", description="Delete commands")

@delete_group.command(name="role", description="Delete a role from the games restricted commands")
@checks.check_if_has_permission_or_role()
async def delete_role(interaction: discord.Interaction, role: discord.Role):
    guild_id = interaction.guild.id
    db_utils.delete_role_by_guild(role.id,guild_id)
    await interaction.response.send_message(f"Role {role.name} has been deleted from accessing restricted commands.",ephemeral=True)
