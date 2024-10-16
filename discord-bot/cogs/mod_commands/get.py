import logging
import discord
from discord import app_commands
import db_utils
import utils.checks as checks
from utils.utils import post_to_target_channel
from utils.helper import calculate_thief_success_rate

# Subcommand group for setting (used within the server group)
get_group = app_commands.Group(name="get", description="get commands")


@get_group.command(name="roles", description="Get all saved roles permitted to use restricted commands.")
@checks.check_if_has_permission_or_role()
async def get_role(interaction: discord.Interaction):
    logging.debug("role_access get command was triggered")
    # await interaction.response.send_message("Fetching roles...",delete_after=10,ephemeral=True)
    role_ids = db_utils.fetch_roles_by_guild(interaction.guild.id)

    # Log the fetched role IDs to verify
    logging.debug(f"Fetched role IDs: {role_ids}")
    if not role_ids:
        await interaction.response.send_message("No roles have been assigned access to restricted commands.", ephemeral=True)
        return

    # Get the role names from the guild and format them
    roles = [interaction.guild.get_role(role_id) for role_id in role_ids]
    valid_roles = [role.name for role in roles if role is not None]  # Filter out any roles that might have been deleted

    if not valid_roles:
        await interaction.response.send_message("None of the assigned roles exist in this guild anymore.", ephemeral=True)
        return
    
    role_names = ", ".join(valid_roles)

    #MessagingLoader
    personal_message = interaction.client.message_loader.get_message(
        "get_role", "personal_message", roles=role_names
    )
    admin_message = interaction.client.message_loader.get_message(
        "get_role","admin_messages", roles=role_names, user=interaction.user.name
    )
         # Respond with the formatted message
    await interaction.response.send_message(personal_message, ephemeral=True)
    await post_to_target_channel(interaction,admin_message,channel_type="admin")

@get_group.command(name="join_game_msg", description="Gets the link to the message where you can join the game.")
async def get_game_join_msg(interaction: discord.Interaction):
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
        #MessagingLoader
        personal_message = interaction.client.message_loader.get_message(
            "get_game_join_msg", "personal_message", channel=game_invite_channel.name,jump_url=game_invite_message.jump_url, user=interaction.user.name
        )
        admin_message = interaction.client.message_loader.get_message(
            "get_game_join_msg","admin_messages", channel=game_invite_channel.name,jump_url=game_invite_message.jump_url, user=interaction.user.name
        )

         # Respond with the formatted message
        await interaction.response.send_message(personal_message, ephemeral=True)
        await post_to_target_channel(interaction,admin_message,channel_type="admin")

    except discord.NotFound:
        # If the message was not found (deleted)
        await interaction.response.send_message("The game invite message no longer exists.", ephemeral=True)
    except discord.Forbidden:
        # If the bot does not have permission to access the message
        await interaction.response.send_message("I do not have permission to access the game invite message.", ephemeral=True)
    except discord.HTTPException:
        # General HTTP error
        await interaction.response.send_message("An error occurred while fetching the game invite message.", ephemeral=True)

