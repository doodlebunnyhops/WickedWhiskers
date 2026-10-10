"""Lazy, server-scoped earnings. Call state transitions before changing eligibility.

No presence events or background timer: persisted UTC timestamps account for offline
and restart time. All balance/claim mutations run in one SQLite transaction.
"""
import time
import db_utils as db

PERIOD = 600
DAILY_CAP = 100
RESERVE_CAP = 300
DAY = 86400
MAX_BALANCE = 2**63 - 1


class IncomeError(ValueError):
    pass


def clock(now=None):
    return int(time.time()) if now is None else int(now)


def initialize_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS passive_earnings (
        guild_id INTEGER, player_id INTEGER, last_at INTEGER NOT NULL,
        carry INTEGER NOT NULL DEFAULT 0 CHECK(carry BETWEEN 0 AND 599),
        pending INTEGER NOT NULL DEFAULT 0 CHECK(pending BETWEEN 0 AND 300),
        total_earned INTEGER NOT NULL DEFAULT 0, total_claimed INTEGER NOT NULL DEFAULT 0,
        total_forfeited INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(guild_id,player_id))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS passive_earning_days (
        guild_id INTEGER, player_id INTEGER, day INTEGER, earned INTEGER NOT NULL CHECK(earned BETWEEN 0 AND 100),
        PRIMARY KEY(guild_id,player_id,day))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS passive_claims (
        guild_id INTEGER, action_id TEXT, player_id INTEGER NOT NULL,
        amount INTEGER NOT NULL CHECK(amount>0), claimed_at INTEGER NOT NULL,
        PRIMARY KEY(guild_id,action_id))''')
    # Existing players begin at installation, never retroactively at season start.
    conn.execute('''INSERT OR IGNORE INTO passive_earnings(guild_id,player_id,last_at)
        SELECT guild_id,player_id,? FROM players''',(clock(),))


def ensure(conn, guild_id, player_id, now):
    conn.execute('INSERT OR IGNORE INTO passive_earnings(guild_id,player_id,last_at) VALUES(?,?,?)', (guild_id,player_id,now))


def day_earned(conn, guild_id, player_id, day):
    row=conn.execute('SELECT earned FROM passive_earning_days WHERE guild_id=? AND player_id=? AND day=?', (guild_id,player_id,day)).fetchone()
    return row[0] if row else 0


def settle(conn, guild_id, player_id, now=None):
    now=clock(now)
    ensure(conn,guild_id,player_id,now)
    last,carry,pending=conn.execute('SELECT last_at,carry,pending FROM passive_earnings WHERE guild_id=? AND player_id=?',(guild_id,player_id)).fetchone()
    # Never move a saved clock backwards (or accrue the same interval twice).
    now=max(now,last)
    row=conn.execute('SELECT active,frozen FROM players WHERE guild_id=? AND player_id=?',(guild_id,player_id)).fetchone()
    pause=conn.execute('SELECT game_disabled FROM game_settings WHERE guild_id=?',(guild_id,)).fetchone()
    start=last
    if not row or not row[0] or (pause and pause[0]):
        start=now
    else:
        freeze=conn.execute('SELECT until_at FROM player_freezes WHERE guild_id=? AND player_id=?',(guild_id,player_id)).fetchone()
        if freeze:
            start=now if freeze[0] is None else min(now,max(start,freeze[0]))
        elif row[1]:
            start=now
    earned=0
    while start < now and pending < RESERVE_CAP:
        day=start//DAY
        end=min(now,(day+1)*DAY)
        used=day_earned(conn,guild_id,player_id,day)
        if used>=DAILY_CAP:
            carry=0
        else:
            seconds=carry+end-start
            count=min(seconds//PERIOD,DAILY_CAP-used,RESERVE_CAP-pending)
            if count:
                conn.execute('''INSERT INTO passive_earning_days VALUES(?,?,?,?)
                    ON CONFLICT(guild_id,player_id,day) DO UPDATE SET earned=earned+excluded.earned''', (guild_id,player_id,day,count))
                earned+=count;pending+=count
            carry=0 if used+count>=DAILY_CAP or pending>=RESERVE_CAP else seconds%PERIOD
        start=end
    if pending>=RESERVE_CAP:
        carry=0
    conn.execute('''UPDATE passive_earnings SET last_at=?,carry=?,pending=?,total_earned=total_earned+?
        WHERE guild_id=? AND player_id=?''',(now,carry,pending,earned,guild_id,player_id))
    return dict(pending=pending,earned_today=day_earned(conn,guild_id,player_id,now//DAY),daily_cap=DAILY_CAP,reserve_cap=RESERVE_CAP,reset_at=(now//DAY+1)*DAY)


def status(guild_id, player_id, now=None):
    with db.transaction() as conn:
        result=settle(conn,guild_id,player_id,now)
        row=conn.execute('SELECT total_earned,total_claimed,total_forfeited FROM passive_earnings WHERE guild_id=? AND player_id=?',(guild_id,player_id)).fetchone()
        result.update(zip(('total_earned','total_claimed','total_forfeited'),row))
        return result


def settle_guild(conn, guild_id, now=None):
    now=clock(now)
    for (uid,) in conn.execute('SELECT player_id FROM players WHERE guild_id=?',(guild_id,)).fetchall():
        settle(conn,guild_id,uid,now)


def restart_clock(conn, guild_id, player_id, now=None):
    now=clock(now);ensure(conn,guild_id,player_id,now)
    conn.execute('UPDATE passive_earnings SET last_at=MAX(last_at,?) WHERE guild_id=? AND player_id=?',(now,guild_id,player_id))


def forfeit(conn, guild_id, player_id, now=None):
    settle(conn,guild_id,player_id,now)
    conn.execute('''UPDATE passive_earnings SET total_forfeited=total_forfeited+pending,pending=0,carry=0
        WHERE guild_id=? AND player_id=?''',(guild_id,player_id))


def claim(guild_id, player_id, action_id, now=None):
    now=clock(now)
    with db.transaction() as conn:
        previous=conn.execute('SELECT player_id,amount FROM passive_claims WHERE guild_id=? AND action_id=?',(guild_id,str(action_id))).fetchone()
        if previous:
            if previous[0]!=player_id:
                raise IncomeError('not_owner')
            return dict(amount=previous[1],repeated=True)
        row=conn.execute('SELECT active,candy_in_bucket FROM players WHERE guild_id=? AND player_id=?',(guild_id,player_id)).fetchone()
        if not row or not row[0]:
            raise IncomeError('not_joined')
        from player_state import freeze_info
        if freeze_info(guild_id,player_id,now):
            raise IncomeError('frozen')
        pause=conn.execute('SELECT game_disabled FROM game_settings WHERE guild_id=?',(guild_id,)).fetchone()
        if pause and pause[0]:
            raise IncomeError('paused')
        result=settle(conn,guild_id,player_id,now)
        amount=result['pending']
        if not amount:
            return dict(amount=0,repeated=False)
        if row[1]>MAX_BALANCE-amount:
            raise IncomeError('balance_limit')
        conn.execute('UPDATE players SET candy_in_bucket=candy_in_bucket+? WHERE guild_id=? AND player_id=?',(amount,guild_id,player_id))
        conn.execute('UPDATE passive_earnings SET pending=0,total_claimed=total_claimed+? WHERE guild_id=? AND player_id=?',(amount,guild_id,player_id))
        conn.execute('INSERT INTO passive_claims VALUES(?,?,?,?,?)',(guild_id,str(action_id),player_id,amount,now))
        return dict(amount=amount,repeated=False)
