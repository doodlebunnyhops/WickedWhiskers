import discord
from discord import app_commands
from utils.checks import check_if_has_permission_or_role
from db_utils import get_active_players_by_guild, get_event_channel
from utils.cauldron import candidates, roll_outcome, select_winners

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
    if not permissions.view_channel or not permissions.send_messages:
        await interaction.response.send_message(message('cauldron', 'event_channel_denied'), ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    outcome = roll_outcome(witch)
    selected = select_winners(candidates(players, witch, outcome), winners)
    # Raw active database records may outlive guild membership. Never crash on a cache miss.
    names = []
    for uid in selected:
        member = interaction.guild.get_member(uid)
        names.append(discord.utils.escape_markdown(member.display_name) if member else message('cauldron', 'missing_member', player_id=uid))
    values = dict(
        witch=message('cauldron', 'witches', witch),
        outcome=message('cauldron', 'outcomes', outcome),
        winners=', '.join(names), winner_count=len(selected),
        user=interaction.user.mention,
    )
    announcement = message('cauldron', 'draw', witch, outcome, **values)
    file = None
    if len(announcement) > 1900:
        import io
        # Preserve the full customized announcement when it exceeds Discord's content limit.
        attachment = announcement + '\n\n' + '\n'.join(f'{uid}: {name}' for uid, name in zip(selected, names))
        file = discord.File(io.BytesIO(attachment.encode()), filename='cauldron-winners.txt')
        summary = message('cauldron', 'long_announcement', **values)
        announcement = summary[:1900]
    try:
        kwargs = {'allowed_mentions': discord.AllowedMentions.none()}
        if file is not None:
            kwargs['file'] = file
        posted = await channel.send(announcement, **kwargs)
    except discord.HTTPException:
        await interaction.followup.send(message('cauldron', 'event_post_failed', channel=channel.mention), ephemeral=True)
        return
    finally:
        if file is not None:
            file.close()
    await interaction.followup.send(message('cauldron', 'event_posted', channel=channel.mention, message_url=posted.jump_url), ephemeral=True)
