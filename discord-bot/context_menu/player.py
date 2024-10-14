


import discord
from utils import checks
from discord import app_commands
from db_utils import is_player_active, create_player_data

# @app_commands.context_menu(name="Join Game")
# @checks.must_target_self()

async def join(interaction: discord.Interaction, member: discord.Member):
    guild_id = interaction.guild.id
    user = interaction.user
    target_user = member
    print(f"Caller: {user}, Target: {target_user}")

    if user.id != target_user.id:
        await interaction.response.send_message("You must target yourself for this command!", ephemeral=True)
        return

    if is_player_active(user.id, guild_id):
        await interaction.response.send_message(f"{user.mention}, you are already in the game! Use `/return` if you previously opted out.", ephemeral=True)
    else:
        try:
            create_player_data(user.id, guild_id)
            greeting_message = interaction.client.message_loader.get_message("join", "messages")
            await interaction.response.send_message(greeting_message.format(user=user.mention), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

    await interaction.response.send_message(f"{interaction.user.name} you selected {member.display_name}.", ephemeral=True)
