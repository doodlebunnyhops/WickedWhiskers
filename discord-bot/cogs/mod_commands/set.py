import discord
from discord import app_commands
import db_utils
import utils.checks as checks
from utils.utils import post_to_target_channel,create_invite_embed
from modals.settings import Bot

# Subcommand group for setting (used within the server group)
set_group = app_commands.Group(name="set", description="Set commands")


# set_player_group = app_commands.Group(name="player", description="Player commands")

# set_group.add_command(set_player_group)

@set_group.command(name="role", description="Set a role for access to restricted bot commands.")
@app_commands.describe(
    role="The role to set"
)
@checks.check_if_has_permission_or_role()
async def set_roles(interaction: discord.Interaction, role: discord.Role):
    guild_id = interaction.guild.id

    # Validate that the role belongs to the current guild
    if role.guild.id != guild_id:
        await interaction.response.send_message(f"The role {role.name} is not valid in this guild.", ephemeral=True)
        return

    db_utils.set_role_by_guild(guild_id, role.id)

    #MessagingLoader
    personal_message = interaction.client.message_loader.get_message(
        "set_roles", "personal_message", role_name=role.name, user=interaction.user.mention
    )
    await interaction.response.send_message(personal_message, ephemeral=True)
    
    admin_message = interaction.client.message_loader.get_message(
        "set_roles", "admin_messages", role_name=role.name, user=interaction.user.name
    )

    await post_to_target_channel(interaction,admin_message,"admin")


# Define choices for the channel type
@set_group.command(name="channel", description="Set the channel for either event or admin messages to be posted.")
@app_commands.describe(
    channel_type="The type of channel to set (event or admin)",
    channel="The channel where the message type will be posted"
)
@checks.check_if_has_permission_or_role()
@app_commands.choices(channel_type=[
    app_commands.Choice(name="Event", value="event"),
    app_commands.Choice(name="Admin", value="admin")
])
async def set_channel(interaction: discord.Interaction, channel_type: app_commands.Choice[str], channel: discord.TextChannel):
    guild_id = interaction.guild.id

    # Check the type of channel (event or admin)
    if channel_type.value == "event":
        existing_channel_id = db_utils.get_event_channel(guild_id)
    elif channel_type.value == "admin":
        existing_channel_id = db_utils.get_admin_channel(guild_id)

    # Check if a channel is already set
    if existing_channel_id is not None:
        existing_channel = interaction.guild.get_channel(existing_channel_id)
        if existing_channel:
            await interaction.response.send_message(
                f"The {channel_type.name.lower()} channel is already set to {existing_channel.mention}. Please delete or update it first.",
                ephemeral=True
            )
            return

    # Set the new channel based on the type
    if channel_type.value == "event":
        db_utils.set_event_channel(guild_id, channel.id)
        # await interaction.response.send_message(f"The event channel has been set to {channel.mention}.", ephemeral=True)
    elif channel_type.value == "admin":
        db_utils.set_admin_channel(guild_id, channel.id)
        # await interaction.response.send_message(f"The admin channel has been set to {channel.mention}.", ephemeral=True)

    #MessagingLoader
    personal_message = interaction.client.message_loader.get_message(
        "set_channel", "personal_message", channel_type=channel_type.value, channel=channel.name
    )
    # Respond with the formatted message
    await interaction.response.send_message(personal_message, ephemeral=True)

    admin_message = interaction.client.message_loader.get_message(
        "set_channel", "admin_messages", channel_type=channel_type.value, channel=channel.name, user=interaction.user.name
    )
    # Respond with the formatted message
    await post_to_target_channel(interaction,admin_message,channel_type="admin")



@set_group.command(name="settings", description="Update the bot's settings.")
@checks.check_if_has_permission_or_role()
async def set_bot_settings(interaction: discord.Interaction):
    modal = Bot()
    await interaction.response.send_modal(modal)


# @set_group.command(name="game_settings", description="Update the game settings.")
# @checks.check_if_has_permission_or_role()
# async def set_game_settings(interaction: discord.Interaction):
#     modal = GameSettings()
#     await interaction.response.send_modal(modal)