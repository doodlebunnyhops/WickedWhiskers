import discord
from discord import app_commands
from db_utils import reset_player_data,reset_lottery_pool,get_player_data,get_lottery_pool,get_admin_channel,set_player_inactive
from utils.checks import check_if_has_permission_or_role
from utils.utils import post_to_target_channel

reset_group = app_commands.Group(name="reset", description="Reset commands")


@reset_group.command(name="player", description="Factory Reset a player")
@check_if_has_permission_or_role()
async def reset_player(interaction: discord.Interaction, user: discord.Member):
    guild_id = interaction.guild.id

    user_data = get_player_data(user.id, guild_id)
    # Respond with the formatted message
    title = f"Player {user.display_name}'s stats before reset"
    description = f"Resetting player initiated by {interaction.user.mention}.\nHere are their stats before reset. Take note that if they were inactive or frozen they will have to join back or you may want to follow up with a `/freeze`:\n\n"
    helpful_commands_name = ":eyes:"
    helpful_commands_value = f"- Candy Bucket:\t{user_data['candy_count']}\n- Successful Tricks:\t{user_data['successful_steals']}\n - Failed Tricks:\t{user_data['failed_steals']}\n - Treats Given:\t{user_data['candy_given']}\n - Potions Purchased:\t{user_data['tickets_purchased']}"

    # Create the embed
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.red()
    )

    embed.add_field(
        name=helpful_commands_name,
        value=helpful_commands_value,
        inline=False
    )

    
    admin_channel_id = get_admin_channel(guild_id)
    if admin_channel_id:
        channel = interaction.guild.get_channel(admin_channel_id)
    else:
        channel = interaction.channel
    await channel.send(embed=embed)

    await interaction.response.send_message(f"Resetting player {user.display_name} now...", ephemeral=True)

    reset_player_data(user.id,guild_id)
    # set_player_inactive(user.id,guild_id)

    await channel.send(f"Player {user.display_name} has been reset.")