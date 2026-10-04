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
    players = get_active_players_by_guild(interaction.guild.id)
    outcome = roll_outcome(witch)
    selected = select_winners(candidates(players, witch, outcome), winners)
    if not selected:
        await interaction.response.send_message(
            'No active players are eligible in this server. Use /game get cauldron_eligibility to check. '
            'The cauldron pool has not changed.', ephemeral=True,
        )
        return
    # Raw active database records may outlive guild membership. Never crash on a cache miss.
    names = []
    for uid in selected:
        member = interaction.guild.get_member(uid)
        names.append(discord.utils.escape_markdown(member.display_name) if member else f'Player {uid}')
    announcement = f"{witch.title()} has cast a {outcome} spell! Winners: " + ', '.join(names)
    if len(announcement) > 1900:
        announcement = announcement[:1800] + f'… ({len(selected)} distinct winners total; full list attached)'
        import io
        file = discord.File(io.BytesIO('\n'.join(f'{uid}: {name}' for uid, name in zip(selected, names)).encode()), filename='cauldron-winners.txt')
        await interaction.response.send_message(announcement, file=file, allowed_mentions=discord.AllowedMentions.none())
    else:
        await interaction.response.send_message(announcement, allowed_mentions=discord.AllowedMentions.none())
