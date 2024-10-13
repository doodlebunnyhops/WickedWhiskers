import discord
from discord import app_commands
import db_utils
import utils.checks as checks
from utils.utils import post_to_target_channel

delete_group = app_commands.Group(name="delete", description="Delete commands")

@delete_group.command(name="role", description="Delete a role from the games restricted commands")
@checks.check_if_has_permission_or_role()
async def delete_role(interaction: discord.Interaction, role: discord.Role):

    personal_message = interaction.client.message_loader.get_message(
        "delete_role", "personal_message", role_name=role.name
    )
    # Respond with the formatted message
    await interaction.response.send_message(personal_message, ephemeral=True)

    ### DO THE THING JULIE!
    guild_id = interaction.guild.id
    db_utils.delete_role_by_guild(role.id,guild_id)

    # Access the message loader from the bot instance
    admin_message = interaction.client.message_loader.get_message(
        "delete_role", "admin_messages", role_name=role.name, user=interaction.user.mention
    )
    await post_to_target_channel(interaction,admin_message,channel_type="admin")
    # await interaction.response.send_message(f"Role {role.name} has been deleted from accessing restricted commands.",ephemeral=True)


@delete_group.command(name="channel", description="Delete the event or admin channel setting.")
@checks.check_if_has_permission_or_role()
@app_commands.choices(channel_type=[
    app_commands.Choice(name="Event", value="event"),
    app_commands.Choice(name="Admin", value="admin")
])
async def delete_channel_command(interaction: discord.Interaction, channel_type: app_commands.Choice[str]):
    guild_id = interaction.guild.id

    # Fetch the existing channel based on the type (event or admin)
    if channel_type.value == "event":
        existing_channel_id = db_utils.get_event_channel(guild_id)
    elif channel_type.value == "admin":
        existing_channel_id = db_utils.get_admin_channel(guild_id)

    # Check if a channel is set
    if existing_channel_id is None:
        await interaction.response.send_message(f"No {channel_type.name.lower()} channel has been set yet. Use the /set channel command to set it.", ephemeral=True)
        return

    personal_message = interaction.client.message_loader.get_message(
        "delete_channel", "personal_message", channel_type=channel_type.value, channel_name=interaction.guild.get_channel(existing_channel_id).name
    )
    # Respond with the formatted message
    await interaction.response.send_message(personal_message, ephemeral=True)

    # Delete the selected channel from the database
    if channel_type.value == "event":
        db_utils.delete_event_channel(guild_id)
    elif channel_type.value == "admin":
        db_utils.delete_admin_channel(guild_id)

    admin_message = interaction.client.message_loader.get_message(
        "delete_channel", "admin_messages", channel_type=channel_type.value, channel_name=interaction.guild.get_channel(existing_channel_id).name,user=interaction.user.mention
    )
    # Respond with the formatted message
    await post_to_target_channel(interaction,admin_message,channel_type=channel_type.value)
