from discord import app_commands
from discord.ext import commands

from cogs.game_commands.set import set_group
from cogs.game_commands.add import add_group
from cogs.game_commands.get import get_group
from cogs.game_commands.cast import cast_group

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.commands_to_toggle = ["join", "trick", "treat"]

    game_group = app_commands.Group(name="game",description="Game options and commands")
    
    game_group.add_command(set_group)
    game_group.add_command(add_group)
    game_group.add_command(get_group)
    game_group.add_command(cast_group)
    



async def setup(bot):
    await bot.tree.add_command(Game.game_group) 