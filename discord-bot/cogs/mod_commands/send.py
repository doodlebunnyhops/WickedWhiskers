import discord
from discord import app_commands
import db_utils as db
from utils.checks import check_if_has_permission_or_role
from utils.utils import create_invite_embed
from utils.join_message import seed_join_reaction
from admin_settings import text

send_group=app_commands.Group(name='post',description='Post game entry messages')


@send_group.command(name='join',description='Publish, refresh or move the pumpkin reaction join message')
@check_if_has_permission_or_role()
async def set_join_game_msg(interaction:discord.Interaction,channel:discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    old_id,old_channel_id=db.get_join_game_msg_settings(interaction.guild_id) or (None,None)
    old_channel=interaction.guild.get_channel(old_channel_id) if old_channel_id else None
    old=None
    try:
        if old_channel and old_id:
            try:old=await old_channel.fetch_message(old_id)
            except discord.NotFound:pass
        embed=create_invite_embed(interaction.client.message_loader)
        if old is not None and old_channel.id==channel.id:
            await old.edit(embed=embed)
            posted=old
        else:
            posted=await channel.send(embed=embed)
        db.set_join_game_msg_settings(interaction.guild_id,posted.id,channel.id)
        await seed_join_reaction(interaction,posted)
        if old is not None and old.id!=posted.id:
            try:await old.delete()
            except discord.NotFound:pass
            except discord.HTTPException:
                await interaction.followup.send(text('old_join_cleanup',url=old.jump_url),ephemeral=True)
        await interaction.followup.send(text('join_posted',url=posted.jump_url),ephemeral=True)
    except discord.HTTPException:
        await interaction.followup.send(text('join_failed'),ephemeral=True)
