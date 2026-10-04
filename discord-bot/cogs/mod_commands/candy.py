import logging
import sqlite3
import discord
from discord import app_commands
import db_utils as db
from utils.utils import has_role_or_permission
from utils.mod_candy import adjust, CandyError

logger = logging.getLogger('bot')


@app_commands.command(name='candy', description='Give or take player candy without affecting gameplay or cauldron stats.')
@app_commands.guild_only()
@app_commands.describe(player='Player whose candy to adjust', action='Give or take candy', amount='Positive amount of candy', include_moderator='Include your name in the event announcement?')
@app_commands.choices(action=[app_commands.Choice(name='Give', value='give'), app_commands.Choice(name='Take', value='take')])
async def candy(interaction: discord.Interaction, player: discord.Member, action: app_commands.Choice[str], amount: app_commands.Range[int, 1, 9007199254740991], include_moderator: bool):
    message = interaction.client.message_loader.get_message
    async def reply(key, **values):
        await interaction.followup.send(message('mod_candy', key, **values), ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    if interaction.guild is None or not has_role_or_permission(interaction.user, interaction.guild.id):
        await reply('denied')
        return
    if player.guild.id != interaction.guild.id or player.bot:
        await reply('invalid_player')
        return
    channel = interaction.guild.get_channel(db.get_event_channel(interaction.guild.id))
    if channel is None:
        await reply('no_channel')
        return
    permissions = channel.permissions_for(interaction.guild.me)
    if not permissions.view_channel or not permissions.send_messages or not permissions.embed_links:
        await reply('channel_permissions')
        return
    try:
        result, repeated = adjust(interaction.guild.id, interaction.user.id, player.id, action.value, amount, include_moderator, interaction.id)
    except CandyError as error:
        await reply(str(error))
        return
    except sqlite3.Error:
        logger.exception('Moderator candy adjustment rolled back')
        await reply('failed')
        return
    if repeated:
        await reply('already_processed')
        return
    values = dict(player=player.mention, amount=result['amount'], moderator=interaction.user.mention)
    key = result['action'] + ('_named' if result['include_moderator'] else '_anonymous')
    embed = discord.Embed(title=message('mod_candy', 'title'), description=message('mod_candy', key, **values), color=discord.Color.orange())
    try:
        await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
    except discord.HTTPException:
        logger.exception('Moderator candy adjustment saved but event post failed')
        await reply('post_failed')
        return
    await reply('saved', **values)
