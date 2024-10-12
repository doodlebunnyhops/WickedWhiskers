import logging
import discord
from discord import app_commands
import db_utils
import utils.checks as checks

# Subcommand group for setting (used within the server group)
get_group = app_commands.Group(name="get", description="get commands")


@get_group.command(name="role", description="Get the saved roles")
@checks.check_if_has_permission_or_role()
async def get_role(interaction: discord.Interaction):
    logging.debug("role_access get command was triggered")
    await interaction.response.send_message("Fetching roles...",delete_after=10,ephemeral=True)
    role_ids = db_utils.fetch_roles_by_guild(interaction.guild.id)

    # Log the fetched role IDs to verify
    logging.debug(f"Fetched role IDs: {role_ids}")
    if not role_ids:
        await interaction.followup.send("No roles have been assigned access to restricted commands.", ephemeral=True)
        return

    # Get the role names from the guild and format them
    roles = [interaction.guild.get_role(role_id) for role_id in role_ids]
    valid_roles = [role.name for role in roles if role is not None]  # Filter out any roles that might have been deleted

    if not valid_roles:
        await interaction.followup.send("None of the assigned roles exist in this guild anymore.", ephemeral=True)
        return

    role_names = ", ".join(valid_roles)
    await interaction.followup.send(f"The following roles have access to restricted commands: {role_names}", ephemeral=True)
