import discord
from discord import app_commands
from utils.checks import check_if_has_permission_or_role
from db_utils import get_active_players_by_guild
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
    outcome = roll_outcome(witch)
    selected = select_winners(candidates(players, witch, outcome), winners)
    if not selected:
        await interaction.response.send_message(
            message('cauldron', 'no_players'), ephemeral=True,
        )
        return
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
    if len(announcement) > 1900:
        import io
        # Preserve the full customized announcement when it exceeds Discord's content limit.
        attachment = announcement + '\n\n' + '\n'.join(f'{uid}: {name}' for uid, name in zip(selected, names))
        file = discord.File(io.BytesIO(attachment.encode()), filename='cauldron-winners.txt')
        summary = message('cauldron', 'long_announcement', **values)
        await interaction.response.send_message(summary[:1900], file=file, allowed_mentions=discord.AllowedMentions.none())
    else:
        await interaction.response.send_message(announcement, allowed_mentions=discord.AllowedMentions.none())
