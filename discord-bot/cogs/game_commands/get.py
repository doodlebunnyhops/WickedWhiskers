import html
import logging
import discord
from discord import app_commands
import db_utils
import utils.checks as checks
from utils.player import calculate_evilness, calculate_sweetness
from utils.player import calculate_thief_success_rate

get_group = app_commands.Group(name="get", description="get commands")


@get_group.command(name="cauldron_eligibility", description="Inspect eligibility for each cauldron outcome")
@checks.check_if_has_permission_or_role()
async def get_cauldron_eligibility(interaction: discord.Interaction):
    from utils.cauldron import eligibility_report

    message = interaction.client.message_loader.get_message
    players = db_utils.get_active_players_by_guild(interaction.guild.id)
    report = eligibility_report(players)
    embed = discord.Embed(
        title=message('cauldron', 'eligibility', 'title'),
        description=message('cauldron', 'eligibility', 'description', player_count=len(players), amount=db_utils.get_cauldron_pool(interaction.guild.id)),
        color=discord.Color.orange(),
    )
    for details in report.values():
        candidates = details['players']
        preview = ', '.join(message('cauldron', 'eligibility', 'candidate', player_id=uid, weight=weight) for uid, weight in candidates[:5]) or message('cauldron', 'eligibility', 'none')
        if len(candidates) > 5:
            preview += message('cauldron', 'eligibility', 'more', count=len(candidates)-5)
        rule = message('cauldron', 'eligibility', 'rules', details['witch'], details['outcome'])
        embed.add_field(
            name=message('cauldron', 'eligibility', 'outcome_title', witch=message('cauldron', 'witches', details['witch']), outcome=message('cauldron', 'outcomes', details['outcome']), chance=details['chance'], count=len(candidates)),
            value=message('cauldron', 'eligibility', 'field', rule=rule, candidates=preview),
            inline=False,
        )
    embed.add_field(name=message('cauldron', 'eligibility', 'notes_title'), value=message('cauldron', 'eligibility', 'notes'), inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())


@get_group.command(name="settings", description="View the game settings.")
@checks.check_if_has_permission_or_role()
async def get_game_settings(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    # Fetch the game settings from the database
    game_disabled, potion_price, trick_success_rate, *_ = db_utils.get_game_settings(guild_id)

    # Prepare the response message
    trick_success_rate = round(trick_success_rate, 2)
    response_message = (
        f"Player Game Commands: {'Disabled' if game_disabled == 1 else 'Enabled'}\n"
        "Potion prices: use /shop browse or /shop manage\n"
        f"Trick Success Rate: {trick_success_rate}%"
    )
    await interaction.response.send_message(response_message, ephemeral=True)

@get_group.command(name="cauldron", description="View how much is in the cauldron.")
@checks.check_if_has_permission_or_role()
async def get_cauldron_pool(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    # Fetch the cauldron pool from the database
    cauldron_pool = db_utils.get_cauldron_pool(guild_id)
    response_message = interaction.client.message_loader.get_message("cauldron", "pool", "get", amount=cauldron_pool)
    await interaction.response.send_message(response_message, ephemeral=True)


@get_group.command(name="player", description="View a player's stats.")
@checks.check_if_has_permission_or_role()
@app_commands.choices(get=[
    app_commands.Choice(name="Stats", value="stats"),
    app_commands.Choice(name="Hidden Values", value="hidden_values"),
    app_commands.Choice(name="All", value="all")
])
@app_commands.describe(
    user="The user whose stats you want to view",
    get="The details you want to view (stats, hidden values, or both)"
)
async def get_player_stats(interaction: discord.Interaction, user: discord.Member, get: app_commands.Choice[str]):
    from utils.player_stats import player_stats_embeds
    embeds = player_stats_embeds(interaction, user, get.value)
    if embeds:
        await interaction.response.send_message(embeds=embeds, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
    else:
        await interaction.response.send_message(interaction.client.message_loader.get_message('player_stats','not_joined',user=user.mention),ephemeral=True)


@get_group.command(name="leaderboard", description="View the leaderboard.")
@checks.check_if_has_permission_or_role()
@app_commands.choices(type=[
    app_commands.Choice(name="Top Tricksters", value="top_tricksters",),
    app_commands.Choice(name="Top Treaters", value="top_treaters"),
    app_commands.Choice(name="Top Thieves", value="top_thieves"), 
    app_commands.Choice(name="Most Generous", value="most_generous"),
    app_commands.Choice(name="Most Evil", value="most_evil"),
    app_commands.Choice(name="Most Sweet", value="most_sweet"),
    app_commands.Choice(name="Highest Risk Takers", value="highest_risk_takers"),
    app_commands.Choice(name="Candy Hoarders", value="candy_hoarders"),
    app_commands.Choice(name="Potion Collector", value="potion_collector"),
    app_commands.Choice(name="Biggest Spender", value="biggest_spender"),
    app_commands.Choice(name="Master of Potions", value="master_of_potions"),
    app_commands.Choice(name="Luna’s Favorites", value="lunas_favorites"),
    app_commands.Choice(name="Untouchable", value="untouchable"),
    app_commands.Choice(name="Cauldron Contributors", value="cauldron_contributors"),
    app_commands.Choice(name="Pumpkin Smashers", value="pumpkin_smashers"),
    app_commands.Choice(name="All", value="all")
    ])
async def get_leaderboard(interaction: discord.Interaction, type: app_commands.Choice[str]):
    from utils.leaderboard import CATEGORIES, LeaderboardView, make_embed

    admin_channel_id = db_utils.get_admin_channel(interaction.guild.id)
    in_admin_channel = bool(admin_channel_id) and interaction.channel_id == admin_channel_id

    if type.value == 'all':
        boards = {key: db_utils.get_leaderboard_query(key, interaction.guild.id) for key in CATEGORIES}
        if not any(boards.values()):
            await interaction.response.send_message(
                interaction.client.message_loader.get_message('leaderboard', 'empty_all'), ephemeral=True,
            )
            return
        view = LeaderboardView(interaction, boards)
        await interaction.response.send_message(embed=view.embed(), view=view, ephemeral=not in_admin_channel, allowed_mentions=discord.AllowedMentions.none())
    else:
        event_channel_id = db_utils.get_event_channel(interaction.guild.id)
        in_event_channel = bool(event_channel_id) and interaction.channel_id == event_channel_id
        rows = db_utils.get_leaderboard_query(type.value, interaction.guild.id)
        await interaction.response.send_message(
            embed=make_embed(interaction, type.value, rows),
            ephemeral=not (rows and (in_admin_channel or in_event_channel)), allowed_mentions=discord.AllowedMentions.none(),
        )


def display_leaderboard(interaction, leaderboard, title):
    embed = discord.Embed(title=title, color=discord.Color.purple())
    for idx, player in enumerate(leaderboard[:10], start=1):
        embed.add_field(name=f"#{idx} {player['player_name']}", value=f"Score: {player['trick_success_rate']}%", inline=False)

    return embed

def sanitize_string(input_string: str) -> str:
    """
    Sanitize a string by escaping HTML characters and removing potentially invalid characters.
    This ensures no unexpected formatting issues in Discord embeds.
    """
    # Escape HTML characters like <, >, &
    sanitized = html.escape(input_string)
    
    # Optionally, remove unwanted characters like non-printable or problematic Unicode
    sanitized = ''.join(c for c in sanitized if c.isprintable())
    
    return sanitized
