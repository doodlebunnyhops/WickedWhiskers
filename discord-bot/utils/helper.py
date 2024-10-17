import random
import discord
import settings

from discord import InteractionType, AppCommandType
from db_utils import is_player_active, create_player_data,get_player_data,update_player_field,update_cauldron_event
from utils.utils import post_to_target_channel,create_embed
from utils.checks import get_game_settings


logger = settings.logging.getLogger("bot")
luna_url = "https://cdn.discordapp.com/attachments/1293052178742644889/1296199541670019133/DALLE_2024-10-16_15.07.46_-_A_cartoon_image_of_Luna_a_kind_and_ethereal_witch._She_has_soft_glowing_features_with_bright_twinkling_eyes_and_long_flowing_silvery_hair_resemblin.webp?ex=67116b64&is=671019e4&hm=ecaecab071be31abcbff4a9af69fa4863a17e09ab2711d2b8208d76e7baec8ff&"
raven_url = "https://cdn.discordapp.com/attachments/1293052178742644889/1296199541158182912/DALLE_2024-10-16_15.07.44_-_A_cartoon_image_of_Raven_the_mischievous_and_dark-hearted_witch._Raven_has_sharp_angular_features_with_glowing_red_eyes_and_long_wild_black_hair_st.webp?ex=67116b64&is=671019e4&hm=d73877b572138632c5cdeb572f0784ba6423ad1d6a1f980587d9eb1a3eeb3eef&"

async def player_join(interaction: discord.Interaction,member: discord.Member):
    guild_id = interaction.guild.id
    game_disabled, _,_ = get_game_settings(guild_id)
    if game_disabled:
        print(f"Game is disabled for guild {guild_id}")
        await interaction.response.send_message("The game is currently paused.", ephemeral=True)
        return
    user = interaction.user
    target_user = member
    
    if target_user:
        if interaction.user.id != target_user.id:
            print(f"After Check:\tCaller: {user}, Target: {target_user}")
            await interaction.response.send_message("You must target yourself for this command!", ephemeral=True)
            return

    if is_player_active(user.id, guild_id):
        await interaction.response.send_message(f"{user.mention}, you are already in the game! Use `/return` if you previously opted out.", ephemeral=True)
        return
    else:
        try:
            create_player_data(user.id, guild_id)
            greeting_message = interaction.client.message_loader.get_message("join", "messages", user=user.mention)
            await interaction.response.send_message(greeting_message.format(user=user.mention), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)


