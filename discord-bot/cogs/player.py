import logging
import discord
from discord import app_commands
from db_utils import create_player_data, update_player_field,get_player_data
import utils.checks as checks
from utils.utils import post_to_target_channel
from discord.ext import commands

class PlayerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Top-level group
    player= app_commands.Group(name="player", description="player commands")
    

    # @checks.check_if_player_is_active(target_arg="target")  # Checks if the target is active
    # @checks.check_if_player_is_active()  # Checks if the player is active
    # @checks.check_if_number_is_valid()   # Checks if the amount is 0 or greater
    # @app_commands.command(name="give_treat", description="Give a treat to another player.")
    @player.command(name="give_treat", description="Give a treat to another player.")
    async def give_treat(self,interaction: discord.Interaction, target: discord.Member, amount: int):
        # Use the helper function to post the message
        await post_to_target_channel(interaction, "Give Treat message...")

    # @app_commands.command(name="hop", description="Join the ghoulish feast of candy!")
    @player.command(name="join", description="Join the ghoulish feast of candy!")
    async def player_join(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Welcome {interaction.user.mention}! You have started with 50 candy. Will you trick or treat others :thinking:?", ephemeral=True)


    
    # player.add_command(give_treat)
    # player.add_command(player_join)
    # server.add_command(delete_group)
    # server.add_command(update_group)
# Setup function to add the "cog" and the group
async def setup(bot):
    await bot.tree.add_command(PlayerCommands.player) # Register the "server" group with Discord's API
