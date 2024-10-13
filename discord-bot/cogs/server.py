import discord
import utils.checks as checks
from discord.ext import commands
from discord import app_commands
import db_utils
import logging

from cogs.set import set_group
from cogs.get import get_group
from cogs.delete import delete_group
from cogs.update import update_group

# importlib.reload(utils)
# importlib.reload(db_utils)

class RoleAccess(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Top-level group
    server = app_commands.Group(name="server", description="Moderator Commands")

    server.add_command(set_group)
    server.add_command(get_group)
    server.add_command(delete_group)
    server.add_command(update_group)
    

# Setup function to add the "cog" and the group
async def setup(bot):
    await bot.tree.add_command(RoleAccess.server) # Register the "server" group with Discord's API

# https://github.com/PaulMarisOUMary/Discord-Bot