async def player_trick(interaction: discord.Interaction,member: discord.Member):
    guild_id = interaction.guild.id
    game_disabled, _,_ = get_game_settings(guild_id)
    if game_disabled:
        print(f"Game is disabled for guild {guild_id}")
        await interaction.response.send_message("The game is currently paused.", ephemeral=True)
        return
    user = interaction.user
    target = member

    if not is_player_active(user.id, guild_id):
        await interaction.response.send_message(f"{user.mention}, you must join the game to participate! /join", ephemeral=True)
        return
    if not target:
        await interaction.response.send_message(f"{user.mention}, you must target a player for this command!", ephemeral=True)
        return
    if interaction.user.id == target.id:
        await interaction.response.send_message(f"{user.mention}, you can't target yourself for this command!", ephemeral=True)
        return
    if not is_player_active(target.id, guild_id):
        await interaction.response.send_message(f"{target.display_name} is not in the game!", ephemeral=True)
        return

    #renaming for easier reference
    thief_id = interaction.user.id
    target_id = target.id
    
    thief_data = get_player_data(thief_id, guild_id)
    target_data =get_player_data(target_id, guild_id)

    #Scenarios where target has no candy to have stolen
    if target_data["candy_in_bucket"] == 0:
        # Target has no candy, special handling
        if thief_data["candy_in_bucket"] > 5 and random.random() < 0.05:  # 5% chance thief feels bad and gives some candy
            given_candy = random.randint(1, min(5, thief_data["candy_in_bucket"] - 5))  # Give between 1 and 5 candy
            if given_candy == 1:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "no_candy","thief_gives_candy", "1", user=interaction.user.mention, target=target.mention)
            if given_candy == 2:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "no_candy","thief_gives_candy", "2", user=interaction.user.mention, target=target.mention)
            if given_candy == 3: 
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "no_candy","thief_gives_candy", "3", user=interaction.user.mention, target=target.mention)
            if given_candy == 4:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "no_candy","thief_gives_candy", "4", user=interaction.user.mention, target=target.mention)
            if given_candy == 5:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "no_candy","thief_gives_candy", "5", user=interaction.user.mention, target=target.mention)
            
            update_player_field(thief_id, guild_id, 'candy_in_bucket', thief_data["candy_in_bucket"] - given_candy)
            update_player_field(target_id, guild_id, 'candy_in_bucket', target_data["candy_in_bucket"] + given_candy)
            update_player_field(thief_id, guild_id, 'failed_tricks', thief_data["failed_tricks"] + 1)
            personal_message = f"{interaction.user.display_name}, you felt so bad for {target.display_name}'s empty stash that you gave {given_candy} candy out of sympathy! You failed the trick, but you gained a friend maybe?"
            
            embeded_message = create_embed(f"{user.display_name} Failed to Trick {target.display_name}",embeded_message,discord.Color.dark_purple(),raven_url,"Raven",None)
            await interaction.response.send_message(personal_message, ephemeral=True)
            await post_to_target_channel(channel_type="event", message=embeded_message, interaction=interaction)
        elif random.random() < 0.03:  # 3% chance of ghastly duel and candy vanishes into the lottery
            duel_candy = random.randint(50, 1000)
            #if duel candy is between 50 and 100
            if duel_candy >= 50 and duel_candy <= 100:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "no_candy","duel", "50-100", user=interaction.user.mention, target=target.mention)
            #if duel_candy is between 101 and 300
            elif duel_candy >= 101 and duel_candy <= 300:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "no_candy","duel", "101-300", user=interaction.user.mention, target=target.mention)
            elif duel_candy >= 301 and duel_candy <= 600:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "no_candy","duel", "301-600", user=interaction.user.mention, target=target.mention)
            elif duel_candy >= 601:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "no_candy","duel", "601+", user=interaction.user.mention, target=target.mention)
            update_player_field(thief_id, guild_id, 'failed_tricks', thief_data["failed_tricks"] + 1)
            update_cauldron_event(guild_id, duel_candy)
            personal_message = f"{interaction.user.display_name}, you tried to trick {target.display_name} but you got into a fight instead! No candy was stolen :( The candy vanished into the cauldron!"
            
            embeded_message = create_embed(f"{user.display_name} Failed to Trick {target.display_name}",event_message,discord.Color.dark_magenta())
            
            await interaction.response.send_message(personal_message, ephemeral=True)
            await post_to_target_channel(channel_type="event", message=embeded_message, interaction=interaction)
        else:
            # No candy exchange, the target laughs at the thief
            update_player_field(thief_id, guild_id, 'failed_tricks', thief_data["failed_tricks"] + 1)
            event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "no_candy","target_laughs", user=interaction.user.mention, target=target.mention)
            personal_message = f"{interaction.user.display_name} I'm so sorry but {target.display_name} has no candy to trick them out of!"

            embeded_message = create_embed(f"{user.display_name} Failed to Trick {target.display_name}",event_message,discord.Color.dark_purple(), raven_url,"Raven")

            await interaction.response.send_message(personal_message, ephemeral=True)
            await post_to_target_channel(channel_type="event", message=embeded_message, interaction=interaction)
        return


    # Determine the success rate of the steal
    success_rate = calculate_thief_success_rate(thief_data["candy_in_bucket"])

    # If target doesn't have enough candy, reduce the amount to the maximum
    stolen_amount = min(random.randint(1, 10), target_data["candy_in_bucket"])

    if random.random() < success_rate:
        # Successful steal

        # Extra probability checks for successful now possibly failed steal
        if random.random() < 0.01:  # 1% chance of trick
            # Trick: both lose the candy, and it's added to the lottery
            if thief_data["candy_in_bucket"] < stolen_amount or target_data["candy_in_bucket"] < stolen_amount:
                # If either player doesn't have enough candy, reduce the amount to the minimum
                stolen_amount = min(thief_data["candy_in_bucket"], target_data["candy_in_bucket"])
            update_player_field(thief_id, guild_id, 'candy_in_bucket', max(0, thief_data["candy_in_bucket"] - stolen_amount))
            update_player_field(target_id, guild_id, 'candy_in_bucket', max(0, target_data["candy_in_bucket"] - stolen_amount))
            update_player_field(thief_id, guild_id, 'failed_tricks', thief_data["failed_tricks"] + 1)

            # Add the lost candy to a lottery
            cauldron_event = stolen_amount * 2  # both lose the candy
            # Add the candy to the lottery pool
            update_cauldron_event(interaction.guild.id, cauldron_event)

            event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "successful_trick","both_lose", user=interaction.user.mention, target=target.mention,amount=stolen_amount)
            personal_message = f"{interaction.user.display_name} well you tried to trick {target.display_name}! But you both lost!"
            embeded_message = create_embed(f"{user.display_name} Failed to Trick {target.display_name}",event_message,discord.Color.dark_purple(),raven_url,"Raven",None)

            await interaction.response.send_message(personal_message, ephemeral=True)
            await post_to_target_channel(channel_type="event", message=embeded_message, interaction=interaction)
            return

        elif random.random() < 0.03 and stolen_amount > 5:  # 3% chance target gets 1 candy back if more than 5 stolen
            update_player_field(thief_id, guild_id, 'candy_in_bucket', thief_data["candy_in_bucket"] + (stolen_amount - 1))
            update_player_field(thief_id, guild_id, 'successful_tricks', thief_data["successful_tricks"] + 1)
            update_player_field(target_id, guild_id, 'candy_in_bucket', target_data["candy_in_bucket"] + 1)  # Target gets 1 candy back

            event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "successful_trick","target_gets_1", user=interaction.user.mention, target=target.mention,amount=stolen_amount)
            personal_message = f"{interaction.user.display_name}, you tricked {stolen_amount -1} candy from {target.display_name}! Success!"
            embeded_message = create_embed(f"{user.display_name} Successfully Tricked {target.display_name}",event_message,discord.Color.purple(),raven_url,"Raven",None)
            
            await interaction.response.send_message(personal_message, ephemeral=True)
            await post_to_target_channel(channel_type="event", message=embeded_message, interaction=interaction)
            return

        else:
            # Regular success
            update_player_field(thief_id, guild_id, 'candy_in_bucket', thief_data["candy_in_bucket"] + stolen_amount)
            update_player_field(target_id, guild_id, 'candy_in_bucket', target_data["candy_in_bucket"] - stolen_amount)
            update_player_field(thief_id, guild_id, 'successful_tricks', thief_data["successful_tricks"] + 1)
            if stolen_amount == 0:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "successful_trick","regular_success",0, user=interaction.user.mention, target=target.mention,amount=stolen_amount)
            elif stolen_amount == 1:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "successful_trick", "regular_success",1, user=interaction.user.mention, target=target.mention,amount=stolen_amount)
            elif stolen_amount <= 3:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "successful_trick", "regular_success",3, user=interaction.user.mention, target=target.mention,amount=stolen_amount)
            elif stolen_amount <= 6:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "successful_trick", "regular_success",6, user=interaction.user.mention, target=target.mention,amount=stolen_amount)
            elif stolen_amount <= 9:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "successful_trick","regular_success",9, user=interaction.user.mention, target=target.mention,amount=stolen_amount)
            else:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "successful_trick", "regular_success",10, user=interaction.user.mention, target=target.mention,amount=stolen_amount)
            personal_message = f"{interaction.user.display_name} you tricked {target.display_name} out of {stolen_amount}!"
            embeded_message = create_embed(f"{user.display_name} Successfully Tricked {target.display_name}",event_message,discord.Color.purple(),raven_url,"Raven",None)
            
            await interaction.response.send_message(personal_message, ephemeral=True)
            await post_to_target_channel(channel_type="event", message=embeded_message, interaction=interaction)
            return
    else: #LEFT OFF HERE
        # Failed steal, reduce the max thief can lose to the amount they have
        penalty = min(random.randint(1, 5), thief_data["candy_in_bucket"])
        
        # Extra probability checks for failed steal
        if random.random() < 0.01:  # 1% chance both fumble and lose candy, added to the lottery
            update_player_field(thief_id, guild_id, 'candy_in_bucket', max(0, thief_data["candy_in_bucket"] - penalty))
            update_player_field(target_id, guild_id, 'candy_in_bucket', max(0, target_data["candy_in_bucket"] - penalty))
            update_player_field(thief_id, guild_id,'failed_tricks', thief_data["failed_tricks"] + 1)
            cauldron_event = penalty * 2  # both lose the candy
            update_cauldron_event(interaction.guild.id, cauldron_event)

            event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "failed_trick", "both_lose", 
                                                                          user=interaction.user.mention, target=target.mention,amount=penalty)
            embeded_message = create_embed(f"{user.display_name} Failed to Trick {target.display_name}",event_message,discord.Color.dark_purple(),  raven_url,"Raven")
            personal_message = f"{interaction.user.display_name} you fumbled the trick and lost {penalty} candy!!"

            await interaction.response.send_message(personal_message, ephemeral=True)
            await post_to_target_channel(channel_type="event", message=embeded_message, interaction=interaction)
            return
        elif random.random() < 0.03:  # 3% chance thief tries again and gets half candy
            half_stolen = max(1, penalty // 2)  # Half the candy, rounded up
            update_player_field(thief_id, guild_id, 'candy_in_bucket', thief_data["candy_in_bucket"] + half_stolen)
            update_player_field(target_id, guild_id, 'candy_in_bucket', target_data["candy_in_bucket"] - half_stolen)
            update_player_field(thief_id, guild_id,'successful_tricks', thief_data["successful_tricks"] + 1)
            event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "failed_trick", "thief_half", 
                                                                          user=interaction.user.mention, target=target.mention,amount=penalty)
            embeded_message = create_embed(f"{user.display_name} Successfully Tricked {target.display_name}",event_message,discord.Color.purple(),raven_url,"Raven",None)
            personal_message = f"{interaction.user.display_name} you initially failed but managed to get {half_stolen} candy!!"

            await interaction.response.send_message(personal_message, ephemeral=True)
            await post_to_target_channel(channel_type="event", message=embeded_message, interaction=interaction)
            return
        else:
            # Regular failure
            if penalty == 0:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "failed_trick", "regular_failure",0, 
                                                                            user=interaction.user.mention, target=target.mention,amount=penalty)
            elif penalty == 1:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "failed_trick", "regular_failure",1, 
                                                                            user=interaction.user.mention, target=target.mention,amount=penalty)
            elif penalty <= 3:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "failed_trick", "regular_failure",3, 
                                                                            user=interaction.user.mention, target=target.mention,amount=penalty)
            elif penalty == 6:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "failed_trick", "regular_failure",6, 
                                                                            user=interaction.user.mention, target=target.mention,amount=penalty)
            elif penalty == 9:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "failed_trick", "regular_failure",9, 
                                                                            user=interaction.user.mention, target=target.mention,amount=penalty)
            else:
                event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "failed_trick", "regular_failure",10, 
                                                                            user=interaction.user.mention, target=target.mention,amount=penalty)
            update_player_field(thief_id, guild_id, 'candy_in_bucket', max(0, thief_data["candy_in_bucket"] - penalty))
            update_player_field(target_id, guild_id, 'candy_in_bucket', target_data["candy_in_bucket"] + penalty)
            update_player_field(thief_id, guild_id,'failed_tricks', thief_data["failed_tricks"] + 1)
            embeded_message = create_embed(f"{user.display_name} Failed to Trick {target.display_name}",event_message,discord.Color.dark_purple(),raven_url,"Raven",None)
            personal_message = f"{interaction.user.display_name} you failed your tricks :( and lost {penalty} candy..."

            await interaction.response.send_message(personal_message, ephemeral=True)
            await post_to_target_channel(channel_type="event", message=embeded_message, interaction=interaction)
            return


