import discord
from discord import app_commands
import db_utils

class PlayerCommands:
    player = app_commands.Group(name="player", description="Player commands")

    @player.command(name="join", description="Join the candy game!")
    async def join_game(interaction: discord.Interaction):
        guild_id = interaction.guild.id
        user = interaction.user

        if db_utils.is_player_active(user.id, guild_id):
            await interaction.response.send_message(f"{user.mention}, you are already in the game! Use `/return` if you previously opted out.", ephemeral=True)
        else:
            try:
                db_utils.create_player_data(user.id, guild_id)
                greeting_message = interaction.client.message_loader.get_message("join", "messages")
                await interaction.response.send_message(greeting_message.format(user=user.mention), ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

# No need to inherit commands.Cog; we'll directly add this class to the tree in bot.py
