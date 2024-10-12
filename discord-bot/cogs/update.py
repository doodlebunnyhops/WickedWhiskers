import discord
from discord import app_commands
import db_utils
import utils.checks as checks

# Subcommand group for updates (used within the server group)
update_group = app_commands.Group(name="update", description="Update commands")

# Slash command to update location of message to players for react to join the game.
@update_group.command(name="game_join_msg", description="Update where react to join message will be posted.")
@checks.check_if_has_permission_or_role()
async def update_game_join_msg(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = interaction.guild.id

    # Fetch the previous game invite message and channel ID from the database
    result = db_utils.get_game_join_msg_settings(guild_id)
    
    if result is None:
        await interaction.response.send_message("No previous game join message found for this guild.", ephemeral=True)
        return
    
    old_message_id, old_channel_id = result

    # Fetch the old channel
    old_channel = interaction.guild.get_channel(old_channel_id)
    
    # Check if the old channel exists
    if old_channel is None:
        await interaction.response.send_message("The old channel where the join message was posted no longer exists.", ephemeral=True)
    else:
        # Try to fetch the old message
        try:
            old_message = await old_channel.fetch_message(old_message_id)
            await interaction.response.send_message(f"The old invite message still exists in {old_channel.mention}. Please delete it before updating. Directly link to message: {old_message.jump_url}", ephemeral=True)
            return  # Exit if the old message is still present
        except discord.NotFound:
            # The old message no longer exists, proceed to post a new one
            await interaction.response.send_message(f"Old invite message not found. Proceeding to post in {channel.mention}.", ephemeral=True)
        except discord.Forbidden:
            # If the bot doesn't have permission to view the old message
            await interaction.response.send_message(f"I do not have permission to access the old invite message in {old_channel.mention}.", ephemeral=True)
            return
        except discord.HTTPException:
            # Handle general errors fetching the message
            await interaction.response.send_message(f"An error occurred while trying to fetch the old invite message.", ephemeral=True)
            return

    # Post the new invite message in the specified channel
    new_invite_message = await channel.send("React with 🎃 to join the candy game and start your trick-or-treat adventure!")
    new_message_id = new_invite_message.id  # Get the new message ID
    new_channel_id = channel.id             # Get the new channel ID

    # Update the database with the new message and channel ID
    db_utils.set_game_join_msg_settings(guild_id, new_message_id, new_channel_id)

    # Confirm the new invite message is posted
    await interaction.followup.send(f"New invite message posted in {channel.mention}. Players can now react to join the game!", ephemeral=True)
