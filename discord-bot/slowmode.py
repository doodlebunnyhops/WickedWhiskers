"""Persistent per-guild, per-player action cooldowns. Call checks inside transactions."""
import math
import time
import db_utils as db
from utils.messages import default_messages

ACTIONS=('trick','treat','smash')
MAX_SECONDS=86400


def text(key,**values):
    return default_messages().get_message('slowmode',key,**values)


class SlowmodeError(ValueError):
    def __init__(self,action,ready):
        super().__init__(text('wait',action=text(action),expiry=math.ceil(ready)))


def initialize_schema(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS action_slowmode (guild_id INTEGER, action TEXT, seconds INTEGER NOT NULL, PRIMARY KEY(guild_id,action))')
    conn.execute('CREATE TABLE IF NOT EXISTS action_last_used (guild_id INTEGER, player_id INTEGER, action TEXT, used_at REAL NOT NULL, PRIMARY KEY(guild_id,player_id,action))')


def settings(guild_id):
    result=dict.fromkeys(ACTIONS,0)
    result.update(db.get_db_connection().execute('SELECT action,seconds FROM action_slowmode WHERE guild_id=?',(guild_id,)))
    return result


def configure(guild_id,**updates):
    if any(k not in ACTIONS or type(v) is not int or not 0<=v<=MAX_SECONDS for k,v in updates.items()):
        raise ValueError('Invalid slowmode setting')
    with db.transaction() as conn:
        old=settings(guild_id)
        for action,seconds in updates.items():
            conn.execute('INSERT OR REPLACE INTO action_slowmode VALUES(?,?,?)',(guild_id,action,seconds))
            # Changing a setting starts a fresh clock; disabling never retains an old lock.
            if seconds!=old[action]:
                conn.execute('DELETE FROM action_last_used WHERE guild_id=? AND action=?',(guild_id,action))
    return settings(guild_id)


def check(conn,guild_id,player_id,action,now=None):
    seconds=settings(guild_id)[action]
    if not seconds:return
    now=time.time() if now is None else now
    row=conn.execute('SELECT used_at FROM action_last_used WHERE guild_id=? AND player_id=? AND action=?',(guild_id,player_id,action)).fetchone()
    if row and now<row[0]+seconds:
        raise SlowmodeError(action,row[0]+seconds)


def mark(conn,guild_id,player_id,action,now=None):
    if settings(guild_id)[action]:
        conn.execute('INSERT OR REPLACE INTO action_last_used VALUES(?,?,?,?)',(guild_id,player_id,action,time.time() if now is None else now))
