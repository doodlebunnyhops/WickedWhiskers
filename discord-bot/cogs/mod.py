from discord.ext import commands
from discord import app_commands

from cogs.mod_commands.remove import remove_group
from cogs.mod_commands.update import update_group
from cogs.mod_commands.get import get_group
from cogs.mod_commands.set import set_group
from cogs.mod_commands.reset import reset_group

# importlib.reload(utils)
# importlib.reload(db_utils)

class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Top-level group
    cmds_group = app_commands.Group(name="zmod", description="Moderator Commands")

    cmds_group.add_command(set_group)
    cmds_group.add_command(get_group)
    cmds_group.add_command(remove_group)
    cmds_group.add_command(update_group)
    cmds_group.add_command(reset_group)
    

# Setup function to add the "cog" and the group
async def setup(bot):
    await bot.tree.add_command(Mod.cmds_group) # Register the "server" group with Discord's API