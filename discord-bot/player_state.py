"""Persistent participation, moderator freezes, and prepaid timed concealment.

Every mutation is synchronous and transactional. Timestamps are checked on use,
so protection/freeze expiry never depends on a running background timer.
"""
import time
from functools import lru_cache
from pathlib import Path
import db_utils as db
import potions
import game_stats as stats
from utils.messages import default_messages

REJOIN_SECONDS = 3600
DEFAULTS = dict(fee=50, rate=5, minimum=5, maximum=30, cooldown=60, modes='both', enabled=True)


@lru_cache(maxsize=1)
def loader():
    return default_messages()


def text(key, **values):
    return loader().get_message('participation', key, **values)


class StateError(potions.PotionError):
    def __init__(self, key, **values):
        self.key, self.values = key, values
        super().__init__(text(key, **values))


def initialize_schema(conn):
    for sql in (
        'CREATE TABLE IF NOT EXISTS player_freezes (guild_id INTEGER, player_id INTEGER, until_at INTEGER, reason TEXT NOT NULL, moderator_id INTEGER, PRIMARY KEY(guild_id,player_id))',
        'CREATE TABLE IF NOT EXISTS player_rejoins (guild_id INTEGER, player_id INTEGER, available_at INTEGER NOT NULL, PRIMARY KEY(guild_id,player_id))',
        'CREATE TABLE IF NOT EXISTS returned_potions (id INTEGER PRIMARY KEY, guild_id INTEGER, player_id INTEGER, potion_id TEXT, charges INTEGER NOT NULL CHECK(charges>0))',
        'CREATE TABLE IF NOT EXISTS protection_credits (guild_id INTEGER, player_id INTEGER, quantity INTEGER NOT NULL CHECK(quantity>=0), PRIMARY KEY(guild_id,player_id))',
        'CREATE TABLE IF NOT EXISTS protection_settings (guild_id INTEGER PRIMARY KEY, fee INTEGER, rate INTEGER, minimum INTEGER, maximum INTEGER, cooldown INTEGER, modes TEXT, enabled INTEGER)',
        'CREATE TABLE IF NOT EXISTS player_protection (guild_id INTEGER, player_id INTEGER, start_at INTEGER, end_at INTEGER, mode TEXT, rate INTEGER, reserve INTEGER, cooldown_seconds INTEGER, PRIMARY KEY(guild_id,player_id))',
        'CREATE TABLE IF NOT EXISTS protection_cooldowns (guild_id INTEGER, player_id INTEGER, available_at INTEGER, PRIMARY KEY(guild_id,player_id))',
    ):
        conn.execute(sql)


def clock(now=None):
    return int(time.time()) if now is None else int(now)


def freeze_info(guild_id, player_id, now=None):
    conn = db.get_db_connection()
    row = conn.execute('SELECT until_at,reason FROM player_freezes WHERE guild_id=? AND player_id=?', (guild_id,player_id)).fetchone()
    if row:
        return dict(until=row[0], reason=row[1]) if row[0] is None or row[0] > clock(now) else None
    # Honor pre-feature flags without changing legacy data on a read.
    row = conn.execute('SELECT frozen FROM players WHERE guild_id=? AND player_id=?', (guild_id,player_id)).fetchone()
    return dict(until=None, reason='') if row and row[0] else None


def protection_info(guild_id, player_id, now=None):
    row = db.get_db_connection().execute('SELECT start_at,end_at,mode,rate,reserve,cooldown_seconds FROM player_protection WHERE guild_id=? AND player_id=?', (guild_id,player_id)).fetchone()
    if row and row[1] > clock(now):
        return dict(zip(('start','end','mode','rate','reserve','cooldown'), row))
    return None


def visible(guild_id, player_id, now=None):
    return db.is_player_active(player_id,guild_id) and not freeze_info(guild_id,player_id,now) and not protection_info(guild_id,player_id,now)