async def player_treat(interaction: discord.Interaction,member: discord.Member, amount: 0):
    guild_id = interaction.guild.id
    game_disabled, _,_ = get_game_settings(guild_id)
    if game_disabled:
        print(f"Game is disabled for guild {guild_id}")
        await interaction.response.send_message("The game is currently paused.", ephemeral=True)
        return
    #Fetch message responses
    event_message,personal_message = give_treat(interaction,member,amount)

    if event_message == "The game is currently paused." or personal_message == "The game is currently paused.":
        await interaction.response.send_message("The game is currently paused.", ephemeral=True)

    #check if event_message is None, this means there was an error
    if event_message is None: #set a condition for give_treat to reuse event_message as none to send error message
        await interaction.response.send_message(personal_message, ephemeral=True)
    else:
        #Send responses
        await interaction.response.send_message(personal_message,ephemeral= True)
        await post_to_target_channel(channel_type="event", message=event_message, interaction=interaction)
    

async def player_bucket(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if game_paused( guild_id):
        interaction.response.send_message("The game is currently paused.", ephemeral=True)
        return
    user = interaction.user
    if not is_player_active(user.id, guild_id):
        await interaction.response.send_message(f"{user.mention}, you must join the game to participate! /join", ephemeral=True)
        return

    player_data = get_player_data(user.id, guild_id)
    candy_in_bucket = player_data["candy_in_bucket"]
    # successful_tricks = player_data["successful_tricks"]
    # failed_tricks = player_data["failed_tricks"]
    # treats_given = player_data["treats_given"]

    witch_name = random.choice(["luna", "raven"])

    personal_message = interaction.client.message_loader.get_message(f"{witch_name}_bucket", user=user.mention, amount=candy_in_bucket)
    await interaction.response.send_message(personal_message, ephemeral=True)

def calculate_thief_success_rate(thief_candy_in_bucket):
    """
    Calculate the success rate of a steal based on the amount of candy the thief has.
    The more candy they have, the harder it becomes to successfully steal.

    Args:  
        thief_candy_in_bucket (int): The amount of candy the thief has.
    """
    base_success_rate = 1  # Start with a 100% base success rate
    max_candy_threshold = 500  # The point where success becomes very difficult
    min_success_rate = 0.01  # New minimum success rate of 1%

    # For candy less than 500, use the original formula
    if thief_candy_in_bucket < max_candy_threshold:
        success_rate = base_success_rate * (1 - (thief_candy_in_bucket / max_candy_threshold))
    else:
        # Start with a base success rate of 10% at 500 candy
        success_rate = 0.10  
        # For every 100 candy over 500, reduce success rate by an additional 1%
        extra_candy = thief_candy_in_bucket - max_candy_threshold
        success_rate -= (extra_candy // 100) * 0.01  # Decrease by 1% per 100 extra candy

    # Cap the success rate at 1%
    return max(success_rate, min_success_rate)


def game_paused(guild_id: int) -> bool:
    """
    Check if the game is paused for a guild.

    Args:
        guild_id (int): The ID of the guild to check.

    Returns:
        bool: True if the game is paused, False otherwise.
    """
    game_disabled, _,_ = get_game_settings(guild_id)
    if game_disabled:
        return True
    return False

def give_treat(interaction: discord.Interaction, user: discord.Member, amount: 0):
    """
    Give candy to another player, handled by the /treat command or context menu Treat Player.
    
    Args:  
        interaction (discord.Interaction): The interaction object to determine guild and user.
        user (discord.Member): The target user to give candy to.
        amount (int): The amount of candy to give.
    """
    guild_id = interaction.guild.id
    giver = interaction.user
    recipient = user
    
    game_disabled, _,_ = get_game_settings(guild_id)
    if game_disabled:
        return None, "The game is currently paused."

    giver_data = get_player_data(giver.id, guild_id)
    recipient_data = get_player_data(recipient.id, guild_id)
    personal_message = None
    event_message = None

    try:
        # Checks for the treat command
        if giver_data['active'] == 0:
            personal_message = f"{giver.mention}, you must join the game to participate! /join"
            return event_message,personal_message
        if not recipient:
            personal_message = f"{giver.mention}, you must target a player for this command!"
            return event_message,personal_message
        if recipient_data['active'] == 0:
            personal_message = f"{recipient.display_name} is not active in the game!"
            return event_message,personal_message
        if giver.id == recipient.id:
            personal_message = f"{giver.mention}, you can't target yourself for this command!"
            return event_message,personal_message
        if amount < 0:
            personal_message = f"{giver.mention}, you can't give negative candy!"
            return event_message,personal_message
        if giver_data["candy_in_bucket"] < amount:
            personal_message = f"{giver.display_name}, you don't have enough candy to give!"
            return event_message,personal_message
    except ValueError:
        personal_message = f"{giver.mention}, please enter a valid number!"
        return event_message,personal_message
    except Exception as e:
        personal_message = f"I made a silly mistake! Sorry about that {giver.mention}! Please try again. or let a moderator know"
        logger.error(f"Error in utils.helper.give_treat: {str(e)}")
        return event_message,personal_message
    
    #Treat Responses
    if amount == 0:
        event_message = interaction.client.message_loader.get_message(
            "give_treat", "event_messages", "0", user=giver.mention, target=recipient.mention,amount=amount
            )   
        personal_message = interaction.client.message_loader.get_message(
            "give_treat", "personal_message","0", user=giver.display_name, target=recipient.name,amount=amount
            )
        #No Candy is given so no need to update the fields, shame on you player lol
        embeded = create_embed(f"{giver.display_name} Gave {recipient.display_name} {amount} Candy...",event_message,discord.Color.magenta(),luna_url,"Luna",None)
        
        return embeded,personal_message
    elif amount == 1:
        event_message = interaction.client.message_loader.get_message(
            "give_treat", "event_messages", "1", user=giver.mention, target=recipient.mention,amount=amount
            )   
        personal_message = interaction.client.message_loader.get_message(
            "give_treat", "personal_message","1", user=giver.display_name, target=recipient.name,amount=amount
            )
    elif amount <= 3:
        event_message = interaction.client.message_loader.get_message(
            "give_treat", "event_messages", "3", user=giver.mention, target=recipient.mention,amount=amount
            )   
        personal_message = interaction.client.message_loader.get_message(
            "give_treat", "personal_message","3", user=giver.display_name, target=recipient.name,amount=amount
            )
    elif amount <= 6:
        event_message = interaction.client.message_loader.get_message(
            "give_treat", "event_messages", "6", user=giver.mention, target=recipient.mention,amount=amount
            )   
        personal_message = interaction.client.message_loader.get_message(
            "give_treat", "personal_message","6", user=giver.display_name, target=recipient.name,amount=amount
            )
    elif amount <= 9:
        event_message = interaction.client.message_loader.get_message(
            "give_treat", "event_messages", "9", user=giver.display_name, target=recipient.mention,amount=amount
            )   
        personal_message = interaction.client.message_loader.get_message(
            "give_treat", "personal_message","9", user=giver.display_name, target=recipient.name,amount=amount
            )
    else:  
        event_message = interaction.client.message_loader.get_message(
            "give_treat", "event_messages", "10", user=giver.display_name, target=recipient.mention,amount=amount
            )   
        personal_message = interaction.client.message_loader.get_message(
            "give_treat", "personal_message","10", user=giver.display_name, target=recipient.name,amount=amount
            )
    embeded = create_embed(f"{giver.display_name} Gave {recipient.display_name} {amount} Candy :heart:",event_message,discord.Color.magenta(),luna_url,"Luna",None)
    
    # Perform the candy transfer
    update_player_field(giver.id, guild_id, 'candy_in_bucket', giver_data["candy_in_bucket"] - amount)
    update_player_field(recipient.id, guild_id, 'candy_in_bucket', recipient_data["candy_in_bucket"] + amount)
    update_player_field(giver.id, guild_id, 'treats_given', giver_data["treats_given"] + 1)
    return embeded,personal_message