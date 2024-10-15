import random
import discord
import settings

from discord import InteractionType, AppCommandType
from db_utils import is_player_active, create_player_data,get_player_data,update_player_field,update_lottery_pool
from utils.utils import post_to_target_channel


logger = settings.logging.getLogger("bot")

async def player_join(interaction: discord.Interaction,member: discord.Member): 
    guild_id = interaction.guild.id
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

#for down the road nede to setup player class
# def load_player_data(player_id,guild_id):
#     player_data = get_player_data(player_id, guild_id)

#     if player_data:
#         # Create a Player instance using the retrieved data
#         player = Player(
#             player_id=player_id,
#             guild_id=guild_id,
#             candy_count=player_data["candy_count"],
#             successful_steals=player_data["successful_steals"],
#             failed_steals=player_data["failed_steals"],
#             candy_given=player_data["candy_given"],
#             tickets_purchased=player_data["tickets_purchased"],
#             active=player_data["active"]
#         )

async def player_trick(interaction: discord.Interaction,member: discord.Member):
    guild_id = interaction.guild.id
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
        await interaction.response.send_message(f"{target.name} is not in the game!", ephemeral=True)
        return

    #renaming for easier reference
    thief_id = interaction.user.id
    target_id = target.id
    
    await interaction.response.send_message(f"{interaction.user.name}, lets see how your trick plays out...", ephemeral=True,delete_after=20)

    thief_data = get_player_data(thief_id, guild_id)
    target_data =get_player_data(target_id, guild_id)

    #Scenarios where target has no candy to have stolen
    if target_data["candy_count"] == 0:
        # Target has no candy, special handling
        if thief_data["candy_count"] > 5 and random.random() < 0.05:  # 5% chance thief feels bad and gives some candy
            given_candy = random.randint(1, min(5, thief_data["candy_count"] - 5))  # Give between 1 and 5 candy
            update_player_field(thief_id, guild_id, 'candy_count', thief_data["candy_count"] - given_candy)
            update_player_field(target_id, guild_id, 'candy_count', target_data["candy_count"] + given_candy)
            message = f"{interaction.user.mention} felt so bad for {target.mention}'s empty stash that they gave {given_candy} candy out of sympathy!"
        elif random.random() < 0.03:  # 3% chance of ghastly duel and candy vanishes into the lottery
            duel_candy = random.randint(50, 1000)
            update_lottery_pool(guild_id, duel_candy)
            message = f"{interaction.user.mention} and {target.mention} got into a ghastly duel over candy, but magically {duel_candy} candy appeared and vanished into the cauldron!"
        else:
            # No candy exchange, the target laughs at the thief
            message = f"{interaction.user.mention} tried to steal from {target.mention}, but {target.mention} laughed in their face because they have no candy!"
        await post_to_target_channel(channel_type="event", message=message, interaction=interaction)
        return

    # Determine the success rate
    success_rate = 0.5  # Default success rate is 50%
    if thief_data["candy_count"] == 0:
        success_rate = 0.2  # Lower success rate if thief has no candy

    if random.random() < success_rate:
        # Successful steal
        stolen_amount = min(random.randint(1, 10), target_data["candy_count"])

        # Extra probability checks for successful steal
        if random.random() < 0.01:  # 1% chance of trick
            # Trick: both lose the candy, and it's added to the lottery
            update_player_field(thief_id, guild_id, 'candy_count', max(0, thief_data["candy_count"] - stolen_amount))
            update_player_field(target_id, guild_id, 'candy_count', max(0, target_data["candy_count"] - stolen_amount))
            update_player_field(thief_id, guild_id, 'successful_steals', thief_data["failed_steals"] + 1)

            # Add the lost candy to a lottery
            lottery_pool = stolen_amount * 2  # both lose the candy
            # Add the candy to the lottery pool
            update_lottery_pool(interaction.guild.id, lottery_pool)

            message = f"{interaction.user.mention} was tricked by {target.mention}! Both lost {stolen_amount} candy, and it has been added to the lottery."
        elif random.random() < 0.03 and stolen_amount > 5:  # 3% chance target gets 1 candy back if more than 5 stolen
            update_player_field(thief_id, guild_id, 'candy_count', thief_data["candy_count"] + (stolen_amount - 1))
            update_player_field(thief_id, guild_id, 'successful_steals', thief_data["successful_steals"] + 1)
            update_player_field(target_id, guild_id, 'candy_count', target_data["candy_count"] + 1)  # Target gets 1 candy back
            message = f"{interaction.user.mention} stole {stolen_amount} candy from {target.mention}, but {target.mention} got 1 candy back!"
        else:
            # Regular success
            update_player_field(thief_id, guild_id, 'candy_count', thief_data["candy_count"] + stolen_amount)
            update_player_field(target_id, guild_id, 'candy_count', target_data["candy_count"] - stolen_amount)
            update_player_field(thief_id, guild_id, 'successful_steals', thief_data["successful_steals"] + 1)
            if stolen_amount == 0:
                message = f"{interaction.user.mention}... tried to trick {target.mention} by hiding in a bush. The bush didn't hide {interaction.user.name} at all and {target.name} laughed. No candy was taken! "
            elif stolen_amount == 1:
                message = f"{interaction.user.mention} crept in the shadows and snatched 1 candy from {target.mention}! Every piece helps build your candy stash!"
            elif stolen_amount <= 3:
                message = f"{interaction.user.mention} quietly nabbed {stolen_amount} candy from {target.mention}. A nice little haul!"
            elif stolen_amount <= 6:
                message = f"Quick and nimble! {interaction.user.mention} just made off with {stolen_amount} candy from {target.mention}."
            elif stolen_amount <= 9:
                message = f"{interaction.user.mention} pulled off a perfect trick, swiping {stolen_amount} candy from {target.mention}! They never saw it coming!"
            else:
                message = f"{interaction.user.mention} hit the ultimate jackpot, tricking {target.mention} out of {stolen_amount} candy! What a spooky success!"

        await post_to_target_channel(channel_type="event", message=message, interaction=interaction)
    else:
        # Failed steal
        penalty = random.randint(0, 5)

        # Extra probability checks for failed steal
        if random.random() < 0.01:  # 1% chance both fumble and lose candy, added to the lottery
            update_player_field(thief_id, guild_id, 'candy_count', max(0, thief_data["candy_count"] - penalty))
            update_player_field(thief_id, guild_id,'failed_steals', thief_data["failed_steals"] + 1)
            update_player_field(target_id, guild_id, 'candy_count', max(0, target_data["candy_count"] - penalty))
            lottery_pool = penalty * 2  # both lose the candy
            update_lottery_pool(interaction.guild.id, lottery_pool)
            message = f"{interaction.user.mention} tried to steal from {target.mention}, but both fumbled and lost {penalty} candy, added to the lottery."
        elif random.random() < 0.03:  # 3% chance thief tries again and gets half candy
            stolen_again = max(1, stolen_amount // 2)  # Half the candy, rounded up
            update_player_field(thief_id, guild_id, 'candy_count', thief_data["candy_count"] + stolen_again)
            update_player_field(thief_id, guild_id,'failed_steals', thief_data["successful_steals"] + 1)
            update_player_field(target_id, guild_id, 'candy_count', target_data["candy_count"] - stolen_again)
            message = f"{interaction.user.mention} initially failed, but managed to steal {stolen_again} candy from {target.mention} on a second attempt!"
        else:
            # Regular failure
            if penalty == 0:
                message = f"{interaction.user.mention} tried to steal but failed! Fortunately, {target.mention} didn't take any candy."
            elif penalty <= 2:
                message = f"Ouch! {interaction.user.mention} failed to grab candy, and {target.mention} swiped {penalty} candy from you. Not too bad!"
            elif penalty == 5:
                message = f"{interaction.user.mention} botched the steal! {target.mention} cleaned you out for {penalty} candy. Better luck next time!"
            else:
                message = f"{interaction.user.mention} failed miserably and {target.mention} got {penalty} candy from your misfortune!"
            update_player_field(thief_id, guild_id, 'candy_count', max(0, thief_data["candy_count"] - penalty))
            update_player_field(thief_id, guild_id,'failed_steals', thief_data["failed_steals"] + 1)
            update_player_field(target_id, guild_id, 'candy_count', target_data["candy_count"] + penalty)

        await post_to_target_channel(channel_type="event", message=message, interaction=interaction)


async def player_treat(interaction: discord.Interaction,member: discord.Member, amount: 0):
    #Fetch message responses
    event_message,personal_message = give_treat(interaction,member,amount)

    #check if event_message is None, this means there was an error
    if event_message is None:
        await interaction.response.send_message(personal_message, ephemeral=True)
    else:
        #Send responses
        await interaction.response.send_message(personal_message,ephemeral= True)
        await post_to_target_channel(channel_type="event", message=event_message, interaction=interaction)
    
    
def give_treat(interaction: discord.Interaction, user: discord.Member, amount: 0):
    guild_id = interaction.guild.id
    giver = interaction.user
    recipient = user

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
            personal_message = f"{recipient.mention} is not active in the game!"
            return event_message,personal_message
        if giver.id == recipient.id:
            personal_message = f"{giver.mention}, you can't target yourself for this command!"
            return event_message,personal_message
        if amount < 0:
            personal_message = f"{giver.mention}, you can't give negative candy!"
            return event_message,personal_message
    except ValueError:
        personal_message = f"{giver.mention}, please enter a valid number!"
        return event_message,personal_message
    except Exception as e:
        personal_message = f"I made a silly mistake! Sorry about that {giver.mention}! Please try again. or let a moderator know"
        logger.error(f"Error in utils.helper.give_treat: {str(e)}")
        return event_message,personal_message
    

    # Perform the candy transfer
    update_player_field(giver.id, guild_id, 'candy_count', giver_data["candy_count"] - amount)
    update_player_field(recipient.id, guild_id, 'candy_count', recipient_data["candy_count"] + amount)
    update_player_field(giver.id, guild_id, 'candy_given', giver_data["candy_given"] + 1)

    #Treat Responses
    if amount == 0:
        event_message = interaction.client.message_loader.get_message(
            "give_treat", "event_messages", "0", user=giver.mention, target=recipient.mention,amount=amount
            )   
        personal_message = interaction.client.message_loader.get_message(
            "give_treat", "personal_message","0", user=giver.name, target=recipient.name,amount=amount
            )   
    elif amount == 1:
        event_message = interaction.client.message_loader.get_message(
            "give_treat", "event_messages", "1", user=giver.mention, target=recipient.mention,amount=amount
            )   
        personal_message = interaction.client.message_loader.get_message(
            "give_treat", "personal_message","1", user=giver.name, target=recipient.name,amount=amount
            )
    elif amount <= 3:
        event_message = interaction.client.message_loader.get_message(
            "give_treat", "event_messages", "3", user=giver.mention, target=recipient.mention,amount=amount
            )   
        personal_message = interaction.client.message_loader.get_message(
            "give_treat", "personal_message","3", user=giver.name, target=recipient.name,amount=amount
            )
    elif amount <= 6:
        event_message = interaction.client.message_loader.get_message(
            "give_treat", "event_messages", "6", user=giver.mention, target=recipient.mention,amount=amount
            )   
        personal_message = interaction.client.message_loader.get_message(
            "give_treat", "personal_message","6", user=giver.name, target=recipient.name,amount=amount
            )
    elif amount <= 9:
        event_message = interaction.client.message_loader.get_message(
            "give_treat", "event_messages", "9", user=giver.name, target=recipient.mention,amount=amount
            )   
        personal_message = interaction.client.message_loader.get_message(
            "give_treat", "personal_message","9", user=giver.name, target=recipient.name,amount=amount
            )
    else:  
        event_message = interaction.client.message_loader.get_message(
            "give_treat", "event_messages", "10", user=giver.name, target=recipient.mention,amount=amount
            )   
        personal_message = interaction.client.message_loader.get_message(
            "give_treat", "personal_message","10", user=giver.name, target=recipient.name,amount=amount
            )
    return event_message,personal_message