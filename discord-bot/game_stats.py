"""Seasonal counters, updated within the gameplay transaction that earned them."""
import time
import db_utils as db


def initialize_schema(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS player_metrics (guild_id INTEGER, player_id INTEGER, potion_id TEXT NOT NULL, metric TEXT NOT NULL, value INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(guild_id,player_id,potion_id,metric))')
    conn.execute('CREATE INDEX IF NOT EXISTS player_metrics_board ON player_metrics(guild_id,metric,player_id)')


def add(conn, guild_id, player_id, metric, amount=1, potion_id=''):
    if amount:
        conn.execute('INSERT INTO player_metrics VALUES(?,?,?,?,?) ON CONFLICT(guild_id,player_id,potion_id,metric) DO UPDATE SET value=value+excluded.value', (guild_id,player_id,potion_id,metric,amount))


def totals(guild_id, player_id):
    return dict(db.get_db_connection().execute('SELECT metric,SUM(value) FROM player_metrics WHERE guild_id=? AND player_id=? GROUP BY metric',(guild_id,player_id)))


def potion_details(guild_id, player_id):
    result = {}
    for potion,metric,value in db.get_db_connection().execute('SELECT potion_id,metric,value FROM player_metrics WHERE guild_id=? AND player_id=? AND potion_id<>?',(guild_id,player_id,'')):
        result.setdefault(potion,{})[metric]=value
    return result


def protection_seconds(guild_id, player_id, now=None):
    conn=db.get_db_connection()
    row=conn.execute('SELECT start_at,end_at FROM player_protection WHERE guild_id=? AND player_id=?',(guild_id,player_id)).fetchone()
    elapsed=max(0,min(int(time.time() if now is None else now),row[1])-row[0]) if row else 0
    return totals(guild_id,player_id).get('protection_seconds',0)+elapsed


def settle_protection(conn, guild_id, player_id, now):
    row=conn.execute('SELECT start_at,end_at FROM player_protection WHERE guild_id=? AND player_id=?',(guild_id,player_id)).fetchone()
    if row:
        add(conn,guild_id,player_id,'protection_seconds',max(0,min(now,row[1])-row[0]),'veil')
