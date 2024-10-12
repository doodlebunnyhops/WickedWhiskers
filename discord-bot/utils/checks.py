import logging
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