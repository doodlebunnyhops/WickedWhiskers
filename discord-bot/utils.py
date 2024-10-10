import discord
import db_utils
from functools import wraps

def cannot_target_self(param_name="user"):
    """
    Decorator to prevent the user from targeting themselves.
    :param param_name: The name of the argument that holds the target user (defaults to 'user').
    """
    def decorator(func):
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            # Get the interaction initiator (the person running the command)
            caller = interaction.user
            # Get the target user from the parameters
            target_user = kwargs.get(param_name)

            if target_user and caller.id == target_user.id:
                # Access the command name
                command_name = interaction.command.name

                # Customize the response based on the command
                if command_name == "give_treat":
                    message = "You can't give candy to yourself, no matter how tempting it is!"
                elif command_name == "trick":
                    message = "You can't trick yourself, even if you are _really_ sneaky!"
                else:
                    message = f"You cannot use the '{command_name}' command on yourself!"

                # Send the personalized message
                await interaction.response.send_message(message, ephemeral=True)
                return

            # Otherwise, proceed with the command
            await func(interaction, *args, **kwargs)

        return wrapper
    return decorator



def positive_number(param_name="amount"):
    """
    Decorator to check if the variable for amount is a positive integer.
    :param param_name: The name of the argument that holds the number value to check (defaults to 'amount').
    """
    def decorator(func):
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            amount = kwargs.get(param_name)
            if amount <= 0:
                await interaction.response.send_message(
                    "The amount must be a positive integer!", ephemeral=True
                )
            else:
                await func(interaction, *args, **kwargs)
        return wrapper
    return decorator

def requires_self_or_permission(param_name="user"):
    """
    Decorator to check if a user has the appropriate role or permission, 
    allowing users to check their own data but requiring permission for others.
    :param param_name: The name of the argument that holds the target user (defaults to 'user').
    """
    def decorator(func):
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            guild_id = interaction.guild.id
            caller = interaction.user  # The user initiating the command
            target_user = kwargs.get(param_name, caller)  # Get the target user (default to caller)

            # Allow if the caller is checking themselves
            if caller == target_user:
                await func(interaction, *args, **kwargs)
                return

            # Check if the caller has the appropriate role/permission to check others
            if not db_utils.has_role_or_permission(caller, guild_id):
                await interaction.response.send_message(
                    "You do not have permission to check other players' stats.", ephemeral=True
                )
            else:
                await func(interaction, *args, **kwargs)
        return wrapper
    return decorator


def requires_permission_or_role():
    """
    Decorator to check if a user has the appropriate role or permission.
    """
    def decorator(func):
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            guild_id = interaction.guild.id
            if not has_role_or_permission(interaction.user, guild_id):
                await interaction.response.send_message(
                    "You do not have permission to use this command!", ephemeral=True
                )
            else:
                await func(interaction, *args, **kwargs)
        return wrapper
    return decorator

from functools import wraps

def requires_active_player(check_initiator=False, check_target=False, param_name="user"):
    """
    Decorator to check if the initiator or target user (or both) are active in the game.
    Passes player data if available to the command via kwargs to avoid redundant DB calls.
    :param check_initiator: Whether to check if the interaction initiator is active.
    :param check_target: Whether to check if the target user is active.
    :param param_name: The name of the argument that holds the target user (defaults to 'user').
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            guild_id = interaction.guild.id
            player_data_initiator = None
            player_data_target = None

            # Check if the interaction initiator is active
            if check_initiator:
                player_data_initiator = db_utils.get_player_data(interaction.user.id, guild_id)
                if not db_utils.is_player_active(interaction.user.id, guild_id):
                    await interaction.response.send_message(
                        f"{interaction.user.mention}, you are not active in the game.", ephemeral=True
                    )
                    return

            # Check if the target user is active
            if check_target:
                target_user = kwargs.get(param_name)  # Retrieve the target user from kwargs
                if target_user is None:
                    await interaction.response.send_message(
                        f"Target user not found or not provided.", ephemeral=True
                    )
                    return

                player_data_target = db_utils.get_player_data(target_user.id, guild_id)
                if not db_utils.is_player_active(target_user.id, guild_id):
                    await interaction.response.send_message(
                        f"{target_user.name} is not active in the game.", ephemeral=True
                    )
                    return

            # Add player data to kwargs to pass to the command, but keep them hidden from the user
            kwargs["_player_data_initiator"] = player_data_initiator
            kwargs["_player_data_target"] = player_data_target

            # If all checks pass, proceed with the original command
            return await func(interaction, *args, **kwargs)

        return wrapper
    return decorator


def has_role_or_permission(member: discord.Member, guild_id):
    conn = db_utils.get_db_connection()
    cursor = conn.cursor()
    # Check if the member has Manage Guild permission
    if member.guild_permissions.manage_guild:
        return True

    # Fetch the allowed roles from the database
    cursor.execute("SELECT role_id FROM role_access WHERE guild_id = ?", (guild_id,))
    allowed_roles = [row[0] for row in cursor.fetchall()]

    # Check if the member has one of the allowed roles
    user_roles = [role.id for role in member.roles]
    return any(role_id in user_roles for role_id in allowed_roles)


# Function to send a message to the dynamically set events channel or fallback to interaction channel
async def post_event_message(bot, guild_id, message, interaction=None):
    event_channel_id = db_utils.get_event_channel(guild_id)
    
    # If an event channel is set, try to send the message there
    if event_channel_id:
        channel = bot.get_channel(event_channel_id)
        if channel:
            await channel.send(message)
            return

    # If no event channel is set or channel is invalid, send the message to the interaction channel
    if interaction:
        await interaction.channel.send(message)
    else:
        print("Error: No event channel or interaction channel available.")


# Function to send a message to the admin/mod channel
async def post_admin_message(bot, guild_id, message, interaction=None):
    admin_channel_id = db_utils.get_admin_channel(guild_id)
    if admin_channel_id:
        channel = bot.get_channel(admin_channel_id)
        if channel:
            await channel.send(message)
            return

    # If no admin channel is set or channel is invalid, send the message to the interaction channel
    if interaction:
        await interaction.channel.send(message)
    else:
        print("Error: No admin channel or interaction channel available.")


# Utility function to split long messages into chunks
def split_message(message, max_length=2000):
    # Split the message into chunks, each with a max length of 2000 characters
    return [message[i:i+max_length] for i in range(0, len(message), max_length)]
