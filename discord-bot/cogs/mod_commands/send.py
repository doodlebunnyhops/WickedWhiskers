import discord
from discord import app_commands
import db_utils
import utils.checks as checks
from utils.utils import post_to_target_channel,create_invite_embed
from modals.settings import Bot

send_group = app_commands.Group(name="send", description="Send commands")

# Slash command to post message players react to join the game.
@send_group.command(name="join_game_msg", description="Posts a message for players to join by reacting with a 🎃.")
@app_commands.describe( #join_game_msg
    channel="Channel where the invite message will be posted"
)
@checks.check_if_has_permission_or_role()
async def set_join_game_msg(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = interaction.guild.id

    # Check if an invite message already exists for the guild
    result = db_utils.get_join_game_msg_settings(guild_id)  # Fetch both the message ID and the channel ID
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

    db_utils.set_join_game_msg_settings(guild_id,game_invite_message_id,channel.id)
    #MessagingLoader
    personal_message = interaction.client.message_loader.get_message(
        "set_join_game_msg", "personal_message", channel=channel.name, jump_url=invite_message.jump_url
    )
    admin_message = interaction.client.message_loader.get_message(
        "set_join_game_msg", "admin_messages", channel=channel.name, jump_url=invite_message.jump_url, user=interaction.user.name
    )
    if interaction.response.is_done():
        await interaction.followup.send(personal_message, ephemeral=True)
    else:
        await interaction.response.send_message(personal_message, ephemeral=True)
    await post_to_target_channel(interaction,admin_message,"admin")
