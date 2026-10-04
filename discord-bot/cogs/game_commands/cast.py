import discord
import logging
import sqlite3
from discord import app_commands
from utils.checks import check_if_has_permission_or_role
from db_utils import get_active_players_by_guild, get_event_channel
from utils.cauldron import award_pool, CauldronError

cast_group = app_commands.Group(name='cast', description='Cast commands')


@cast_group.command(name='spell', description='Trigger a spell on the cauldron!')
@check_if_has_permission_or_role()
@app_commands.choices(
    witch=[app_commands.Choice(name='Luna', value='luna'), app_commands.Choice(name='Raven', value='raven')],
    winners=[app_commands.Choice(name='Many', value='many'), app_commands.Choice(name='One', value='One')],
)
@app_commands.describe(witch='The witch to cast the spell', winners='The number of distinct winners')
async def cast_spell(interaction: discord.Interaction, witch: str, winners: str):
    message = interaction.client.message_loader.get_message
    players = get_active_players_by_guild(interaction.guild.id)
    if not players:
        await interaction.response.send_message(message('cauldron', 'no_players'), ephemeral=True)
        return
    channel_id = get_event_channel(interaction.guild.id)
    channel = interaction.guild.get_channel(channel_id) if channel_id else None
    if channel is None:
        await interaction.response.send_message(message('cauldron', 'event_channel_missing'), ephemeral=True)
        return
    permissions = channel.permissions_for(interaction.guild.me)
    if not all((permissions.view_channel, permissions.send_messages, permissions.embed_links, permissions.attach_files)):
        await interaction.response.send_message(message('cauldron', 'event_channel_denied'), ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        result, repeated = award_pool(interaction.guild.id, interaction.id, interaction.user.id, witch, winners)
    except CauldronError as error:
        await interaction.followup.send(message('cauldron', str(error)), ephemeral=True)
        return
    except sqlite3.Error:
        logging.getLogger('bot').exception('Cauldron payout rolled back for guild %s', interaction.guild.id)
        await interaction.followup.send(message('cauldron', 'payout_failed'), ephemeral=True)
        return
    if repeated:
        await interaction.followup.send(message('cauldron', 'already_paid', amount=result['amount']), ephemeral=True)
        return
    outcome = result['outcome']
    names = []
    for award in result['awards']:
        uid = award['player_id']
        member = interaction.guild.get_member(uid)
        name = discord.utils.escape_markdown(member.display_name) if member else message('cauldron', 'missing_member', player_id=uid)
        names.append(name)
    values = dict(
        witch=message('cauldron', 'witches', witch), outcome=message('cauldron', 'outcomes', outcome),
        winners=', '.join(names), winner_count=len(names), user=interaction.user.mention,
        amount=result['amount'], remaining=result['remaining'],
    )
    announcement = message('cauldron', 'draw', witch, outcome, **values)
    file = None
    if len(announcement) > 3800:
        import io
        attachment = announcement
        file = discord.File(io.BytesIO(attachment.encode()), filename='cauldron-winners.txt')
        announcement = message('cauldron', 'long_announcement', **values)[:1900]
    embed = discord.Embed(
        title=message('cauldron', 'embed', 'title', **values)[:256],
        description=announcement,
        color=discord.Color.magenta() if witch == 'luna' else discord.Color.dark_purple(),
    )
    embed.set_image(url=message(f'who_is_{witch}', 'image_url'))
    embed.set_author(name=values['witch'])
    embed.add_field(name=message('cauldron', 'embed', 'pool_title')[:256], value=message('cauldron', 'embed', 'pool_value', **values)[:1024], inline=False)
    try:
        kwargs = {'embed': embed, 'allowed_mentions': discord.AllowedMentions.none()}
        if file is not None:
            kwargs['file'] = file
        posted = await channel.send(**kwargs)
    except discord.HTTPException:
        await interaction.followup.send(message('cauldron', 'event_post_failed', channel=channel.mention, **values), ephemeral=True)
        return
    finally:
        if file is not None:
            file.close()
    await interaction.followup.send(message('cauldron', 'event_posted', channel=channel.mention, message_url=posted.jump_url, **values), ephemeral=True)
