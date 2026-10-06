"""Public gameplay delivery; temporary private acknowledgement is removed on success."""
import logging
import re
import discord

MENTION = re.compile(r'<@!?(\d+)>')


def unique_mentions(message, interaction, members=()):
    """Mention each ID once across the assembled announcement, then use safe names."""
    known = {m.id:m for m in (interaction.user,*members) if m is not None}
    parts = [message] if isinstance(message,str) else [message.title or '',message.description or '',*[s for f in message.fields for s in (f.name,f.value)]]
    ids = {int(m) for part in parts for m in MENTION.findall(part)}
    names = {}
    for uid in ids:
        member = known.get(uid) or (interaction.guild.get_member(uid) if hasattr(interaction.guild,'get_member') else None)
        names[uid] = member.display_name[:64] if member else str(uid)
    seen = set()
    def replace(match):
        uid = int(match[1])
        if uid not in seen:
            seen.add(uid)
            return f'<@{uid}>'
        name=names[uid]
        if sum(n==name for n in names.values())>1:
            name=f'{name} ({uid})'
        # Escape mention syntax before inserting display names into the finished text.
        name=discord.utils.escape_mentions(name).replace('<@','<\u200b@')
        return discord.utils.escape_markdown(name)
    def clean(text):
        return MENTION.sub(replace,text)
    if isinstance(message,str):
        return clean(message)
    result=message.copy()
    if result.title:result.title=clean(result.title)
    if result.description:result.description=clean(result.description)
    for i,field in enumerate(result.fields):
        result.set_field_at(i,name=clean(field.name),value=clean(field.value),inline=field.inline)
    return result


async def publish_result(interaction, message, post, members=(), deferred=False):
    if not deferred and not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True,thinking=True)
    message=unique_mentions(message,interaction,members)
    try:
        await post(interaction,message,channel_type='event')
    except discord.HTTPException:
        logging.getLogger('bot').exception('Gameplay saved but public announcement failed')
        await interaction.edit_original_response(content=interaction.client.message_loader.get_message('gameplay_messages','post_failed'))
        return False
    try:
        await interaction.delete_original_response()
    except discord.HTTPException:
        logging.getLogger('bot').warning('Could not remove temporary gameplay acknowledgement')
    return True
