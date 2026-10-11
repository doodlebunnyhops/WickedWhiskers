import discord
from discord import app_commands
import db_utils
import utils.checks as checks
from utils.utils import post_to_target_channel,create_invite_embed
import admin_settings as shared

# Subcommand group for setting (used within the server group)
set_group = app_commands.Group(name="set", description="Set commands")
add_group = app_commands.Group(name="add", description="Add access roles")


# set_player_group = app_commands.Group(name="player", description="Player commands")

# set_group.add_command(set_player_group)

@add_group.command(name="role", description="Set a role for access to restricted bot commands.")
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

    try:
        shared.add_role(guild_id, role)
    except ValueError as error:
        await interaction.response.send_message(str(error), ephemeral=True)
        return

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

    shared.set_channel(guild_id, channel_type.value, channel)

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
    await interaction.response.send_message(shared.text("bot_panel"), view=shared.BotSettingsView(interaction), ephemeral=True)


# @set_group.command(name="game_settings", description="Update the game settings.")
# @checks.check_if_has_permission_or_role()
# async def set_game_settings(interaction: discord.Interaction):
#     modal = GameSettings()
#     await interaction.response.send_modal(modal)
