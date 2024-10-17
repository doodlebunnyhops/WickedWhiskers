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

    db_utils.set_role_by_guild(role.id, guild_id)

    #MessagingLoader
    personal_message = interaction.client.message_loader.get_message(
        "set_roles", "personal_message", role_name=role.name, user=interaction.user.mention
    )
    await interaction.response.send_message(personal_message, ephemeral=True)
    
    admin_message = interaction.client.message_loader.get_message(
        "set_roles", "admin_messages", role_name=role.name, user=interaction.user.name
    )

    await post_to_target_channel(interaction,admin_message,"admin")

# Slash command to post message players react to join the game.
@set_group.command(name="game_join_msg", description="Posts a message for players to join by reacting with a 🎃.")
@app_commands.describe(
    channel="Channel where the invite message will be posted"
)
@checks.check_if_has_permission_or_role()
async def set_game_join_msg(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = interaction.guild.id

    # Check if an invite message already exists for the guild
    result = db_utils.get_game_join_msg_settings(guild_id)  # Fetch both the message ID and the channel ID
    if result and result[0] is not None and result[1] is not None:
        existing_message_id = result[0]
        existing_channel_id = result[1]

        # Fetch the existing channel
        existing_channel = interaction.guild.get_channel(existing_channel_id)
        if existing_channel is None:
            await interaction.response.send_message("The channel for the previous invite message no longer exists.", ephemeral=True)
            return
        
        # Check if the message still exists in the channel
        try:
            existing_message = await existing_channel.fetch_message(existing_message_id)
            # If the message exists, notify the moderator
            await interaction.response.send_message(
                f"An invite message already exists! Players can react to it to join. Here is the message: {existing_message.jump_url}",
                ephemeral=True
            )
            return
        except discord.NotFound:
            # If the message no longer exists, proceed to create a new one
            await interaction.response.send_message("Previous invite message not found, creating a new invite...", ephemeral=True)
        except discord.Forbidden:
            # The bot does not have permission to access the message
            await interaction.response.send_message("I do not have permission to access the previous invite message. Creating a new invite...", ephemeral=True)
        except discord.HTTPException:
            # A general HTTP error occurred
            await interaction.response.send_message("An error occurred while fetching the previous invite message. Creating a new invite...", ephemeral=True)
        except Exception as e:
            # Catch-all for any other exceptions
             await interaction.response.send_message(f"An unexpected error occurred: {str(e)}. Creating a new invite...", ephemeral=True)

    # Post the new invite message
    embed = create_invite_embed(interaction.client.message_loader)
    invite_message = await channel.send(embed=embed)
    # invite_message = await channel.send("React with 🎃 to join the candy game and start your trick-or-treat adventure!")
    game_invite_message_id = invite_message.id  # Get the new message ID

    db_utils.set_game_join_msg_settings(guild_id,game_invite_message_id,channel.id)
    #MessagingLoader
    personal_message = interaction.client.message_loader.get_message(
        "set_game_join_msg", "personal_message", channel=channel.name, jump_url=invite_message.jump_url
    )
    admin_message = interaction.client.message_loader.get_message(
        "set_game_join_msg", "admin_messages", channel=channel.name, jump_url=invite_message.jump_url, user=interaction.user.name
    )
    if interaction.response.is_done():
        await interaction.followup.send(personal_message, ephemeral=True)
    else:
        await interaction.response.send_message(personal_message, ephemeral=True)
    post_to_target_channel(interaction,admin_message,"admin")

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

@set_group.command(name="player_stat", description="Set Player stat")
@checks.check_if_has_permission_or_role()
@app_commands.choices(stat=[
    app_commands.Choice(name="Candy", value="candy_count"),
    app_commands.Choice(name="Successful Tricks", value="successful_steals"),
    app_commands.Choice(name="Failed Tricks", value="failed_steals"),
    app_commands.Choice(name="Treats Given", value="candy_given"),
    app_commands.Choice(name="Potions Purchased", value="tickets_purchased")
])
@app_commands.describe(
    user="The player you want to modify",
    stat="The stat you want to change (e.g., candy_count)",
    number="The value you want to set for the stat"
)
async def set_player_stat(interaction: discord.Interaction, user: discord.Member, stat: str, number: int):    
    guild_id = interaction.guild.id

    #check if player exits
    if not db_utils.is_player_active(user.id, guild_id):
        await interaction.response.send_message(f"{user.display_name} has not joined the game!", ephemeral=True)
        return
    else:
        # Update the player's stat in the database
        db_utils.update_player_field(user.id,guild_id, stat, number)
        await interaction.response.send_message(f"{user.display_name}'s {stat.replace('_', ' ')} has been updated to {number}.", ephemeral=True)


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