def require(guild_id, player_id, action='social', now=None):
    frozen = freeze_info(guild_id,player_id,now)
    if frozen:
        import discord
        until = frozen['until']
        expiry = text('indefinite') if until is None else f'<t:{until}:F> (<t:{until}:R>)'
        reason = discord.utils.escape_markdown(frozen['reason']) if frozen['reason'] else text('no_reason')
        raise StateError('frozen_private', expiry=expiry, reason=reason)
    if action in ('social','use'):
        shield = protection_info(guild_id,player_id,now)
        if shield:
            raise StateError('protected_private', expiry=shield['end'])


def settings(guild_id):
    row = db.get_db_connection().execute('SELECT fee,rate,minimum,maximum,cooldown,modes,enabled FROM protection_settings WHERE guild_id=?', (guild_id,)).fetchone()
    return dict(zip(DEFAULTS,row)) if row else dict(DEFAULTS)


def configure(guild_id, actor_id, values):
    for key in ('fee','rate','minimum','maximum','cooldown'):
        if type(values.get(key)) is not int or not 1 <= values[key] <= (1_000_000 if key in ('fee','rate') else 10080):
            raise StateError('bad_settings')
    if values['minimum'] > values['maximum'] or values.get('modes') not in ('both','fixed','budget') or type(values.get('enabled')) is not bool:
        raise StateError('bad_settings')
    with db.transaction() as conn:
        old = settings(guild_id)
        conn.execute('INSERT OR REPLACE INTO protection_settings VALUES(?,?,?,?,?,?,?,?)', (guild_id,*(values[k] for k in DEFAULTS)))
        potions.audit(conn,guild_id,actor_id,'protection_settings',dict(old=old,new=values))


def credits(guild_id, player_id):
    row = db.get_db_connection().execute('SELECT quantity FROM protection_credits WHERE guild_id=? AND player_id=?',(guild_id,player_id)).fetchone()
    return row[0] if row else 0


def quote(guild_id, player_id, mode, units):
    config = settings(guild_id)
    if not config['enabled']:
        raise StateError('sales_disabled')
    if mode not in ('fixed','budget') or config['modes'] not in ('both',mode):
        raise StateError('mode_disabled')
    if type(units) is not int or units <= 0:
        raise StateError('bad_duration')
    if mode == 'budget' and units % config['rate']:
        raise StateError('budget_multiple', rate=config['rate'])
    minutes = units if mode == 'fixed' else units // config['rate']
    if not config['minimum'] <= minutes <= config['maximum']:
        raise StateError('duration_range', minimum=config['minimum'], maximum=config['maximum'])
    credit = credits(guild_id,player_id) > 0
    fee = 0 if credit else config['fee']
    reserve = minutes * config['rate']
    return dict(config=config,mode=mode,units=units,minutes=minutes,fee=fee,reserve=reserve,total=fee+reserve,credit=credit)


