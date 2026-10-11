"""Persistent cauldron schedules; claims and payouts share the database transaction."""
import math
import random
import time
import db_utils as db
from utils.messages import default_messages

DEFAULTS=dict(enabled=False,trigger='interval',interval_minutes=None,candy_threshold=None,witch='random',winners='random',minimum_gap_minutes=5,last_cast=None,started_at=None)


def text(key,**values):
    return default_messages().get_message('auto_cauldron',key,**values)


def initialize_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS auto_cauldron (
        guild_id INTEGER PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 0,
        trigger TEXT NOT NULL DEFAULT 'interval', interval_minutes INTEGER,
        candy_threshold INTEGER, witch TEXT NOT NULL DEFAULT 'random',
        winners TEXT NOT NULL DEFAULT 'random', minimum_gap_minutes INTEGER NOT NULL DEFAULT 5,
        last_cast REAL, started_at REAL)''')
    conn.execute('CREATE INDEX IF NOT EXISTS auto_cauldron_enabled ON auto_cauldron(enabled)')


def settings(guild_id):
    row=db.get_db_connection().execute('SELECT '+','.join(DEFAULTS)+' FROM auto_cauldron WHERE guild_id=?',(guild_id,)).fetchone()
    return dict(zip(DEFAULTS,row)) if row else dict(DEFAULTS)


def event_channel(guild):
    channel_id=db.get_event_channel(guild.id)
    channel=guild.get_channel(channel_id) if channel_id else None
    if channel is None:
        return None,'event_channel_missing'
    permissions=channel.permissions_for(guild.me)
    if not all(getattr(permissions,key,False) for key in ('view_channel','send_messages','embed_links','attach_files')):
        return None,'event_channel_denied'
    return channel,None


def configure(guild_id, *, guild=None, now=None, **updates):
    if any(k not in DEFAULTS or k in ('last_cast','started_at') for k in updates):
        raise ValueError(text('invalid'))
    updates={k:v for k,v in updates.items() if v is not None}
    now=time.time() if now is None else now
    with db.transaction() as conn:
        old=settings(guild_id)
        values={**old,**updates}
        if 'enabled' in updates and type(updates['enabled']) is not bool:
            raise ValueError(text('invalid'))
        if values['trigger'] not in ('interval','threshold','either') or values['witch'] not in ('luna','raven','random') or values['winners'] not in ('one','many','random'):
            raise ValueError(text('invalid'))
        for key in ('interval_minutes','candy_threshold','minimum_gap_minutes'):
            value=values[key]
            if value is not None and (type(value) is not int or not 1<=value<=2147483647):
                raise ValueError(text('invalid'))
        if values['enabled']:
            if values['trigger'] in ('interval','either') and values['interval_minutes'] is None:
                raise ValueError(text('interval_required'))
            if values['trigger'] in ('threshold','either') and values['candy_threshold'] is None:
                raise ValueError(text('threshold_required'))
            if guild is not None:
                _,error=event_channel(guild)
                if error:
                    raise ValueError(default_messages().get_message('cauldron',error))
        if values['enabled'] and not old['enabled']:
            values['started_at']=now
        conn.execute('INSERT OR REPLACE INTO auto_cauldron (guild_id,'+','.join(DEFAULTS)+') VALUES ('+','.join('?' for _ in range(len(DEFAULTS)+1))+')',(guild_id,*values.values()))
    return settings(guild_id)


def mark_cast(conn,guild_id,now=None):
    conn.execute('INSERT OR IGNORE INTO auto_cauldron(guild_id) VALUES(?)',(guild_id,))
    conn.execute('UPDATE auto_cauldron SET last_cast=? WHERE guild_id=?',(time.time() if now is None else now,guild_id))


def next_interval(values):
    if values['interval_minutes'] is None:
        return None
    baseline=max(values['last_cast'] or 0,values['started_at'] or 0)
    return max(baseline+values['interval_minutes']*60,(values['last_cast'] or 0)+values['minimum_gap_minutes']*60)


def due(guild_id,now=None):
    now=time.time() if now is None else now
    values=settings(guild_id)
    if not values['enabled'] or db.get_game_settings(guild_id)[0]:
        return False
    if values['last_cast'] is not None and now<values['last_cast']+values['minimum_gap_minutes']*60:
        return False
    pool=db.get_cauldron_pool(guild_id)
    if pool<=0:
        return False
    interval=next_interval(values)
    by_time=values['trigger'] in ('interval','either') and interval is not None and now>=interval
    by_pool=values['trigger'] in ('threshold','either') and values['candy_threshold'] is not None and pool>=values['candy_threshold']
    return bool(by_time or by_pool)


def claim(guild_id,action_id,caster_id,now=None):
    from utils.cauldron import award_pool
    now=time.time() if now is None else now
    with db.transaction():
        if not due(guild_id,now):
            return None
        values=settings(guild_id)
        witch=random.choice(('luna','raven')) if values['witch']=='random' else values['witch']
        winners=random.choice(('one','many')) if values['winners']=='random' else values['winners']
        result,repeated=award_pool(guild_id,action_id,caster_id,witch,winners,now=now)
        return None if repeated else result


def describe(guild_id,guild=None):
    values=settings(guild_id)
    next_at=next_interval(values)
    blockers=[]
    if not values['enabled']:blockers.append(text('disabled'))
    if db.get_game_settings(guild_id)[0]:blockers.append(text('paused'))
    if db.get_cauldron_pool(guild_id)<=0:blockers.append(text('empty'))
    if not db.get_active_players_by_guild(guild_id):blockers.append(text('no_players'))
    if guild is not None:
        _,error=event_channel(guild)
        if error:blockers.append(default_messages().get_message('cauldron',error))
    if values['last_cast'] and time.time()<values['last_cast']+values['minimum_gap_minutes']*60:
        blockers.append(text('gap_until',expiry=math.ceil(values['last_cast']+values['minimum_gap_minutes']*60)))
    shown={k:(text('unset') if v is None else v) for k,v in values.items()}
    shown['enabled']=text('enabled') if values['enabled'] else text('disabled')
    shown['next_time']=f'<t:{math.ceil(next_at)}:R>' if values['enabled'] and values['trigger']!='threshold' and next_at else text('not_scheduled')
    return text('summary',**shown,blockers='; '.join(blockers) or text('waiting'))
