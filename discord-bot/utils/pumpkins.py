"""Pumpkin outcomes are net changes, settled exactly once per interaction."""
import random
import db_utils as db
import potions


class PumpkinError(ValueError):
    pass


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
        half = (wager + 1) // 2
        roll = rng.random()
        if roll < .10:
            outcome, delta = 'win_extra', wager
        elif roll < .40:
            outcome, delta = 'win', half
        elif roll < .60:
            outcome, delta = 'break_even', 0
        elif roll < .90:
            outcome, delta = 'lose', -min(half, balance)
        else:
            outcome, delta = 'lose_double', -min(2 * wager, balance)
        after = balance + delta
        if after > 2**63-1:
            raise PumpkinError('balance_limit')
        message_key = 'lose_all' if delta < 0 and after == 0 else outcome
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
        result = dict(protected=bool(protection_info(guild_id, player_id)), outcome=outcome, message_key=message_key, wager=wager, delta=delta, balance=after, magic=magic, contribution=contribution)
        potions.record_action(conn, guild_id, action_id, player_id, 'pumpkin', result)
        return result, False