def buy_protection(guild_id, player_id, quoted, action_id, now=None):
    now = clock(now)
    with db.transaction() as conn:
        previous = potions.prior_action(conn,guild_id,action_id,player_id,'protection_buy')
        if previous is not None:
            return previous
        potions.eligible(guild_id,player_id)
        require(guild_id,player_id,'use',now)
        if settings(guild_id) != quoted['config'] or (credits(guild_id,player_id)>0) != quoted['credit']:
            raise StateError('quote_changed')
        current = quote(guild_id,player_id,quoted['mode'],quoted['units'])
        if current != quoted:
            raise StateError('quote_changed')
        row = conn.execute('SELECT available_at FROM protection_cooldowns WHERE guild_id=? AND player_id=?',(guild_id,player_id)).fetchone()
        if row and row[0] > now:
            raise StateError('protection_cooldown', expiry=row[0])
        changed = conn.execute('UPDATE players SET candy_in_bucket=candy_in_bucket-? WHERE guild_id=? AND player_id=? AND candy_in_bucket>=?',(current['total'],guild_id,player_id,current['total']))
        if changed.rowcount != 1:
            raise StateError('not_enough', amount=current['total'])
        if current['credit']:
            conn.execute('UPDATE protection_credits SET quantity=quantity-1 WHERE guild_id=? AND player_id=?',(guild_id,player_id))
        stats.settle_protection(conn,guild_id,player_id,now)
        stats.add(conn,guild_id,player_id,'purchased',int(not current['credit']),'veil')
        stats.add(conn,guild_id,player_id,'activated',1,'veil')
        stats.add(conn,guild_id,player_id,'spent',current['total'],'veil')
        stats.add(conn,guild_id,player_id,'protection_purchased_seconds',current['minutes']*60,'veil')
        end = now + current['minutes']*60
        cooldown = current['config']['cooldown']*60
        conn.execute('INSERT OR REPLACE INTO player_protection VALUES(?,?,?,?,?,?,?,?)',(guild_id,player_id,now,end,current['mode'],current['config']['rate'],current['reserve'],cooldown))
        conn.execute('INSERT OR REPLACE INTO protection_cooldowns VALUES(?,?,?)',(guild_id,player_id,end+cooldown))
        result = dict(end=end,total=current['total'],mode=current['mode'],cooldown=end+cooldown)
        return potions.record_action(conn,guild_id,action_id,player_id,'protection_buy',result)


