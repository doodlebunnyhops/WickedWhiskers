


import discord
from utils import helper

# @app_commands.context_menu(name="Join Game")
# @checks.must_target_self()

async def join(interaction: discord.Interaction, member: discord.Member):
    await helper.player_join(interaction, member)

async def trick(interaction: discord.Interaction, member: discord.Member):
    await helper.player_trick(interaction, member)