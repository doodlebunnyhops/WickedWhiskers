import discord
from discord import app_commands
from utils.checks import check_if_has_permission_or_role
import random
from db_utils import get_active_players_by_guild
from utils.player import calculate_evilness,calculate_sweetness

cast_group = app_commands.Group(name="cast", description="Cast commands")

#I need to also consider having the caauldron auto trigger when the pool reaches a certain amount
@check_if_has_permission_or_role()
@cast_group.command(name="spell", description="Trigger a spell on the cauldron!")
@app_commands.choices(
    witch=[
        app_commands.Choice(name="Luna", value="luna"),
        app_commands.Choice(name="Raven", value="raven")
    ],
    winners = [
        app_commands.Choice(name="Many", value="many"),
        # app_commands.Choice(name="Few", value="few"),
        app_commands.Choice(name="One", value="One")
    ])
@app_commands.describe(
    witch="The witch to cast the spell",
    winners="The number of winners"
)
async def cast_spell(interaction: discord.Interaction, witch: str, winners: str):
    # Fetch active players from the database by guild
    guild_id = interaction.guild.id
    players = get_active_players_by_guild(guild_id)
    weighted_players = []

    # Filter players based on the selected witch
    if witch == "luna":
        if random.random() < 0.15:  # 15% chance Luna fumbles, weigh sweet + potions purchased
            for player_id, candy_in_bucket, potions_purchased, treats_given, total_candy_given, successful_tricks, failed_tricks, total_candy_stolen in players:
                if potions_purchased > 0:
                    sweetness = max(calculate_sweetness(total_candy_given,treats_given), 1)
                    weighted_players.extend([player_id] * sweetness)
                    weighted_players.extend([player_id] * potions_purchased)
        elif random.random() < 0.10:  # 10% chance Luna is evil, weigh evilness + potions purchased LOL...maybe another day copilot
            #find the most sweet players, ignoring potions purchased
            for player_id, candy_in_bucket, potions_purchased, treats_given, total_candy_given, successful_tricks, failed_tricks, total_candy_stolen in players:
                #if potions_purchased > 0: # it's the most sweet player we aint counting this!
                sweetness = max(calculate_sweetness(total_candy_given,treats_given), 1)
                evilness = max(calculate_evilness(total_candy_stolen,failed_tricks), 1)
                if evilness < sweetness:
                    weighted_players.extend([player_id] * (sweetness - evilness))
        else: #regular luna weigh by potions purchased
            for player_id, candy_in_bucket, potions_purchased, treats_given, total_candy_given, successful_tricks, failed_tricks, total_candy_stolen in players:
                weighted_players.extend([player_id] * potions_purchased)
            
    elif witch == "raven":
        if random.random() < 0.15: #15% chance raven causes an explosion, weigh by trickery
            for player_id, candy_in_bucket, potions_purchased, treats_given, total_candy_given, successful_tricks, failed_tricks, total_candy_stolen in players:
                evilness = max(calculate_evilness(total_candy_stolen,successful_tricks), 1) #kinda evil, but not too evil
                if successful_tricks > 0:
                    weighted_players.extend([player_id] * evilness)
        elif random.random() < 0.10: #10% chance raven has a raging fit and wipes out the ..idk but she angry, weigh by pure evilness
            for player_id, candy_in_bucket, potions_purchased, treats_given, total_candy_given, successful_tricks, failed_tricks, total_candy_stolen in players:
                evilness = max(calculate_evilness(total_candy_stolen,(successful_tricks - failed_tricks)), 1) #utrla max evilness, like the joker MUWAHAHAA
                sweetness = max(calculate_sweetness(total_candy_given,treats_given), 1)
                if evilness > sweetness:
                    weighted_players.extend([player_id] * (evilness - sweetness))
        else: #regular raven weigh by trickery
            for player_id, candy_in_bucket, potions_purchased, treats_given, total_candy_given, successful_tricks, failed_tricks, total_candy_stolen in players:
                if successful_tricks > 0:
                    weighted_players.extend([player_id] * successful_tricks)

    # Determine winners
    if winners == "many":
        num_winners = random.randint(1, len(weighted_players))
        selected_winners = random.sample(weighted_players, num_winners)
    else:  # winners == "one"
        selected_winner = random.choice(weighted_players)
        selected_winners = [selected_winner]

 
    # Format the winners for the response
    for player_id in selected_winners:
        print(player_id)
        winner = interaction.guild.get_member(player_id).display_name

    winners = ", ".join([interaction.guild.get_member(winner).display_name for winner in selected_winners])
    await interaction.response.send_message(f"{witch} has cast a spell with {winners} winners!")