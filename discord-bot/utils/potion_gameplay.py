"""Potion hooks called inside the shared synchronous gameplay transaction."""
import random
import discord
import db_utils as db
import potions
import game_stats as stats


def text(interaction, key, **values):
    return interaction.client.message_loader.get_message('potion_events', key, user=interaction.user.mention, **values)


def take(interaction, uid, key):
    conn = db.get_db_connection()
    if potions.consume_charge(conn, interaction.guild.id, uid, key):
        potions.audit(conn, interaction.guild.id, uid, key + '_trigger', {'attacker': interaction.user.id})
        return True
    return False


def prepare_rate(interaction, responses, base_rate):
    active = potions.inventory(interaction.guild.id, interaction.user.id)[1].get('cunning', 0)
    rate = potions.trick_rate(interaction.guild.id, interaction.user.id, base_rate)
    if active:
        responses.potion_notes.append(text(interaction, 'cunning', chance=round(rate * 100, 2)))
    return rate


def roll_trick(interaction, responses, rate):
    success = random.random() < rate
    if not success and take(interaction, interaction.user.id, 'second_chance'):
        success = random.random() < rate
        responses.potion_notes.append(text(interaction, 'second_success' if success else 'second_failure'))
    return success


def sticky_amount(interaction, responses, target, amount, available):
    bonus = min((amount + 3) // 4, max(0, available - amount))
    if bonus > 0 and take(interaction, interaction.user.id, 'sticky'):
        responses.potion_notes.append(text(interaction, 'sticky', target=target.mention, amount=bonus, total=amount + bonus))
        return amount + bonus
    return amount


def finish_mirror(interaction, responses, key, original, target, amount=0):
    body = text(interaction, key, original=original.mention, target=target.mention, amount=amount)
    witch = interaction.client.message_loader.get_message('who_is_raven', 'image_url')
    embed = discord.Embed(title=text(interaction, 'mirror_title'), description=body, color=discord.Color.dark_purple())
    embed.set_thumbnail(url=witch)
    responses.append_personal(body)
    responses.append_event(message=embed)


def choose_redirect(candidates):
    return random.choice(candidates)


def resolve_protection(interaction, target, responses):
    guild_id, attacker = interaction.guild.id, interaction.user
    if potions.block_trick(guild_id, attacker.id, target.id):
        stats.add(db.get_db_connection(),guild_id,attacker.id,'blocked_attempts')
        body = text(interaction, 'ward', target=target.mention)
        responses.append_personal(body)
        responses.append_event(message=body)
        return True
    if not potions.inventory(guild_id, target.id)[1].get('mirror', 0):
        return False
    # Only known current non-bot members are eligible. The invoking attacker is known current.
    choices = []
    for row in db.get_active_players_by_guild(guild_id):
        uid = row[0]
        member = attacker if uid == attacker.id else interaction.guild.get_member(uid)
        if uid != target.id and member and not getattr(member, 'bot', False) and not db.is_player_frozen(uid, guild_id):
            choices.append(member)
    if not choices:
        responses.append_personal(text(interaction, 'mirror_no_target', target=target.mention))
        return True
    redirected = choose_redirect(choices)
    take(interaction, target.id, 'mirror')
    stats.add(db.get_db_connection(),guild_id,target.id,'defended',1,'mirror')
    stats.add(db.get_db_connection(),guild_id,attacker.id,'redirected_attempts')
    responses.potion_notes.append(text(interaction, 'mirror_redirect', original=target.mention, target=redirected.mention))
    if potions.block_trick(guild_id, attacker.id, redirected.id):
        stats.add(db.get_db_connection(),guild_id,attacker.id,'blocked_attempts')
        responses.potion_notes.append(text(interaction, 'ward', target=redirected.mention))
        finish_mirror(interaction, responses, 'mirror_blocked', target, redirected)
        return True
    if take(interaction, redirected.id, 'mirror'):
        stats.add(db.get_db_connection(),guild_id,redirected.id,'defended',1,'mirror')
        stats.add(db.get_db_connection(),guild_id,attacker.id,'blocked_attempts')
        responses.potion_notes.append(text(interaction, 'mirror_stop', target=redirected.mention))
        finish_mirror(interaction, responses, 'mirror_blocked', target, redirected)
        return True
    attacker_data = db.get_player_data(attacker.id, guild_id)
    victim_data = db.get_player_data(redirected.id, guild_id)
    if victim_data['candy_in_bucket'] <= 0:
        finish_mirror(interaction, responses, 'mirror_empty', target, redirected)
        return True
    from utils.player import calculate_thief_success_rate
    rate = prepare_rate(interaction, responses, calculate_thief_success_rate(attacker_data['candy_in_bucket']))
    amount = min(random.randint(1, 10), victim_data['candy_in_bucket'])
    conn = db.get_db_connection()
    if not roll_trick(interaction, responses, rate):
        conn.execute('UPDATE players SET failed_tricks=failed_tricks+1 WHERE guild_id=? AND player_id=?', (guild_id, attacker.id))
        finish_mirror(interaction, responses, 'mirror_failed', target, redirected)
        return True
    if redirected.id == attacker.id:
        conn.execute('UPDATE players SET candy_in_bucket=candy_in_bucket-?, total_candy_lost=total_candy_lost+?, failed_tricks=failed_tricks+1 WHERE guild_id=? AND player_id=?', (amount, amount, guild_id, attacker.id))
        db.update_cauldron_pool(guild_id, amount)
        db.update_cauldron_contribution(attacker.id, guild_id, amount)
        finish_mirror(interaction, responses, 'mirror_self', target, redirected, amount)
    else:
        amount = sticky_amount(interaction, responses, redirected, amount, victim_data['candy_in_bucket'])
        conn.execute('UPDATE players SET candy_in_bucket=candy_in_bucket-?, total_candy_lost=total_candy_lost+? WHERE guild_id=? AND player_id=?', (amount, amount, guild_id, redirected.id))
        conn.execute('UPDATE players SET candy_in_bucket=candy_in_bucket+?, total_candy_stolen=total_candy_stolen+?, successful_tricks=successful_tricks+1 WHERE guild_id=? AND player_id=?', (amount, amount, guild_id, attacker.id))
        finish_mirror(interaction, responses, 'mirror_success', target, redirected, amount)
    return True


def favor_bonus(interaction, recipient, amount):
    bonus = min(5, amount // 2)
    guild_id = interaction.guild.id
    if bonus <= 0 or db.is_player_frozen(interaction.user.id, guild_id) or db.is_player_frozen(recipient.id, guild_id):
        return None
    if take(interaction, interaction.user.id, 'favor'):
        db.get_db_connection().execute('UPDATE players SET total_candy_given=total_candy_given+? WHERE guild_id=? AND player_id=?',(bonus,guild_id,interaction.user.id))
        stats.add(db.get_db_connection(),guild_id,interaction.user.id,'gifted',bonus,'favor')
        db.get_db_connection().execute('UPDATE players SET candy_in_bucket=candy_in_bucket+? WHERE guild_id=? AND player_id=?', (bonus, guild_id, recipient.id))
        return text(interaction, 'favor', target=recipient.mention, amount=bonus)
    return None
