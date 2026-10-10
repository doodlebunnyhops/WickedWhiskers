"""Pumpkin outcomes are net changes, settled exactly once per interaction."""
import random
from fractions import Fraction
import time
import db_utils as db
import potions


class PumpkinError(ValueError):
    pass


def smaller_bucket_boost(conn, guild_id, balance, now=None):
    """Positive active/unfrozen buckets, including Veil users who can smash.

Unclaimed income and the cauldron are intentionally absent from this query.
"""
    now=int(time.time()) if now is None else int(now)
    balances=[row[0] for row in conn.execute("""
        SELECT p.candy_in_bucket FROM players p
        LEFT JOIN player_freezes f ON f.guild_id=p.guild_id AND f.player_id=p.player_id
        WHERE p.guild_id=? AND p.active=1 AND p.candy_in_bucket>0
        AND ((f.player_id IS NULL AND COALESCE(p.frozen,0)=0)
             OR (f.player_id IS NOT NULL AND f.until_at IS NOT NULL AND f.until_at<=?))
        ORDER BY p.candy_in_bucket
    """,(guild_id,now))]
    if len(balances)<3:
        return 0.0,len(balances)
    n=len(balances)
    median=Fraction(balances[n//2]) if n%2 else Fraction(balances[n//2-1]+balances[n//2],2)
    return float(Fraction(1,20)*max(0,1-Fraction(balance)/median)),n


def roll_amount(wager, balance, outcome, rng):
    """Uniform multiplier, nearest integer (halves up), minimum one.

Rational arithmetic avoids overflow/precision loss for SQLite-sized balances.
"""
    risk=Fraction(wager,balance)
    if outcome=='win_extra':
        low,high=1-risk/2,1+risk/2
    elif outcome in ('win','lose'):
        low,high=Fraction(2,5)-risk/5,Fraction(3,5)+risk/5
    else:
        low,high=Fraction(1),Fraction(2)
    amount=wager*(low+Fraction(rng.random())*(high-low))+Fraction(1,2)
    return max(1,amount.numerator//amount.denominator)


def smash(guild_id, player_id, wager, action_id, rng=random):
    with db.transaction() as conn:
        previous = potions.prior_action(conn, guild_id, action_id, player_id, 'pumpkin')
        if previous is not None:
            return previous, True
        if db.get_game_settings(guild_id)[0]:
            raise PumpkinError('paused')
        data = db.get_player_data(player_id, guild_id)
        if not data or not data['active']:
            raise PumpkinError('not_joined')
        if db.is_player_frozen(player_id, guild_id):
            raise PumpkinError('frozen')
        if type(wager) is not int or wager <= 0:
            raise PumpkinError('invalid_wager')
        balance = data['candy_in_bucket']
        if wager > balance:
            raise PumpkinError('insufficient')
        boost,comparison_count = smaller_bucket_boost(conn,guild_id,balance)
        roll = rng.random()
        if roll < .10:
            outcome = 'win_extra'
        elif roll < .40 + boost:
            outcome = 'win'
        elif roll < .60:
            outcome = 'break_even'
        elif roll < .90:
            outcome = 'lose'
        else:
            outcome = 'lose_double'
        amount = 0 if outcome=='break_even' else roll_amount(wager,balance,outcome,rng)
        delta = amount if outcome in ('win','win_extra') else -min(amount,balance)
        after = balance + delta
        if after > 2**63-1:
            raise PumpkinError('balance_limit')
        # Narration follows the actual magnitude, not overlapping roll categories.
        message_key = ('lose_all' if delta<0 and after==0 else
                       'lose_double' if delta<0 and -delta>=wager else
                       'lose' if delta<0 else
                       'win_extra' if delta>0 and delta>=wager else
                       'win' if delta>0 else 'break_even')
        contribution = 0
        magic = None
        if delta > 0 and rng.random() < .30:
            magic, contribution = 'luna', delta
        elif delta < 0 and rng.random() < .90:
            magic, contribution = 'raven', -delta
        conn.execute('UPDATE players SET candy_in_bucket=?, pumpkins_smashed=pumpkins_smashed+1, total_candy_spent_on_pumpkins=total_candy_spent_on_pumpkins+?, total_candy_won_from_pumpkins=total_candy_won_from_pumpkins+?, total_candy_lost_on_pumpkins=total_candy_lost_on_pumpkins+? WHERE guild_id=? AND player_id=?', (after, wager, max(delta, 0), max(-delta, 0), guild_id, player_id))
        if contribution:
            db.update_cauldron_pool(guild_id, contribution)
            db.update_cauldron_contribution(player_id, guild_id, contribution)
        from player_state import protection_info
        result = dict(protected=bool(protection_info(guild_id, player_id)), outcome=outcome, win_boost=boost, comparison_count=comparison_count, risk=wager/balance, message_key=message_key, wager=wager, delta=delta, balance=after, magic=magic, contribution=contribution)
        potions.record_action(conn, guild_id, action_id, player_id, 'pumpkin', result)
        return result, False