def finish_protection(conn, guild_id, player_id, now, frozen=False, forfeited=False):
    shield = protection_info(guild_id,player_id,now)
    refund = 0
    if shield:
        minutes = max(1, (now-shield['start'])//60 + 1)
        if not forfeited and (frozen or shield['mode']=='budget'):
            refund = max(0,shield['reserve'] - minutes*shield['rate'])
            conn.execute('UPDATE players SET candy_in_bucket=candy_in_bucket+? WHERE guild_id=? AND player_id=?',(refund,guild_id,player_id))
        if frozen:
            conn.execute('INSERT INTO protection_credits VALUES(?,?,1) ON CONFLICT(guild_id,player_id) DO UPDATE SET quantity=quantity+1',(guild_id,player_id))
        conn.execute('INSERT OR REPLACE INTO protection_cooldowns VALUES(?,?,?)',(guild_id,player_id,now+shield['cooldown']))
    stats.settle_protection(conn,guild_id,player_id,now)
    stats.add(conn,guild_id,player_id,'spent',-refund,'veil')
    conn.execute('DELETE FROM player_protection WHERE guild_id=? AND player_id=?',(guild_id,player_id))
    return refund


def end_protection(guild_id, player_id, action_id, now=None):
    now = clock(now)
    with db.transaction() as conn:
        previous = potions.prior_action(conn,guild_id,action_id,player_id,'protection_end')
        if previous is not None:
            return previous
        if not protection_info(guild_id,player_id,now):
            raise StateError('no_protection')
        refund = finish_protection(conn,guild_id,player_id,now)
        return potions.record_action(conn,guild_id,action_id,player_id,'protection_end',dict(refund=refund))


def freeze(guild_id, player_id, moderator_id, minutes, reason, action_id, update=False, now=None):
    now = clock(now)
    if minutes is not None and (type(minutes) is not int or not 1 <= minutes <= 525600):
        raise StateError('bad_duration')
    if len(reason)>500:
        raise StateError('reason_length')
    with db.transaction() as conn:
        previous = potions.prior_action(conn,guild_id,action_id,moderator_id,'freeze')
        if previous is not None:
            return previous,True
        if db.get_player_data(player_id,guild_id) is None:
            raise StateError('not_joined')
        existing = freeze_info(guild_id,player_id,now)
        if existing and not update:
            raise StateError('already_frozen')
        if not existing:
            conn.execute('INSERT INTO returned_potions(guild_id,player_id,potion_id,charges) SELECT guild_id,player_id,potion_id,charges FROM potion_effects WHERE guild_id=? AND player_id=? AND charges>0',(guild_id,player_id))
            conn.execute('DELETE FROM potion_effects WHERE guild_id=? AND player_id=?',(guild_id,player_id))
            finish_protection(conn,guild_id,player_id,now,frozen=True)
        until = None if minutes is None else now+minutes*60
        conn.execute('INSERT OR REPLACE INTO player_freezes VALUES(?,?,?,?,?)',(guild_id,player_id,until,reason,moderator_id))
        conn.execute('UPDATE players SET frozen=1 WHERE guild_id=? AND player_id=?',(guild_id,player_id))
        result=dict(player_id=player_id,until=until,reason=reason,updated=bool(existing))
        potions.record_action(conn,guild_id,action_id,moderator_id,'freeze',result)
        return result,False


def unfreeze(guild_id, player_id, moderator_id, action_id):
    with db.transaction() as conn:
        previous=potions.prior_action(conn,guild_id,action_id,moderator_id,'unfreeze')
        if previous is not None:
            return previous,True
        conn.execute('DELETE FROM player_freezes WHERE guild_id=? AND player_id=?',(guild_id,player_id))
        conn.execute('UPDATE players SET frozen=0 WHERE guild_id=? AND player_id=?',(guild_id,player_id))
        result=dict(player_id=player_id)
        potions.record_action(conn,guild_id,action_id,moderator_id,'unfreeze',result)
        return result,False


def join(guild_id, player_id, now=None):
    now=clock(now)
    with db.transaction() as conn:
        require(guild_id,player_id,'join',now)
        row=conn.execute('SELECT available_at FROM player_rejoins WHERE guild_id=? AND player_id=?',(guild_id,player_id)).fetchone()
        if row and row[0]>now:
            raise StateError('rejoin_wait', expiry=row[0])
        if db.get_game_settings(guild_id)[0]:
            raise StateError('paused')
        data=db.get_player_data(player_id,guild_id)
        if data and data['active']:
            raise StateError('already_joined')
        if data:
            conn.execute('UPDATE players SET active=1,candy_in_bucket=50 WHERE guild_id=? AND player_id=?',(guild_id,player_id))
        else:
            db.create_player_data(player_id,guild_id)
        conn.execute('DELETE FROM player_rejoins WHERE guild_id=? AND player_id=?',(guild_id,player_id))


def leave(guild_id, player_id, now=None):
    now=clock(now)
    with db.transaction() as conn:
        data=db.get_player_data(player_id,guild_id)
        if not data or not data['active']:
            return False
        finish_protection(conn,guild_id,player_id,now,forfeited=True)
        # Preserve freeze records, all cooldowns, and receipts/audit to prevent replay exploits.
        for table in ('player_metrics','potion_inventory','potion_effects','potion_stats','returned_potions','protection_credits'):
            conn.execute(f'DELETE FROM {table} WHERE guild_id=? AND player_id=?',(guild_id,player_id))
        columns=[r[1] for r in conn.execute('PRAGMA table_info(players)') if r[1] not in ('guild_id','player_id','frozen')]
        conn.execute('UPDATE players SET '+','.join('"'+c+'"=0' for c in columns)+' WHERE guild_id=? AND player_id=?',(guild_id,player_id))
        conn.execute('INSERT OR REPLACE INTO player_rejoins VALUES(?,?,?)',(guild_id,player_id,now+REJOIN_SECONDS))
        potions.audit(conn,guild_id,player_id,'leave',dict(rejoin_at=now+REJOIN_SECONDS))
        return True


def clear_for_reset(conn, guild_id, player_id):
    for table in ('player_freezes','player_rejoins','returned_potions','protection_credits','player_protection'):
        conn.execute(f'DELETE FROM {table} WHERE guild_id=? AND player_id=?',(guild_id,player_id))
