# -----------------------------------------------------------------------------
# Author: doodlebunnyhops
# Date: 10-07-2024
# Description: Utility functions to support discord bot.
# License: This file is part of a project licensed under the MIT License.
# Attribution: If you reuse or modify this code, please attribute the original
# creator, doodlebunnyhops, by referencing the source repository at 
# https://github.com/doodlebunnyhops.
# -----------------------------------------------------------------------------

import logging
import discord
import db_utils

# importlib.reload(db_utils)
logging.basicConfig(level=logging.DEBUG)

# print("utils.py is running")

def has_role_or_permission(member: discord.Member, guild_id):
    # Check if the member has Manage Guild permission
    if member.guild_permissions.manage_guild:
        return True

    # Fetch the allowed roles from the database
    allowed_roles = db_utils.fetch_roles_by_guild(guild_id)

    # Check if the member has one of the allowed roles
    user_roles = [role.id for role in member.roles]
    return any(role_id in user_roles for role_id in allowed_roles)

async def post_to_target_channel(interaction: discord.Interaction, message: str, channel_type: str = "event"):
    """
    Posts a message to the event or admin channel if set, otherwise posts in the interaction channel.
    
    Args:
        interaction (discord.Interaction): The interaction object to determine guild and channel.
        message (str): The message to be sent.
        channel_type (str): The type of channel to post to ("event" or "admin"). Defaults to "event".
    """
    guild_id = interaction.guild.id

    # Fetch the appropriate channel (event or admin) from the database
    if channel_type == "event":
        channel_id = db_utils.get_event_channel(guild_id)
    elif channel_type == "admin":
        channel_id = db_utils.get_admin_channel(guild_id)
    else:
        channel_id = None
    
    # Fetch the channel from the guild
    target_channel = interaction.guild.get_channel(channel_id) if channel_id else None

    # If target channel exists, send the message there
    if target_channel is not None:
        await target_channel.send(message)
    else:
        # Fallback to sending the message in the interaction channel
        if interaction.response.is_done():
            await interaction.followup.send(message)
        else:
            await interaction.response.send_message(message)
