import logging

import discord
from db_utils import is_player_active
import utils.utils as utils
from discord import app_commands
from discord import Interaction



def check_if_has_permission_or_role():
    async def predicate(interaction: Interaction) -> bool:
        logging.debug("I'm checking perms...")
        guild_id = interaction.guild.id
        member = interaction.user

        # Check for permission or role (using your `has_role_or_permission` logic)
        if not utils.has_role_or_permission(member, guild_id):
            logging.info(f"{interaction.user.name} attempted '/{interaction.command.qualified_name}', denied for no permission or role")
            raise app_commands.CheckFailure("You do not have permission to use this command.")
            # return False (will be caught by global if not raised here)
        return True

    return app_commands.check(predicate)

def check_if_number_is_valid(min_value: int = 0, param_name: str = "amount"):
    """Check if a given number is greater than or equal to min_value."""
    async def predicate(interaction: discord.Interaction) -> bool:
        logging.debug("Validating number...")

        # Access the amount (or other parameter) from the interaction's namespace
        number = getattr(interaction.namespace, param_name)

        # Validate the number against the min_value
        if number < min_value:
            logging.info(f"Invalid number {number}, must be greater than or equal to {min_value}")
            raise app_commands.CheckFailure(f"The number must be greater than or equal to {min_value}.")
        
        return True

    return app_commands.check(predicate)

def check_if_player_is_active(target_arg: str = None):
    """Check if a player (either the user or the target) is active in the game."""
    async def predicate(interaction: discord.Interaction) -> bool:
        logging.debug("Checking if player is active...")

        guild_id = interaction.guild.id

        # Determine whether to check the interaction user or a target
        if target_arg:
            # Extract the target from interaction arguments
            target = interaction.namespace[target_arg]
            player_id = target.id
            player_name = target.display_name
        else:
            player_id = interaction.user.id
            player_name = interaction.user.display_name

        # Check if the player is active using db_utils
        if not is_player_active(player_id, guild_id):
            logging.info(f"{player_name} is inactive, command '{interaction.command.qualified_name}' denied.")
            raise app_commands.CheckFailure(f"{player_name} is not active in the game. Please rejoin to participate.")

        return True

    return app_commands.check(predicate)

def check_if_player_is_not_active():
    """Check if the player is not active in the game."""
    async def predicate(interaction: discord.Interaction) -> bool:
        logging.debug("Checking if player is not active...")

        guild_id = interaction.guild.id
        player_id = interaction.user.id

        # Check if the player is not active using db_utils
        if is_player_active(player_id, guild_id):
            logging.info(f"{interaction.user.name} is already active in the game.")
            raise app_commands.CheckFailure("You are already active in the game.")
        
        return True

    return app_commands.check(predicate)



