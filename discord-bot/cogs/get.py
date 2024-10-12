import logging
import discord
from discord import app_commands
import db_utils
import utils.checks as checks

# Subcommand group for setting (used within the server group)
get_group = app_commands.Group(name="get", description="get commands")


@get_group.command(name="roles", description="Get all saved roles permitted to use restricted commands.")
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


@get_group.command(name="game_join_msg", description="Gets the link to the message where you can join the game.")
async def game_join_msg(interaction: discord.Interaction):
    guild_id = interaction.guild.id

    # Fetch the game invite message and channel ID from the database
    result = db_utils.get_game_join_msg_settings(guild_id)

    if result is None:
        # No message stored for the guild
        await interaction.response.send_message("No game invite message has been set up for this guild.", ephemeral=True)
        return

    game_invite_message_id, game_invite_channel_id = result

    # Fetch the channel object
    game_invite_channel = interaction.guild.get_channel(game_invite_channel_id)
    if game_invite_channel is None:
        await interaction.response.send_message("The channel where the game invite was posted no longer exists.", ephemeral=True)
        return

    # Fetch the message from the channel
    try:
        game_invite_message = await game_invite_channel.fetch_message(game_invite_message_id)
        # Send the message link to the user
        await interaction.response.send_message(
            f"Here is the invite message: {game_invite_message.jump_url}",
            ephemeral=True
        )
    except discord.NotFound:
        # If the message was not found (deleted)
        await interaction.response.send_message("The game invite message no longer exists.", ephemeral=True)
    except discord.Forbidden:
        # If the bot does not have permission to access the message
        await interaction.response.send_message("I do not have permission to access the game invite message.", ephemeral=True)
    except discord.HTTPException:
        # General HTTP error
        await interaction.response.send_message("An error occurred while fetching the game invite message.", ephemeral=True)