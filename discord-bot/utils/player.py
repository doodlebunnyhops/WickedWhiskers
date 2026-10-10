import random
import discord
import settings
import db_utils as db
import potions
import game_stats as stats
from utils import potion_gameplay as perks
from utils.artwork import image_url, icon_embed
from utils.game_messages import publish_result

from discord import InteractionType, AppCommandType
from db_utils import is_player_active, create_player_data,get_player_data,update_player_field,update_cauldron_pool,get_active_players_by_guild,update_many_players_fields, update_cauldron_contribution
from utils.utils import post_to_target_channel,create_embed
from utils.checks import get_game_settings


logger = settings.logging.getLogger("bot")
luna_url = image_url("luna_portrait")
luna_cauldron = image_url("luna_cauldron")
luna_banner = image_url("luna_banner")
luna_candy_rain = image_url("luna_candy_shower")
luna_pumpkin = image_url("luna_pumpkin")
luna_pumpkin_cauldron = image_url("luna_pumpkin_cauldron")

raven_url = image_url("raven_portrait")
raven_banner = image_url("raven_banner")
raven_cauldron = image_url("raven_cauldron")
raven_pumpkin = image_url("raven_pumpkin")
raven_pumpkin_cauldron = image_url("raven_pumpkin_cauldron")


async def player_join(interaction: discord.Interaction, member: discord.Member):
    import player_state as state
    if member and member.id != interaction.user.id:
        await interaction.response.send_message(state.text('join_self'), ephemeral=True)
        return
    if interaction.user.bot:
        return
    try:
        state.join(interaction.guild.id, interaction.user.id)
    except state.StateError as error:
        await interaction.response.send_message(str(error), ephemeral=True)
        return
    await interaction.response.send_message(interaction.client.message_loader.get_message('join', 'messages', user=interaction.user.mention), ephemeral=True)


class _TrickResponses:
    def __init__(self):
        self.messages = []
        self.potion_notes = []

    def append_personal(self, message, **kwargs):
        self.messages.append(("personal", message))

    def append_event(self, message=None, **kwargs):
        if self.potion_notes:
            notes = "\n\n".join(self.potion_notes)
            if isinstance(message, discord.Embed):
                message.description = (message.description or "") + "\n\n" + notes
            else:
                message = (message or "") + "\n\n" + notes
            self.potion_notes.clear()
        self.messages.append(("event", message))


async def player_trick(interaction: discord.Interaction, member: discord.Member):
    import player_state as state
    try:
        state.require(interaction.guild.id, interaction.user.id)
    except state.StateError as error:
        await interaction.response.send_message(str(error), ephemeral=True)
        return
    responses = _TrickResponses()
    if member and potions.inventory(interaction.guild.id, member.id)[1].get('mirror', 0) and not getattr(interaction.guild, 'chunked', True):
        await interaction.response.defer(ephemeral=True)
        try:
            await interaction.guild.chunk(cache=True)
            if not interaction.guild.chunked:
                raise RuntimeError('Member verification incomplete')
        except (discord.DiscordException, RuntimeError):
            await interaction.followup.send(interaction.client.message_loader.get_message('potion_events', 'mirror_members_unavailable'), ephemeral=True)
            return
    # No Discord I/O until balances, effects and stats have all committed.
    with db.transaction() as conn:
        previous = potions.prior_action(conn, interaction.guild.id, interaction.id, interaction.user.id, "trick")
        if previous is not None:
            responses.append_personal("This trick was already processed; no extra charge or candy was taken.")
        else:
            _resolve_trick(interaction, member, responses)
            potions.record_action(conn, interaction.guild.id, interaction.id, interaction.user.id, "trick", {"target": member.id})
    events = [message for kind,message in responses.messages if kind == 'event']
    if events:
        for event in events:
            if not await publish_result(interaction,event,post_to_target_channel,members=(member,)):
                break
    else:
        for kind,message in responses.messages:
            if interaction.response.is_done():
                await interaction.followup.send(message,ephemeral=True)
            else:
                await interaction.response.send_message(message,ephemeral=True)


