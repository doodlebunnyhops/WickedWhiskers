"""Shared cauldron eligibility, weighting and distinct-player selection."""
import random

OUTCOMES = {
    'luna': [('normal', 76.5), ('fumble', 15), ('special', 8.5)],
    'raven': [('normal', 76.5), ('explosion', 15), ('rage', 8.5)],
}


def candidates(players, witch, outcome):
    """All supplied active players retain baseline weight 1, including newcomers."""
    if witch not in OUTCOMES or outcome not in dict(OUTCOMES[witch]):
        raise ValueError('Unknown cauldron outcome')
    result = {}
    for uid, candy, purchased, treats, given, successes, failures, stolen in players:
        treats, successes = max(0, treats), max(0, successes)
        preferred, other = (treats, successes) if witch == 'luna' else (successes, treats)
        bonus = max(0, preferred - other) if outcome in ('special', 'rage') else preferred
        result[uid] = 1 + bonus
    return list(result.items())


def roll_outcome(witch):
    if witch not in OUTCOMES:
        raise ValueError('Unknown witch')
    outcomes = OUTCOMES[witch]
    if random.random() < 0.15:
        return outcomes[1][0]
    if random.random() < 0.10:
        return outcomes[2][0]
    return 'normal'


def select_winners(weighted_players, mode, max_winners=None):
    """Weighted sampling without replacement; never expand weights into tickets."""
    remaining = dict(weighted_players)
    if not remaining:
        return []
    limit = min(len(remaining), max_winners) if max_winners is not None else len(remaining)
    count = random.randint(2, limit) if mode == 'many' and limit >= 2 else 1
    selected = []
    for _ in range(count):
        uid = random.choices(list(remaining), weights=list(remaining.values()), k=1)[0]
        selected.append(uid)
        del remaining[uid]
    return selected


def eligibility_report(players):
    report = {}
    for witch, outcomes in OUTCOMES.items():
        for outcome, chance in outcomes:
            report[f'{witch.title()} {outcome} ({chance:g}%)'] = {
                'witch': witch, 'outcome': outcome, 'chance': chance,
                'players': candidates(players, witch, outcome),
            }
    return report


class CauldronError(ValueError):
    pass


def award_pool(guild_id, action_id, caster_id, witch, mode):
    """Commit one complete draw and payout. No network awaits inside this transaction."""
    import json
    import db_utils as db
    with db.transaction() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS cauldron_draws (guild_id INTEGER NOT NULL, action_id TEXT NOT NULL, result TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(guild_id, action_id))")
        previous = conn.execute('SELECT result FROM cauldron_draws WHERE guild_id=? AND action_id=?', (guild_id, str(action_id))).fetchone()
        if previous:
            return json.loads(previous[0]), True
        players = db.get_active_players_by_guild(guild_id)
        if not players:
            raise CauldronError('no_players')
        pool = conn.execute('SELECT candy_in_cauldron FROM cauldron_pool WHERE guild_id=?', (guild_id,)).fetchone()
        amount = pool[0] if pool else 0
        if amount <= 0:
            raise CauldronError('empty_pool')
        outcome = roll_outcome(witch)
        selected = select_winners(candidates(players, witch, outcome), mode, max_winners=amount)
        share, remainder = divmod(amount, len(selected))
        awards = []
        for index, uid in enumerate(selected):
            reward = share + (1 if index < remainder else 0)
            updated = conn.execute('UPDATE players SET candy_in_bucket=candy_in_bucket+? WHERE guild_id=? AND player_id=? AND active=1', (reward, guild_id, uid))
            if updated.rowcount != 1:
                raise CauldronError('payout_failed')
            awards.append({'player_id': uid, 'amount': reward})
        conn.execute('UPDATE cauldron_pool SET candy_in_cauldron=0 WHERE guild_id=?', (guild_id,))
        conn.execute('INSERT INTO cauldron_event (guild_id,caster_id,witch,outcome,num_players_rewarded,total_candy_given) VALUES (?,?,?,?,?,?)', (guild_id,caster_id,witch,outcome,len(awards),amount))
        result = dict(witch=witch, outcome=outcome, awards=awards, amount=amount, remaining=0)
        conn.execute('INSERT INTO cauldron_draws (guild_id,action_id,result) VALUES (?,?,?)', (guild_id,str(action_id),json.dumps(result)))
        return result, False
