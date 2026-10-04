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
    guild_id = interaction.guild.id
    # Fetch the player's stats from the database
    player_data = db_utils.get_player_data(user.id, guild_id)

    if player_data:
        try:
            candy_in_bucket = player_data.get('candy_in_bucket', 0)
            successful_tricks = player_data.get('successful_tricks', 0)
            failed_tricks = player_data.get('failed_tricks', 0)
            treats_given = player_data.get('treats_given', 0)
            potions_purchased = player_data.get('potions_purchased', 0)
            total_candy_given = player_data.get('total_candy_given', 0)
            total_candy_stolen = player_data.get('total_candy_stolen', 0)
            total_candy_lost = player_data.get('total_candy_lost', 0)
            active = player_data.get('active', 0)


            
            active_status = "Active" if active == 1 else "Inactive"

            # Prepare the response based on the selected details option
            response_message = ""

            if get.value == "stats" or get.value == "all":
                # Standard player stats
                response_message += (
                    f"**{user.display_name} Stats:**\n\n"
                    f"Bucket Contents:"
                    f"\tCandy: {candy_in_bucket} candy.\n"
                    f"\tPotions: {potions_purchased}\n\n"
                    f"Tricerky Stats:\n"
                    f"\tSuccessful Tricks: {successful_tricks}\n"
                    f"\tFailed Tricks: {failed_tricks}\n"
                    f"\tTotal Tricks: {successful_tricks + failed_tricks}\n"
                    f"\tTotal candy stolen: {total_candy_stolen}\n\n"
                    f"Treats Stats:\n"
                    f"\t# Times Treated: {treats_given}\n"
                    f"\tTotal candy given: {total_candy_given}\n\n"
                    f"Other:\n"
                    f"\tCandy lost: {total_candy_lost}\n"
                    f"\tStatus: {active_status}\n"
                )
            
            if get.value == "hidden_values" or get.value == "all":
                # Hidden values
                # evilness, sweetness, trick_success_rate = hidden_values
                evilness = calculate_evilness(total_candy_given, total_candy_stolen)
                sweetness = calculate_sweetness(total_candy_given, total_candy_stolen)
                trick_success_rate = calculate_thief_success_rate(candy_in_bucket)

                response_message += (
                    f"**Hidden Values:**\n"
                    f"\tEvilness: {round(evilness*100, 2)}%\n"
                    f"\tSweetness: {round(sweetness*100, 2)}%\n"
                    f"\tTrick Success Rate: {round(trick_success_rate*100, 2)}%\n"
                )

            await interaction.response.send_message(response_message, ephemeral=True)
        
        except Exception as e:
            logging.error(f"Error fetching player stats: {str(e)}")
            await interaction.response.send_message("An error occurred while fetching player stats.", ephemeral=True)
    
    else:
        await interaction.response.send_message(f"{user.display_name} has not joined the game yet.", ephemeral=True)



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
    app_commands.Choice(name="All", value="all")
    ])
async def get_leaderboard(interaction: discord.Interaction, type: app_commands.Choice[str]):
    from utils.leaderboard import CATEGORIES, LeaderboardView, make_embed

    if type.value == 'all':
        boards = {key: db_utils.get_leaderboard_query(key, interaction.guild.id) for key in CATEGORIES}
        if not any(boards.values()):
            await interaction.response.send_message(
                interaction.client.message_loader.get_message('leaderboard', 'empty_all'), ephemeral=True,
            )
            return
        view = LeaderboardView(interaction, boards)
        await interaction.response.send_message(embed=view.embed(), view=view, allowed_mentions=discord.AllowedMentions.none())
    else:
        rows = db_utils.get_leaderboard_query(type.value, interaction.guild.id)
        await interaction.response.send_message(
            embed=make_embed(interaction, type.value, rows),
            ephemeral=not bool(rows), allowed_mentions=discord.AllowedMentions.none(),
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
