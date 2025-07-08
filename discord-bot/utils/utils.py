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
from utils.messages import MessageLoader


logging.basicConfig(level=logging.DEBUG)


def has_role_or_permission(member: discord.Member, guild_id):
    # Check if the member has Manage Guild permission
    if member.guild_permissions.manage_guild:
        return True

    # Fetch the allowed roles from the database
    allowed_roles = db_utils.fetch_roles_by_guild(guild_id)

    # Check if the member has one of the allowed roles
    user_roles = [role.id for role in member.roles]
    return any(role_id in user_roles for role_id in allowed_roles)

import discord

async def post_to_target_channel(interaction: discord.Interaction, message, channel_type: str = "event"):
    """
    Posts a message to the event or admin channel if set, otherwise posts in the interaction channel.
    
    Args:
        interaction (discord.Interaction): The interaction object to determine guild and channel.
        message (str or discord.Embed): The message to be sent, can be a string or an embed.
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

    # Determine if the message is an embed
    is_embed = isinstance(message, discord.Embed)

    # If target channel exists, send the message there
    if target_channel is not None:
        if is_embed:
            await target_channel.send(embed=message)
        else:
            await target_channel.send(message)
    else:
        # Fallback to sending the message in the interaction channel
        if interaction.response.is_done():
            if is_embed:
                await interaction.followup.send(embed=message)
            else:
                await interaction.followup.send(message)
        else:
            if is_embed:
                await interaction.response.send_message(embed=message)
            else:
                await interaction.response.send_message(message)

            
import random

def create_invite_embed(message_loader, message_choice=None):
    """
    Creates a uniform embed for the game invite using messages.json.
    
    Args:
        message_loader (MessageLoader): The MessageLoader instance to retrieve messages.
        message_choice (str, optional): The specific message ID to use. If None, a random message will be chosen.
    
    Returns:
        discord.Embed: The generated embed object.
    """
    # Fetch the entire block of react_join_msg
    message_block = message_loader.get_message_block("react_join_msg")
    
    if message_block is None:
        raise ValueError("No react_join_msg block available in messages.")

    # If message_choice is None, pick a random message ID from the available keys
    if message_choice is None:
        # Pick a random message ID from available keys if not provided
        message_choice = random.choice(list(message_block.keys()))
    else:
        # Ensure that the provided message_choice exists in the available keys
        if str(message_choice) not in message_block:
            raise ValueError(f"Message choice {message_choice} is not a valid option.")
    
    # Now we fetch the specific message using the selected message_choice
    title = message_loader.get_message("react_join_msg", message_choice, "title")
    description = message_loader.get_message("react_join_msg", message_choice, "description")
    helpful_commands_name = message_loader.get_message("react_join_msg", message_choice, "helpful_commands", "name")
    helpful_commands_value = message_loader.get_message("react_join_msg", message_choice, "helpful_commands", "value")

    # Create the embed
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.orange()
    )

    embed.add_field(
        name=helpful_commands_name,
        value=helpful_commands_value,
        inline=False
    )

    return embed


def create_embed(title: str = None, description: str = None, color: discord.Color = discord.Color.orange(),thumbnail_url=None,character=None,author_url=None,image_url=None):
    """
    Utility function to create a Discord embed.
    
    :param title: The title of the embed.
    :param description: The description or main content of the embed.
    :param color: The color of the embed. Default is blue.
    :param thumbnail_url: The URL of the thumbnail image.
    :param character: The character name for the author field.
    :param author_url: The URL of the author's image.
    :param image_url: The URL of the main image.
    :return: A discord.Embed object.
    """
    embed = discord.Embed(title=title, description=description, color=color)

    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    if character:
        embed.set_author(name=character)
        if author_url:
            embed.set_author(name=character, icon_url=author_url)
    if image_url:    
        embed.set_image(url=image_url)

    return embed

def create_character_embed(message_loader: MessageLoader, character: str = None,title: str = None, description: str = None, color: discord.Color = discord.Color.orange()):
    """
    Creates an embed for a character profile.
    
    Args:
        message_loader (MessageLoader): The MessageLoader instance to retrieve messages.
        character (str): The character name to generate the embed for.
        title (str): The title of the embed.
        description (str): The description of the character.
        color (discord.Color): The color of the embed.
           
    Returns:
        discord.Embed: The generated embed object.
    """
    if character is None:
        raise ValueError("Character data is required to create a character embed.")
 
    title = f"Meet {character}"
    author = character
    description = message_loader.get_message(f"who_is_{character.lower()}", "description")
    image_url = message_loader.get_message(f"who_is_{character.lower()}", "image_url")
    image_banner_url = message_loader.get_message(f"who_is_{character.lower()}", "image_banner_url")
    message = message_loader.get_message(f"who_is_{character.lower()}", "message")
    color = discord.Color.green()

    if character == "Luna":
        color = discord.Color.pink()
    else:
        color = discord.Color.dark_purple()
    embed = discord.Embed(title=title, color=color)
    embed.set_image(url=image_banner_url)
    embed.set_thumbnail(url=image_url)
    embed.set_author(name=character, icon_url=image_url)
    embed.add_field(name="", value=message, inline=False)

    # if image_url:
    #     embed.set_image(url=image_url)

    return embed