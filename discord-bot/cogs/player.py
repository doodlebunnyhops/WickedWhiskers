from discord import app_commands
from discord.ext import commands
import discord
from utils import helper
# from slashcmds.subgroup import subgroup
# from cogs.subgroup import subgroup

class Player(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # group = app_commands.Group(name="group1",description="...")
    # subgroup = app_commands.Group(name="subgroup",description="...")
    # group.add_command(subgroup)

    @app_commands.command(name="join", description="Join the game!")
    async def join(self, interaction: discord.Interaction):
        await helper.player_join(interaction,None)

    @app_commands.command(name="trick", description="Trick a player into giving you candy!")
    async def join(self, interaction: discord.Interaction, member: discord.Member):
        await helper.player_trick(interaction,member)


async def setup(bot):
    await bot.add_cog(Player(bot))