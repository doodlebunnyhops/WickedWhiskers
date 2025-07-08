


import discord
from utils import shop

# @app_commands.context_menu(name="Join Game")
# @checks.must_target_self()

async def buy_potion(interaction: discord.Interaction, member: discord.Member):
    await shop.buy_potion(interaction, member)
