"""Administrative balance corrections; never update gameplay or cauldron counters."""
import db_utils as db
import potions


class CandyError(ValueError):
    pass


def adjust(guild_id, moderator_id, player_id, action, amount, include_moderator, action_id):
    if action not in ('give', 'take') or type(amount) is not int or amount <= 0:
        raise CandyError('invalid_amount')
    with db.transaction() as conn:
        previous = potions.prior_action(conn, guild_id, action_id, moderator_id, 'mod_candy')
        if previous is not None:
            return previous, True
        row = conn.execute('SELECT candy_in_bucket FROM players WHERE guild_id=? AND player_id=?', (guild_id, player_id)).fetchone()
        if row is None:
            raise CandyError('not_joined')
        balance = row[0]
        if action == 'take' and amount > balance:
            raise CandyError('insufficient')
        after = balance + (amount if action == 'give' else -amount)
        if after < 0 or after > 2**63-1:
            raise CandyError('balance_limit')
        conn.execute('UPDATE players SET candy_in_bucket=? WHERE guild_id=? AND player_id=?', (after, guild_id, player_id))
        result = dict(player_id=player_id, action=action, amount=amount, include_moderator=include_moderator)
        potions.record_action(conn, guild_id, action_id, moderator_id, 'mod_candy', result)
        return result, False
