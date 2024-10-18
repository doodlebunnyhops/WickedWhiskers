import discord
from discord import app_commands
import db_utils
import utils.checks as checks
from utils.utils import post_to_target_channel,create_invite_embed

# Subcommand group for updates (used within the server group)
update_group = app_commands.Group(name="update", description="Update commands")

# Slash command to update location of message to players for react to join the game.
@update_group.command(name="join_game_msg", description="Update where react to join message will be posted.")
@app_commands.describe(
    channel="Channel where the invite message will be posted"
)
@checks.check_if_has_permission_or_role()
async def update_join_game_msg(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = interaction.guild.id

    # Fetch the previous game invite message and channel ID from the database
    result = db_utils.get_join_game_msg_settings(guild_id)
    
    if result is None:
        # The Invite Message wasn't created yet, lets go ahead and make it
        no_previous_msg = interaction.client.message_loader.get_message(
        "update_join_game_msg", "no_previous_msg"
        )
        await interaction.response.send_message(no_previous_msg, ephemeral=True)
    
    old_message_id, old_channel_id = result

    # Fetch the old channel
    old_channel = interaction.guild.get_channel(old_channel_id)
    
    # Check if the old channel exists
    if old_channel is not None:
        # Try to fetch the old message
        try: #this is gross... i'm sorry
            old_message = await old_channel.fetch_message(old_message_id)
            await interaction.response.send_message(f"The old invite message still exists in {old_channel.mention}. Please delete it before updating. Directly link to message: {old_message.jump_url}", ephemeral=True)
            return  # Exit if the old message is still present
        except discord.NotFound:
            # The old message no longer exists, proceed to post a new one
            msg_deleted_check = interaction.client.message_loader.get_message(
                "update_join_game_msg", "msg_deleted_check")
            if interaction.response.is_done():
                await interaction.followup.send(msg_deleted_check, ephemeral=True)
            else:
                await interaction.response.send_message(msg_deleted_check, ephemeral=True)
        except discord.Forbidden:
            # If the bot doesn't have permission to view the old message
            await interaction.response.send_message(f"I do not have permission to access the old invite message in {old_channel.mention}.", ephemeral=True)
            return
        except discord.HTTPException:
            # Handle general errors fetching the message
            await interaction.response.send_message(f"An error occurred while trying to fetch the old invite message.", ephemeral=True)
            return
        except discord.errors.NotFound:
            # The old message no longer exists, proceed to post a new one
            msg_deleted_check = interaction.client.message_loader.get_message(
                "update_join_game_msg", "msg_deleted_check")
            if interaction.response.is_done:
                await interaction.followup.send(msg_deleted_check, ephemeral=True)
            else:
                await interaction.response.send_message(msg_deleted_check, ephemeral=True)
        except Exception as e:
            # Generic exception handler for any other exceptions
            if interaction.response.is_done():
                print(f"idk....{str(e)}")
            else:
                print(f"idk....{str(e)}")



    # Post the new invite message in the specified channel
    embed = create_invite_embed(message_loader=interaction.client.message_loader)
    new_invite_message = await channel.send(embed=embed)
    # new_invite_message = await channel.send("React with 🎃 to join the candy game and start your trick-or-treat adventure!")
    new_message_id = new_invite_message.id  # Get the new message ID
    new_channel_id = channel.id             # Get the new channel ID

    # Update the database with the new message and channel ID
    db_utils.set_join_game_msg_settings(guild_id, new_message_id, new_channel_id)

    #MessagingLoader
    personal_message = interaction.client.message_loader.get_message(
        "update_join_game_msg", "personal_message", channel=channel.name,jump_url=new_invite_message.jump_url, user=interaction.user.name
    )
    admin_message = interaction.client.message_loader.get_message(
        "update_join_game_msg","admin_messages", channel=channel.name,jump_url=new_invite_message.jump_url, user=interaction.user.name
    )

        # Respond with the formatted message
    if interaction.response.is_done():
        await interaction.followup.send(personal_message, ephemeral=True)
    else:
        await interaction.response.send_message(personal_message, ephemeral=True)
    await post_to_target_channel(interaction,admin_message,channel_type="admin")

@update_group.command(name="channel", description="Update the channel where event or admin messages will be posted.")
@app_commands.describe(
    channel="The channel to update the event or admin channel bot messages to.",
    channel_type="The type of channel to update (event or admin)"
)
@checks.check_if_has_permission_or_role()
@app_commands.choices(channel_type=[
    app_commands.Choice(name="Event", value="event"),
    app_commands.Choice(name="Admin", value="admin")
])
async def update_channel_command(interaction: discord.Interaction, channel_type: app_commands.Choice[str], channel: discord.TextChannel):
    guild_id = interaction.guild.id

    # Fetch the existing channel based on the type (event or admin)
    if channel_type.value == "event":
        existing_channel_id = db_utils.get_event_channel(guild_id)
    elif channel_type.value == "admin":
        existing_channel_id = db_utils.get_admin_channel(guild_id)

    # Check if a channel is already set for the selected type
    if existing_channel_id is None:
        await interaction.response.send_message(f"No {channel_type.name.lower()} channel has been set yet. Use the /set channel command to set it.", ephemeral=True)
        return

    # Update the selected channel in the database
    if channel_type.value == "event":
        db_utils.set_event_channel(guild_id, channel.id)
    elif channel_type.value == "admin":
        db_utils.set_admin_channel(guild_id, channel.id)
    
    #MessagingLoader
    personal_message = interaction.client.message_loader.get_message(
        "update_channel", "personal_message", channel=channel.name,user=interaction.user.name, channel_type=channel_type.value
    )
    admin_message = interaction.client.message_loader.get_message(
        "update_channel","admin_messages", channel=channel.name,user=interaction.user.name, channel_type=channel_type.value
    )

    # Respond with the formatted message
    await interaction.response.send_message(personal_message, ephemeral=True)
    await post_to_target_channel(interaction,admin_message,channel_type="admin")

