import discord
from discord import app_commands
import db_utils as db
import potions
import player_state as state
from utils.checks import check_if_has_permission_or_role
from utils.utils import post_to_target_channel

reset_group = app_commands.Group(name='reset', description='Reset commands')


@reset_group.command(name='player',description='Reset player progress and explicitly remove their freeze.')
@check_if_has_permission_or_role()
async def reset_player(interaction:discord.Interaction,user:discord.Member):
    if db.get_player_data(user.id,interaction.guild.id) is None:
        await interaction.response.send_message(state.text('reset_missing'),ephemeral=True)
        return
    with db.transaction() as conn:
        previous=potions.prior_action(conn,interaction.guild.id,interaction.id,interaction.user.id,'admin_reset')
        if previous is None:
            db.reset_player_data(user.id,interaction.guild.id)
            potions.record_action(conn,interaction.guild.id,interaction.id,interaction.user.id,'admin_reset',dict(player_id=user.id))
    await interaction.response.send_message(state.text('reset_saved',player=user.mention),ephemeral=True)


async def reset_game(interaction:discord.Interaction):
    db.reset_cauldron_event(interaction.guild.id)
    await interaction.response.send_message(state.text('reset_pool'),ephemeral=True)
