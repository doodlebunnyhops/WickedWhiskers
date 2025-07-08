import html
import logging
import discord
from discord import app_commands
import db_utils
import utils.checks as checks
from utils.player import calculate_evilness, calculate_sweetness
from utils.player import calculate_thief_success_rate

get_group = app_commands.Group(name="get", description="get commands")


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
        f"Potion Price: {potion_price} candy for 1 potion\n"
        f"Trick Success Rate: {trick_success_rate}%"
    )
    await interaction.response.send_message(response_message, ephemeral=True)

@get_group.command(name="cauldron", description="View how much is in the cauldron.")
@checks.check_if_has_permission_or_role()
async def get_cauldron_pool(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    # Fetch the cauldron pool from the database
    cauldron_pool = db_utils.get_cauldron_pool(guild_id)
    response_message = f"The cauldron currently has {cauldron_pool} candy."
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
    luna_banner = "https://cdn.discordapp.com/attachments/1293052178742644889/1296215769687785524/luna_banner.png?ex=6712cc02&is=67117a82&hm=ef0c794acb0a20732ff871fb5569dce4b4e6715d2b3bdef26b2a1590df9e55b8&"
    # leader_banner = "https://cdn.discordapp.com/attachments/1293052178742644889/1297018273128386593/file-2eM6TRxhaqj8KWU84Otbu0Ao.webp?ex=671465e5&is=67131465&hm=e90f476eee52384771aa0a426c1b94da0a07d862cf3ac5c76c4b1c634151659e&"
    leaderboard_type_descriptions = {
        "top_tricksters": "Trick(s)",
        "top_treaters": "Treat(s)",
        "top_thieves": "Candy Stolen",
        "most_generous": "Candy Given",
        "most_evil": "Evil",
        "most_sweet": "Sweet",
        "highest_risk_takers": "Risk Taken",
        "candy_hoarders": "Candy Hoarded",
        "all": "Points"  # Default for the 'all' type
        }
    leaderboard_as_percentage = {
        "most_sweet": True,
        "most_evil": True,
        "trick_success_rate": True
    }
    guild = interaction.guild
     # Fetch the leaderboard from the database
    leaderboard = db_utils.get_leaderboard_query(type.value, guild.id)

    if leaderboard:
        # Unicode variables for formatting
        zero_width_space = "\u200B"  # Invisible separator (zero-width space)
        colon_unicode = "\u003A"  # Unicode for colon (:)

        # Prepare the response message with a zero-width space at the beginning and the end
        response_message = "## \u200B" #zero_width_space and discord format double hash for big text on first player

        for i, (player_id, result) in enumerate(leaderboard):
            member = guild.get_member(player_id)

            # Get the description for this leaderboard type
            result_description = leaderboard_type_descriptions.get(type.value, "Result")

            # Determine if this leaderboard result should be displayed as a percentage
            if leaderboard_as_percentage.get(type.value, False):
                result_str = f"{result * 100:.2f}% {result_description}"
            else:
                result_str = f"{result} {result_description}"

            # Add the player and their result to the response message
            if member:
                response_message += f"**{i + 1}. {member.display_name}**: {result_str}\n\n{zero_width_space}"
            else:
                response_message += f"**{i + 1}. Player with ID {player_id}**: {result_str}\n\n{zero_width_space}"

        # Create the embed and set the description with the formatted response message
        embed = discord.Embed(
            title=f".:{type.name} Leaderboard:.",
            description=response_message,
            color=discord.Color.gold(),
        )
        embed.set_image(url=luna_banner)

        # Send the embed as the response message
        await interaction.response.send_message(embed=embed)

    else:
        # Send a response when no leaderboard data is found
        await interaction.response.send_message(
            f"No data found for **{type.name}** leaderboard.",
            ephemeral=True
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