# Slash Command to get the event or admin channel
@get_group.command(name="channel", description="Get the channel where event or admin messages will be posted.")
@checks.check_if_has_permission_or_role()
@app_commands.choices(channel_type=[
    app_commands.Choice(name="Event", value="event"),
    app_commands.Choice(name="Admin", value="admin"),
    app_commands.Choice(name="Both", value="both")
])
@app_commands.describe(
    channel_type="The type of channel to get (event, admin, or both)"
)
async def get_channel(interaction: discord.Interaction, channel_type: app_commands.Choice[str]):
    guild_id = interaction.guild.id

    # Initialize variables for the messages
    event_msg = None
    admin_msg = None

    event_channel = None
    admin_channel = None
    # Fetch the event channel if selected or if 'both' is selected
    if channel_type.value == "event" or channel_type.value == "both":
        event_channel_id = db_utils.get_event_channel(guild_id)
        event_channel = interaction.guild.get_channel(event_channel_id) if event_channel_id else None

        if not event_channel:
            event_msg = "The event channel is not set or I do not have access to it."
            await interaction.response.send_message(event_msg, ephemeral=True)
            return

    # Fetch the admin channel if selected or if 'both' is selected
    if channel_type.value == "admin" or channel_type.value == "both":
        admin_channel_id = db_utils.get_admin_channel(guild_id)
        admin_channel = interaction.guild.get_channel(admin_channel_id) if admin_channel_id else None

        if not admin_channel:
            admin_msg = "The admin channel is not set or I do not have access to it."
            await interaction.response.send_message(admin_msg, ephemeral=True)
            return

    personal_message = ""
    admin_message = ""
    # Combine the messages if 'both' is selected
    if channel_type.value == "both":

        #MessagingLoader
        personal_message = interaction.client.message_loader.get_message(
            "get_channel", "both_messages", "personal",event_channel=event_channel.name, admin_channel=admin_channel.name,user=interaction.user.name
        )
        admin_message = interaction.client.message_loader.get_message(
            "get_channel","both_messages", "admin",event_channel=event_channel.name, admin_channel=admin_channel.name,user=interaction.user.name
        )

    else:
        # Send individual messages based on selection
        if channel_type.value == "event":

            #MessagingLoader
            personal_message = interaction.client.message_loader.get_message(
                "get_channel", "personal_message",channel=event_channel.name,user=interaction.user.name, channel_type=channel_type.value
            )
            admin_message = interaction.client.message_loader.get_message(
                "get_channel","admin_messages",channel=event_channel.name,user=interaction.user.name, channel_type=channel_type.value
            )
        elif channel_type.value == "admin":

            #MessagingLoader
            personal_message = interaction.client.message_loader.get_message(
                "get_channel", "personal_message", channel=admin_channel.name,user=interaction.user.name, channel_type=channel_type.value
            )
            admin_message = interaction.client.message_loader.get_message(
                "get_channel","admin_messages", channel=admin_channel.name,user=interaction.user.name, channel_type=channel_type.value
            )

    # Respond with the formatted message
    await interaction.response.send_message(personal_message, ephemeral=True)
    await post_to_target_channel(interaction,admin_message,channel_type="admin")

@get_group.command(name="player", description="View a player's stats.")
@checks.check_if_has_permission_or_role()
@app_commands.choices(get=[
    app_commands.Choice(name="Stats", value="stats"),
    app_commands.Choice(name="Hidden Values", value="hidden_values"),
    app_commands.Choice(name="All", value="all")
])
@app_commands.describe(
    user="The user whose stats you want to view",
    get="The details you want to view (stats, hidden values, or both)"
)
async def get_player_stats(interaction: discord.Interaction, user: discord.Member, get: app_commands.Choice[str]):
    guild_id = interaction.guild.id
    # Fetch the player's stats from the database
    player_data = db_utils.get_player_data(user.id, guild_id)

    if player_data:
        try:
            candy_count, successful_steals, failed_steals, candy_given, tickets_purchased, active = list(player_data.values())
            active_status = "Active" if active == 1 else "Inactive"

            # Prepare the response based on the selected details option
            response_message = ""

            if get.value == "stats" or get.value == "all":
                # Standard player stats
                response_message += (
                    f"{user.display_name} has {candy_count} candy.\n"
                    f"Potions In Stock: {tickets_purchased}\n"
                    f"Successful steals: {successful_steals}\n"
                    f"Failed steals: {failed_steals}\n"
                    f"Candy given: {candy_given}\n"
                    f"Status: {active_status}\n"
                )
            
            if get.value == "hidden_values" or get.value == "all":
                # Hidden values
                # evilness, sweetness, trick_success_rate = hidden_values
                trick_success_rate = calculate_thief_success_rate(candy_count)
                response_message += (
                    f"Hidden Values:\n"
                    # f"Evilness: {evilness}\n"
                    # f"Sweetness: {sweetness}\n"
                    f"Trick Success Rate: {trick_success_rate*100}%\n"
                )

            await interaction.response.send_message(response_message, ephemeral=True)
        
        except Exception as e:
            logging.error(f"Error fetching player stats: {str(e)}")
            await interaction.response.send_message("An error occurred while fetching player stats.", ephemeral=True)
    
    else:
        await interaction.response.send_message(f"{user.display_name} has not joined the game yet.", ephemeral=True)
