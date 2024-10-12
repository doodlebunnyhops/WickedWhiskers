import logging
import discord
from discord import app_commands
from db_utils import create_player_data, update_player_field,get_player_data
import utils.checks as checks
from utils.utils import post_to_event_or_interaction_channel
from discord.ext import commands

class PlayerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Top-level group
    player= app_commands.Group(name="player", description="player commands")


    @player.command(name="bond", description="Join the ghoulish feast of candy!")
    # @checks.check_if_player_is_not_active()  # Ensure the player is not already active
    async def player_join(self, interaction: discord.Interaction):
        player_id = interaction.user.id
        guild_id = interaction.guild.id

        # Check if the player is already in the game
        # cursor.execute('SELECT * FROM players WHERE player_id = ? AND guild_id = ?', (player_id, guild_id))
        result = get_player_data(player_id,guild_id)

        if result:
            await interaction.response.send_message(f"{interaction.user.mention}, you are already in the game! Use /optin if you previously opted out.", ephemeral=True)
        else:
            # Insert the new player into the database with default values (50 candy and 0 tickets purchased)
            # cursor.execute('INSERT INTO players (player_id, guild_id, candy_count, successful_steals, failed_steals, candy_given, active, tickets_purchased, frozen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', 
            #             (player_id, guild_id, 50, 0, 0, 0, 1, 0, 0))
            # conn.commit()
            create_player_data(player_id,guild_id)

            await interaction.response.send_message(f"Welcome {interaction.user.mention}! You have started with 50 candy. Will you trick or treat others :thinking:?", ephemeral=True)



    @player.command(name="give_treat", description="Give a treat to another player.")
    @checks.check_if_player_is_active(target_arg="target")  # Checks if the target is active
    @checks.check_if_player_is_active()  # Checks if the player is active
    @checks.check_if_number_is_valid()   # Checks if the amount is 0 or greater
    async def give_treat(self,interaction: discord.Interaction, target: discord.Member, amount: int):
        guild_id = interaction.guild.id
        player_id = interaction.user.id
        target_id = target.id

        ###this needs to fetch add then db_utils.update_player_field(player_id, guild_id, field, value): for both user and target

        # Perform the logic for giving candy to the target
        # give_candy_to_player(target_id, guild_id, amount)

            # Format the message using the helper function
        message = self.bot.message_loader.get_message(
            "give_treat", "event_messages", amount, "else",
            user=interaction.user.mention, target=target.mention, amount=amount
        )

        # Use the helper function to post the message
        await post_to_event_or_interaction_channel(interaction, message)
    
    # player.add_command(player_join)
    # server.add_command(get_group)
    # server.add_command(delete_group)
    # server.add_command(update_group)
# Setup function to add the "cog" and the group
async def setup(bot):
    await bot.tree.add_command(PlayerCommands.player) # Register the "server" group with Discord's API