def _resolve_trick(interaction: discord.Interaction,member: discord.Member, responses):
    guild_id = interaction.guild.id
    import player_state as state
    try:
        state.require(guild_id, interaction.user.id)
    except state.StateError as error:
        responses.append_personal(str(error))
        return
    if member and not state.visible(guild_id, member.id):
        responses.append_personal(state.text('target_unavailable'))
        return
    game_disabled, _,_ = get_game_settings(guild_id)
    if game_disabled:
        print(f"Game is disabled for guild {guild_id}")
        responses.append_personal("The game is currently paused.", ephemeral=True)
        return
    user = interaction.user
    target = member

    if not is_player_active(user.id, guild_id):
        responses.append_personal(f"{user.mention}, you must join the game to participate! /join", ephemeral=True)
        return
    if not target:
        responses.append_personal(f"{user.mention}, you must target a player for this command!", ephemeral=True)
        return
    if interaction.user.id == target.id:
        responses.append_personal(f"{user.mention}, you can't target yourself for this command!", ephemeral=True)
        return
    if not is_player_active(target.id, guild_id):
        responses.append_personal(f"{target.display_name} is not in the game!", ephemeral=True)
        return

    if db.is_player_frozen(user.id, guild_id) or db.is_player_frozen(target.id, guild_id):
        responses.append_personal("Frozen players cannot participate in tricks.", ephemeral=True)
        return
    stats.add(db.get_db_connection(),guild_id,user.id,"trick_attempts")
    if perks.resolve_protection(interaction, target, responses):
        return

    #renaming for easier reference
    thief_id = interaction.user.id
    target_id = target.id
    
    thief_data = get_player_data(thief_id, guild_id)
    target_data =get_player_data(target_id, guild_id)

    #Scenarios where target has no candy to have stolen
    if target_data["candy_in_bucket"] == 0:
        # Target has no candy, special handling
        if thief_data["candy_in_bucket"] > 5 and random.random() < 0.20:  # 20% chance thief feels bad and gives some candy
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
            
            embedded_message = create_embed(f"{user.display_name} Failed to Trick {target.display_name}",event_message,discord.Color.dark_purple(),raven_url,"Raven",None)
            responses.append_personal(personal_message, ephemeral=True)
            responses.append_event(channel_type="event", message=embedded_message, interaction=interaction)
        elif random.random() < 0.15:  # 15% chance of ghastly duel and candy vanishes into the lottery
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
            update_cauldron_pool(guild_id, duel_candy)
            personal_message = f"{interaction.user.display_name}, you tried to trick {target.display_name} but you got into a fight instead! No candy was stolen :( The candy vanished into the cauldron!"
            
            # URL HERE
            embedded_message = create_embed(f"{user.display_name} Failed to Trick {target.display_name}",event_message,discord.Color.dark_green(),None,"Raven",raven_url,raven_cauldron)
            
            responses.append_personal(personal_message, ephemeral=True)
            responses.append_event(channel_type="event", message=embedded_message, interaction=interaction)
        else:
            # No candy exchange, the target laughs at the thief
            update_player_field(thief_id, guild_id, 'failed_tricks', thief_data["failed_tricks"] + 1)
            event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "no_candy","target_laughs", user=interaction.user.mention, target=target.mention)
            personal_message = f"{interaction.user.display_name} I'm so sorry but {target.display_name} has no candy to trick them out of!"

            embedded_message = create_embed(f"{user.display_name} Failed to Trick {target.display_name}",event_message,discord.Color.dark_purple(), raven_url,"Raven")

            responses.append_personal(personal_message, ephemeral=True)
            responses.append_event(channel_type="event", message=embedded_message, interaction=interaction)
        return


    # Determine the success rate of the steal
    success_rate = perks.prepare_rate(interaction, responses, calculate_thief_success_rate(thief_data["candy_in_bucket"]))

    # If target doesn't have enough candy, reduce the amount to the maximum
    stolen_amount = min(random.randint(1, 10), target_data["candy_in_bucket"])

    if perks.roll_trick(interaction, responses, success_rate):
        # Successful steal

        # Extra probability checks for successful now possibly failed steal
        if random.random() < 0.10:  # 1% chance of trick
            # Trick: both lose the candy, and it's added to the lottery
            if thief_data["candy_in_bucket"] < stolen_amount or target_data["candy_in_bucket"] < stolen_amount:
                # If either player doesn't have enough candy, reduce the amount to the minimum
                stolen_amount = min(thief_data["candy_in_bucket"], target_data["candy_in_bucket"])
            update_player_field(thief_id, guild_id, 'candy_in_bucket', max(0, thief_data["candy_in_bucket"] - stolen_amount))
            update_player_field(target_id, guild_id, 'candy_in_bucket', max(0, target_data["candy_in_bucket"] - stolen_amount))
            update_player_field(thief_id, guild_id, 'failed_tricks', thief_data["failed_tricks"] + 1)
            
            update_player_field(thief_id, guild_id, 'total_candy_lost', thief_data["total_candy_lost"] + stolen_amount)
            update_player_field(target_id, guild_id, 'total_candy_lost', target_data["total_candy_lost"] + stolen_amount)


            # Add the lost candy to a lottery
            cauldron_event = stolen_amount * 2  # both lose the candy
            # Add the candy to the lottery pool
            update_cauldron_pool(interaction.guild.id, cauldron_event)
            update_cauldron_contribution(thief_id,guild_id,stolen_amount)
            update_cauldron_contribution(target_id,guild_id,stolen_amount)

            event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "successful_trick","both_lose", user=interaction.user.mention, target=target.mention,amount=stolen_amount)
            personal_message = f"{interaction.user.display_name} well you tried to trick {target.display_name}! But you both lost!"
            embedded_message = create_embed(f"{user.display_name} Failed to Trick {target.display_name}",event_message,discord.Color.dark_purple(),raven_url,"Raven",None)

            responses.append_personal(personal_message, ephemeral=True)
            responses.append_event(channel_type="event", message=embedded_message, interaction=interaction)
            return

        elif random.random() < 0.15 and stolen_amount > 5:  # 3% chance target gets 1 candy back if more than 5 stolen
            update_player_field(thief_id, guild_id, 'candy_in_bucket', thief_data["candy_in_bucket"] + (stolen_amount - 1))
            update_player_field(thief_id, guild_id, 'successful_tricks', thief_data["successful_tricks"] + 1)
            update_player_field(target_id, guild_id, 'candy_in_bucket', target_data["candy_in_bucket"] - (stolen_amount - 1))

            update_player_field(thief_id, guild_id, 'total_candy_stolen', thief_data["total_candy_stolen"] + stolen_amount - 1)
            update_player_field(target_id, guild_id, 'total_candy_lost', target_data["total_candy_lost"] + stolen_amount -1 )

            event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "successful_trick","target_gets_1", user=interaction.user.mention, target=target.mention,amount=stolen_amount,net_amount=stolen_amount-1)
            personal_message = f"{interaction.user.display_name}, you tricked {stolen_amount -1} candy from {target.display_name}! Success!"
            embedded_message = create_embed(f"{user.display_name} Successfully Tricked {target.display_name}",event_message,discord.Color.purple(),raven_url,"Raven",None)
            
            responses.append_personal(personal_message, ephemeral=True)
            responses.append_event(channel_type="event", message=embedded_message, interaction=interaction)
            return

        else:
            # Regular success
            stolen_amount = perks.sticky_amount(interaction, responses, target, stolen_amount, target_data["candy_in_bucket"])
            update_player_field(thief_id, guild_id, 'candy_in_bucket', thief_data["candy_in_bucket"] + stolen_amount)
            update_player_field(target_id, guild_id, 'candy_in_bucket', target_data["candy_in_bucket"] - stolen_amount)
            update_player_field(thief_id, guild_id, 'successful_tricks', thief_data["successful_tricks"] + 1)
            
            update_player_field(thief_id, guild_id, 'total_candy_stolen', thief_data["total_candy_stolen"] + stolen_amount)
            update_player_field(target_id, guild_id, 'total_candy_lost', target_data["total_candy_lost"] + stolen_amount)

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
            embedded_message = create_embed(f"{user.display_name} Successfully Tricked {target.display_name}",event_message,discord.Color.purple(),raven_url,"Raven",None)
            
            responses.append_personal(personal_message, ephemeral=True)
            responses.append_event(channel_type="event", message=embedded_message, interaction=interaction)
            return
    else:
        # Failed steal, reduce the max thief can lose to the amount they have
        penalty = min(random.randint(1, 5), thief_data["candy_in_bucket"])
        
        # Extra probability checks for failed steal
        if random.random() < 0.10:  # 1% chance both fumble and lose candy, added to the lottery
            target_penalty = min(penalty, target_data['candy_in_bucket'])
            update_player_field(thief_id, guild_id, 'candy_in_bucket', max(0, thief_data["candy_in_bucket"] - penalty))
            update_player_field(target_id, guild_id, 'candy_in_bucket', max(0, target_data["candy_in_bucket"] - target_penalty))
            update_player_field(thief_id, guild_id,'failed_tricks', thief_data["failed_tricks"] + 1)

            update_player_field(thief_id, guild_id, 'total_candy_lost', thief_data["total_candy_lost"] + penalty)
            update_player_field(target_id, guild_id, 'total_candy_lost', target_data["total_candy_lost"] + target_penalty)

            cauldron_event = penalty + target_penalty  # both lose the candy
            update_cauldron_pool(interaction.guild.id, cauldron_event)
            update_cauldron_contribution(thief_id,guild_id,penalty)
            update_cauldron_contribution(target_id,guild_id,target_penalty)

            event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "failed_trick", "both_lose", 
                                                                          user=interaction.user.mention, target=target.mention,amount=penalty)
            embedded_message = create_embed(f"{user.display_name} Failed to Trick {target.display_name}",event_message,discord.Color.dark_purple(),  raven_url,"Raven")
            personal_message = f"{interaction.user.display_name} you fumbled the trick and lost {penalty} candy!!"
            if target_penalty != penalty:
                embedded_message = create_embed("Raven claims the fumbled candy", interaction.client.message_loader.get_message("gameplay_messages","unequal_loss",user=user.mention,target=target.mention,amount=penalty,target_amount=target_penalty,total=cauldron_event), discord.Color.dark_purple(), raven_url, "Raven")

            responses.append_personal(personal_message, ephemeral=True)
            responses.append_event(channel_type="event", message=embedded_message, interaction=interaction)
            return
        elif random.random() < 0.10:  # 3% chance thief tries again and gets half candy
            half_stolen = min(target_data["candy_in_bucket"], max(1, penalty // 2))  # Half the candy, rounded up
            update_player_field(thief_id, guild_id, 'candy_in_bucket', thief_data["candy_in_bucket"] + half_stolen)
            update_player_field(target_id, guild_id, 'candy_in_bucket', target_data["candy_in_bucket"] - half_stolen)
            update_player_field(thief_id, guild_id,'successful_tricks', thief_data["successful_tricks"] + 1)

            update_player_field(thief_id, guild_id, 'total_candy_stolen', thief_data["total_candy_stolen"] + half_stolen)
            update_player_field(target_id, guild_id, 'total_candy_lost', target_data["total_candy_lost"] + half_stolen)

            event_message = interaction.client.message_loader.get_message("trick_player", "event_messages", "failed_trick", "thief_half", 
                                                                          user=interaction.user.mention, target=target.mention,amount=half_stolen)
            embedded_message = create_embed(f"{user.display_name} Successfully Tricked {target.display_name}",event_message,discord.Color.purple(),raven_url,"Raven",None)
            personal_message = f"{interaction.user.display_name} you initially failed but managed to get {half_stolen} candy!!"

            responses.append_personal(personal_message, ephemeral=True)
            responses.append_event(channel_type="event", message=embedded_message, interaction=interaction)
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

            update_player_field(thief_id, guild_id, 'total_candy_lost', thief_data["total_candy_lost"] + penalty)

            embedded_message = create_embed(f"{user.display_name} Failed to Trick {target.display_name}",event_message,discord.Color.dark_purple(),raven_url,"Raven",None)
            personal_message = f"{interaction.user.display_name} you failed your tricks :( and lost {penalty} candy..."

            responses.append_personal(personal_message, ephemeral=True)
            responses.append_event(channel_type="event", message=embedded_message, interaction=interaction)
            return


async def player_treat(interaction: discord.Interaction,member: discord.Member, amount: 0):
    import player_state as state
    try:
        state.require(interaction.guild.id, interaction.user.id)
    except state.StateError as error:
        await interaction.response.send_message(str(error), ephemeral=True)
        return
    guild_id = interaction.guild.id
    game_disabled, _,_ = get_game_settings(guild_id)
    if game_disabled:
        print(f"Game is disabled for guild {guild_id}")
        await interaction.response.send_message("The game is currently paused.", ephemeral=True)
        return
    #Fetch message responses
    with db.transaction():
        event_message,personal_message = give_treat(interaction,member,amount)

    if event_message is None:
        await interaction.response.send_message(personal_message,ephemeral=True)
    else:
        await publish_result(interaction,event_message,post_to_target_channel,members=(member,))


async def player_bucket(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    user = interaction.user
    if not is_player_active(user.id, guild_id):
        await interaction.response.send_message(f"{user.mention}, you must join the game to participate! /join", ephemeral=True)
        return

    player_data = get_player_data(user.id, guild_id)
    candy_in_bucket = player_data["candy_in_bucket"]
    bottles, effects = potions.inventory(guild_id, user.id)
    potions_purchased = sum(bottles.values())
    # successful_tricks = player_data["successful_tricks"]
    # failed_tricks = player_data["failed_tricks"]
    # treats_given = player_data["treats_given"]

    import player_state as state
    witch_name = 'hidden' if state.protection_info(guild_id,user.id) else random.choice(['luna','raven'])
    tier = 'empty' if candy_in_bucket == 0 else 'small' if candy_in_bucket < 50 else 'growing' if candy_in_bucket < 500 else 'large'
    message = interaction.client.message_loader.get_message
    personal_message = message('bucket_messages',witch_name,tier) + '\n\n' + message('bucket_messages','summary',candy_amount=candy_in_bucket,potion_amount=potions_purchased)
    import passive_income as income
    from modals.earnings import EarningsView, details
    earnings=income.status(guild_id,user.id)
    personal_message+='\n\n'+details(interaction,earnings)
    await interaction.response.send_message(embed=icon_embed(personal_message, "candy_bucket"), view=EarningsView(interaction), ephemeral=True)

async def smash_pumpkin(interaction: discord.Interaction, amount: int = 0):
    from utils.pumpkins import smash, PumpkinError
    import sqlite3

    message = interaction.client.message_loader.get_message
    await interaction.response.defer(ephemeral=True)
    import player_state as state
    try:
        state.require(interaction.guild.id, interaction.user.id, 'pumpkin')
    except state.StateError as error:
        await interaction.followup.send(str(error), ephemeral=True)
        return
    try:
        result, repeated = smash(interaction.guild.id, interaction.user.id, amount, interaction.id)
    except PumpkinError as error:
        await interaction.followup.send(message("smash_pumpkin", "errors", str(error)), ephemeral=True)
        return
    except sqlite3.Error:
        logger.exception("Pumpkin settlement rolled back for guild %s", interaction.guild.id)
        await interaction.followup.send(message("smash_pumpkin", "errors", "settlement_failed"), ephemeral=True)
        return
    if repeated:
        await interaction.followup.send(message("smash_pumpkin", "already_processed"), ephemeral=True)
        return
    values = dict(user=interaction.user.mention, candy_amount=abs(result['delta']),
                  wager=result['wager'], balance=result['balance'], delta=result['delta'])
    event = message("smash_pumpkin", "event_messages", ("hidden_" if result.get("protected") else "") + result['message_key'], **values)
    # Append magical contributions rather than replacing the actual outcome (especially a wiped bucket).
    if result['magic']:
        event += "\n\n" + message("smash_pumpkin", "event_messages", ("hidden_" if result.get("protected") else "") + result['magic'], **values)
    summary = message("smash_pumpkin", "summary", **values)
    event += "\n\n" + summary
    is_win = result['delta'] >= 0
    image = (luna_pumpkin_cauldron if result['magic'] == 'luna' else luna_pumpkin) if is_win else (raven_pumpkin_cauldron if result['magic'] == 'raven' else raven_pumpkin)
    embed = create_embed(message("smash_pumpkin", "title", user=interaction.user.display_name),
                         event, discord.Color.orange(), image, "Luna" if is_win else "Raven", None)
    if result.get('protected'):
        embed = discord.Embed(title=message('smash_pumpkin', 'title', user=interaction.user.display_name), description=event, color=discord.Color.orange())
    await publish_result(interaction,embed,post_to_target_channel,deferred=True)

def calculate_sweetness(total_candy_given, total_candy_stolen):
    """
    Calculate the percentage of pure sweetness based on candy given and stolen.

    Args:
        total_candy_given (int): The total amount of candy given by the player.
        total_candy_stolen (int): The total amount of candy stolen by the player.

    Returns:
        float: The player's pure sweetness percentage.
    """
    # Total actions
    total_actions = total_candy_given + total_candy_stolen
    
    # If no actions were taken, player can't be sweet or evil
    if total_actions == 0:
        return 0.0

    # Calculate sweetness percentage
    sweetness = (total_candy_given / total_actions)
    return sweetness

def calculate_evilness(total_candy_given, total_candy_stolen):
    """
    Calculate the percentage of pure evil based on candy stolen and given.

    Args:
        total_candy_given (int): The total amount of candy given by the player.
        total_candy_stolen (int): The total amount of candy stolen by the player.

    Returns:
        float: The player's pure evil percentage.
    """
    # Total actions
    total_actions = total_candy_given + total_candy_stolen

    # If no actions were taken, player can't be sweet or evil
    if total_actions == 0:
        return 0.0

    # Calculate evil percentage
    evilness = (total_candy_stolen / total_actions)
    return evilness

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
    with db.transaction() as conn:
        previous = potions.prior_action(conn, interaction.guild.id, interaction.id, interaction.user.id, "treat")
        if previous is not None:
            return None, interaction.client.message_loader.get_message("potion_events", "treat_replayed")
        result = _resolve_treat(interaction, user, amount)
        potions.record_action(conn, interaction.guild.id, interaction.id, interaction.user.id, "treat", {"target": user.id, "amount": amount})
        return result


def _resolve_treat(interaction: discord.Interaction, user: discord.Member, amount: 0):
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

    import player_state as state
    try:
        state.require(guild_id, giver.id)
    except state.StateError as error:
        return None, str(error)
    if not recipient or not state.visible(guild_id, recipient.id):
        return None, state.text('target_unavailable')

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
            "give_treat", "event_messages", "standard", "0", user=giver.mention, target=recipient.mention,amount=amount
            )   
        personal_message = interaction.client.message_loader.get_message(
            "give_treat", "personal_message","0", user=giver.display_name, target=recipient.name,amount=amount
            )
        #No Candy is given so no need to update the fields, shame on you player lol
        embeded = create_embed(f"{giver.display_name} Gave {recipient.display_name} {amount} Candy...",event_message,discord.Color.magenta(),luna_url,"Luna",None)
        
        return embeded,personal_message

    #if amount given is 25% or more of the giver's total candy, the giver is considered generous
    if amount >= giver_data["candy_in_bucket"] * 0.60:
        #time box this frist condition
        if random.random() < .05: # Luna's Magic Multitplies double the candy to the recipient and giver gets some too
           embeded, personal_message = double_candy(interaction,guild_id,giver,giver_data,recipient,recipient_data,amount)
        elif random.random() < .05: #Luna fills the cauldron with the candy
            embeded, personal_message = luna_cauldron_fill(interaction,guild_id,giver,giver_data,recipient,recipient_data,amount,1000)
        else: #generous 60 responses
            embeded, personal_message = generous_response(interaction,guild_id,giver,giver_data,recipient,recipient_data,amount,60)
    
    elif amount >= giver_data["candy_in_bucket"] * 0.30:
        
        if random.random() < 0.10: #10% chance luna will give a piece of candy to all active players
            embeded, personal_message = give_all_candy(interaction,guild_id,giver,giver_data,recipient,recipient_data,amount)
        elif random.random() < 0.10: #10% chance luna fills the cauldron with the candy
            embeded, personal_message = luna_cauldron_fill(interaction,guild_id,giver,giver_data,recipient,recipient_data,amount,500)
        else: #Generous giver 30 response
            embeded, personal_message = generous_response(interaction,guild_id,giver,giver_data,recipient,recipient_data,amount,30)    
    
    elif amount >= giver_data["candy_in_bucket"] * 0.10:
        if random.random() < 0.05: #5% chance luna will give a piece of candy to all active players
            embeded, personal_message = give_all_candy(interaction,guild_id,giver,giver_data,recipient,recipient_data,amount)
        else: # Generous giver 11 response
            embeded, personal_message = generous_response(interaction,guild_id,giver,giver_data,recipient,recipient_data,amount,11)
    else:
        if amount < 10 and amount > 1: # Standard respsones 1-10 for giving candy
            embeded, personal_message = generous_response(interaction,guild_id,giver,giver_data,recipient,recipient_data,amount,amount)   
        else: # anything else just boiler plate at standard 5
            embeded, personal_message = generous_response(interaction,guild_id,giver,giver_data,recipient,recipient_data,amount,5)
    return embeded,personal_message

def give_all_candy(interaction: discord.Interaction, guild_id: int, giver: discord.Member, giver_data, recipient: discord.Member, recipient_data, amount: int):
    """
    Give all the candy from the giver to the recipient.

    Args:
        interaction (discord.Interaction): The interaction object to determine guild and user.
        guild_id (int): The ID of the guild.
        giver (discord.Member): The giver of the candy.
        giver_data (dict): The giver's player data.
        recipient (discord.Member): The recipient of the candy.
        recipient_data (dict): The recipient's player data.
        amount (int): The amount of candy to give.

    Returns:
        tuple: The event message and personal message for the interaction.
    """

    # Messages
    event_message = interaction.client.message_loader.get_message(
        "give_treat", "event_messages", "candy_for_all", user=giver.mention, target=recipient.mention,amount=amount
        ) 
    personal_message = f":{giver.display_name} you gave {recipient.display_name} {amount} and now Luna is throwing candy everywhere! LOL"
    embeded = create_embed(f"EVERYONE GETS CANDY!",event_message,discord.Color.pink(),luna_url,"Luna",None,luna_candy_rain)

    #Update the giver's candy bucket, we wont take candy from the giver
    update_player_field(giver.id, guild_id, 'treats_given', giver_data["treats_given"] + 1)
    update_player_field(giver.id, guild_id, 'total_candy_given', giver_data["total_candy_given"] + amount)

    #Update the recipient's candy bucket
    update_player_field(recipient.id, guild_id, 'candy_in_bucket', recipient_data["candy_in_bucket"] + amount)

    #update all active players candy buckets to add 1 candy
    active_players = get_active_players_by_guild(guild_id)
    player_ids = [player[0] for player in active_players]
    fields_to_update = {
        'candy_in_bucket': 'candy_in_bucket + 1'
    }
    update_many_players_fields(player_ids, guild_id, fields_to_update)

    return embeded,personal_message
    

def double_candy(interaction: discord.Interaction, guild_id: int, giver: discord.Member, giver_data, recipient: discord.Member, recipient_data, amount: int):
    """
    Double the amount of candy given by the giver to the recipient.

    Args:
        interaction (discord.Interaction): The interaction object to determine guild and user.
        guild_id (int): The ID of the guild.
        giver (discord.Member): The giver of the candy.
        giver_data (dict): The giver's player data.
        recipient (discord.Member): The recipient of the candy.
        recipient_data (dict): The recipient's player data.
        amount (int): The amount of candy to double.

    Returns:
        tuple: The event message and personal message for the interaction.
    """
    event_message = interaction.client.message_loader.get_message(
        "give_treat", "event_messages", "double_candy", user=giver.mention, target=recipient.mention,amount=amount*2,giver_bonus=amount
        )
    personal_message = f"Oh my! Looks like Luna got carried away again and doubled the candy {giver.display_name}!"
    embeded = create_embed(f"{giver.display_name} Gave {recipient.display_name} {amount} Candy... but wait?",event_message,discord.Color.magenta(),luna_url,"Luna",None)
    #Update the giver's candy bucket
    update_player_field(giver.id, guild_id, 'candy_in_bucket', giver_data["candy_in_bucket"] + amount)
    update_player_field(giver.id, guild_id, 'total_candy_given', giver_data["total_candy_given"] + amount) #techincally the giver gave the candy so it counts
    update_player_field(giver.id, guild_id, 'treats_given', giver_data["treats_given"] + 1)
    update_player_field(recipient.id, guild_id, 'candy_in_bucket', recipient_data["candy_in_bucket"] + amount*2)

    return embeded,personal_message

def luna_cauldron_fill(interaction: discord.Interaction, guild_id: int, giver: discord.Member, giver_data, recipient: discord.Member, recipient_data, amount: int,max_candy: 500):
    magic_burst_candy = random.randint(50, max_candy)
    event_message = interaction.client.message_loader.get_message(
        "give_treat", "event_messages", "cauldron", user=giver.mention, target=recipient.mention,amount=amount,cauldron_candy_amount=magic_burst_candy
        )
    personal_message = f"Oh my! Looks like Luna got carried away again... :D Luna gave you and {recipient.display_name} a Witch's Ward potion, {giver.display_name}!"
    embeded = create_embed(f"{giver.display_name} Gave {recipient.display_name} {amount} Candy.",event_message,discord.Color.pink(),luna_url,"Luna",None,luna_cauldron)
    
    #Special Gift
    potions.grant(db.get_db_connection(), guild_id, giver.id, 'ward')
    potions.grant(db.get_db_connection(), guild_id, recipient.id, 'ward')
    
    #Update the giver's candy bucket, no candy taken for this event
    update_player_field(giver.id, guild_id, 'treats_given', giver_data["treats_given"] + 1)
    update_player_field(giver.id, guild_id, 'total_candy_given', giver_data["total_candy_given"] + amount)
    #update the recipient's candy bucket
    update_player_field(recipient.id, guild_id, 'candy_in_bucket', recipient_data["candy_in_bucket"] + amount)

    #update the cauldron pool
    update_cauldron_pool(guild_id, magic_burst_candy)
    return embeded,personal_message

def generous_response(interaction: discord.Interaction, guild_id: int, giver: discord.Member, giver_data, recipient: discord.Member, recipient_data, amount: int, generosity: 0):
    
    #Generosity will be 60,30,11 and 0 = standard
    if generosity > 10:
        event_message = interaction.client.message_loader.get_message(
            "give_treat", "event_messages", f"generous_{generosity}", user=giver.mention, target=recipient.mention,amount=amount
            )
        personal_message = f":stars: {giver.display_name} that's a lot to give, too kind :heart:!"
        embeded = create_embed(f"{giver.display_name} Gave {recipient.display_name} {amount} Candy",event_message,discord.Color.magenta(),luna_url,"Luna",None)

    else: #standard 1-10 responses
        # Check thresholds and select the correct message key
        if generosity == 1:
            message_key = "1"
        elif 2 <= generosity <= 3:
            message_key = "3"
        elif 4 <= generosity <= 6:
            message_key = "6"
        elif 7 <= generosity <= 9:
            message_key = "9"
        else:  # Default to "10" for generosity >= 10
            message_key = "10"

        #This is gross..i need to better dynamically load the messages
        event_message = interaction.client.message_loader.get_message(
        "give_treat", "event_messages", "standard",f"{message_key}", user=giver.mention, target=recipient.mention,amount=amount
        )
        personal_message = interaction.client.message_loader.get_message(
            "give_treat", "personal_message", f"{message_key}", user=giver.display_name, target=recipient.name,amount=amount
            )
        embeded = create_embed(f"{giver.display_name} Gave {recipient.display_name} {amount} Candy",event_message,discord.Color.magenta(),luna_url,"Luna",None)

    #Update the giver's candy bucket
    update_player_field(giver.id, guild_id, 'candy_in_bucket', giver_data["candy_in_bucket"] - amount)
    update_player_field(giver.id, guild_id, 'treats_given', giver_data["treats_given"] + 1)
    update_player_field(giver.id, guild_id, 'total_candy_given', giver_data["total_candy_given"] + amount)

    update_player_field(recipient.id, guild_id, 'candy_in_bucket', recipient_data["candy_in_bucket"] + amount)
    bonus_note = perks.favor_bonus(interaction, recipient, amount)
    if bonus_note:
        embeded.description = (embeded.description or '') + '\n\n' + bonus_note
        personal_message = (personal_message or '') + '\n' + bonus_note

    return embeded,personal_message
