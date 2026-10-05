"""Seasonal potion inventory and effects. All mutating actions are synchronous transactions."""
from dataclasses import dataclass
import json
import random
import time

import db_utils as db
import game_stats as stats


@dataclass(frozen=True)
class Potion:
    name: str
    description: str
    price: int
    charges: int = 0


CATALOG = {
    "ward": Potion("Witch's Ward", "Blocks one incoming player trick. Does not protect against pumpkins or cauldron events.", 5, 1),
    "cunning": Potion("Raven's Cunning", "+15 percentage points on the next 3 eligible initial trick rolls. Special events still apply.", 5, 3),
    "mirror": Potion("Mirror Brew", "Redirects the next incoming trick attempt, possibly back to its caster. Cannot coexist with Ward.", 10, 1),
    "sticky": Potion("Sticky Fingers", "+25% candy (rounded up) on your next ordinary successful theft, capped by the target's balance.", 8, 1),
    "second_chance": Potion("Second Chance", "Rerolls your next failed initial trick roll once. Cannot bypass protection.", 8, 1),
    "favor": Potion("Luna's Favor", "On your next ordinary treat of 2+ candy, Luna adds half the gift (rounded down), up to 5 candy.", 5, 1),
    "luna": Potion("Luna's Calling", "Gives 5 candy each to up to 3 random other active, unfrozen players. 60-second server cooldown.", 10),
}
MAX_QUANTITY = 100
MAX_PRICE = 1_000_000
LUNA_COOLDOWN = 60


class PotionError(ValueError):
    pass


class PotionCooldownError(PotionError):
    """A rejected activation; no inventory has been consumed."""
    pass


class PriceChanged(PotionError):
    def __init__(self, price):
        self.price = price
        super().__init__(f"The price changed to {price} candy each. Review the new total and confirm again.")


def initialize_schema(conn):
    stats.initialize_schema(conn)
    statements = [
        "CREATE TABLE IF NOT EXISTS potion_inventory (guild_id INTEGER, player_id INTEGER, potion_id TEXT, quantity INTEGER NOT NULL CHECK(quantity >= 0), PRIMARY KEY(guild_id, player_id, potion_id))",
        "CREATE TABLE IF NOT EXISTS potion_effects (guild_id INTEGER, player_id INTEGER, potion_id TEXT, charges INTEGER NOT NULL CHECK(charges >= 0), PRIMARY KEY(guild_id, player_id, potion_id))",
        "CREATE TABLE IF NOT EXISTS potion_prices (guild_id INTEGER, potion_id TEXT, price INTEGER NOT NULL CHECK(price > 0), enabled INTEGER NOT NULL DEFAULT 1, PRIMARY KEY(guild_id, potion_id))",
        "CREATE TABLE IF NOT EXISTS potion_managers (guild_id INTEGER PRIMARY KEY, role_id INTEGER)",
        "CREATE TABLE IF NOT EXISTS potion_cooldowns (guild_id INTEGER, effect TEXT, available_at REAL, PRIMARY KEY(guild_id, effect))",
        "CREATE TABLE IF NOT EXISTS potion_actions (guild_id INTEGER, action_id TEXT, player_id INTEGER, kind TEXT, result TEXT NOT NULL, PRIMARY KEY(guild_id, action_id))",
        "CREATE TABLE IF NOT EXISTS potion_audit (id INTEGER PRIMARY KEY, guild_id INTEGER, actor_id INTEGER, kind TEXT, details TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS potion_stats (guild_id INTEGER, player_id INTEGER, tricks_blocked INTEGER NOT NULL DEFAULT 0, luna_summons INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(guild_id, player_id))",
    ]
    for statement in statements:
        conn.execute(statement)


def item(potion_id):
    if potion_id not in CATALOG:
        raise PotionError("Unknown potion.")
    return CATALOG[potion_id]


def offer(guild_id, potion_id):
    potion = item(potion_id)
    row = db.get_db_connection().execute("SELECT price, enabled FROM potion_prices WHERE guild_id=? AND potion_id=?", (guild_id, potion_id)).fetchone()
    return (row[0], bool(row[1])) if row else (potion.price, True)


def eligible(guild_id, player_id):
    from player_state import require
    require(guild_id, player_id, "shop")
    if db.get_game_settings(guild_id)[0]:
        raise PotionError("The game is paused.")
    row = db.get_db_connection().execute("SELECT candy_in_bucket, active, frozen FROM players WHERE guild_id=? AND player_id=?", (guild_id, player_id)).fetchone()
    if not row or not row[1]:
        raise PotionError("Join the game before using the shop.")
    return row[0]


def inventory(guild_id, player_id):
    conn = db.get_db_connection()
    bottles = dict(conn.execute("SELECT potion_id, quantity FROM potion_inventory WHERE guild_id=? AND player_id=?", (guild_id, player_id)))
    for key, count in conn.execute("SELECT potion_id,COUNT(*) FROM returned_potions WHERE guild_id=? AND player_id=? GROUP BY potion_id", (guild_id,player_id)):
        bottles[key] = bottles.get(key,0) + count
    effects = dict(conn.execute("SELECT potion_id, charges FROM potion_effects WHERE guild_id=? AND player_id=? AND charges>0", (guild_id, player_id)))
    return bottles, effects


def audit(conn, guild_id, actor_id, kind, details):
    conn.execute("INSERT INTO potion_audit(guild_id, actor_id, kind, details) VALUES(?,?,?,?)", (guild_id, actor_id, kind, json.dumps(details)))


def prior_action(conn, guild_id, action_id, actor_id, kind):
    row = conn.execute("SELECT player_id, kind, result FROM potion_actions WHERE guild_id=? AND action_id=?", (guild_id, str(action_id))).fetchone()
    if row:
        if row[0] != actor_id or row[1] != kind:
            raise PotionError("This action belongs to another request.")
        return json.loads(row[2])


def record_action(conn, guild_id, action_id, actor_id, kind, result):
    conn.execute("INSERT INTO potion_actions VALUES(?,?,?,?,?)", (guild_id, str(action_id), actor_id, kind, json.dumps(result)))
    audit(conn, guild_id, actor_id, kind, result)
    return result


def grant(conn, guild_id, player_id, potion_id, quantity=1):
    item(potion_id)
    if type(quantity) is not int or quantity <= 0:
        raise PotionError("Invalid gift quantity.")
    conn.execute("INSERT INTO potion_inventory VALUES(?,?,?,?) ON CONFLICT(guild_id,player_id,potion_id) DO UPDATE SET quantity=quantity+excluded.quantity", (guild_id, player_id, potion_id, quantity))


def purchase(guild_id, buyer_id, potion_id, quantity, quoted_price, action_id):
    potion = item(potion_id)
    if type(quantity) is not int or not 1 <= quantity <= MAX_QUANTITY:
        raise PotionError(f"Choose a whole quantity from 1 to {MAX_QUANTITY}.")
    with db.transaction() as conn:
        previous = prior_action(conn, guild_id, action_id, buyer_id, "purchase")
        if previous is not None:
            return previous
        eligible(guild_id, buyer_id)
        price, enabled = offer(guild_id, potion_id)
        if not enabled:
            raise PotionError("This potion is currently unavailable for purchase.")
        if price != quoted_price:
            raise PriceChanged(price)
        total = price * quantity
        updated = conn.execute("UPDATE players SET candy_in_bucket=candy_in_bucket-? WHERE guild_id=? AND player_id=? AND candy_in_bucket>=?", (total, guild_id, buyer_id, total))
        if updated.rowcount != 1:
            raise PotionError(f"You need {total} candy for this purchase.")
        grant(conn, guild_id, buyer_id, potion_id, quantity)
        stats.add(conn,guild_id,buyer_id,"purchased",quantity,potion_id)
        stats.add(conn,guild_id,buyer_id,"spent",total,potion_id)
        balance = eligible(guild_id, buyer_id)
        return record_action(conn, guild_id, action_id, buyer_id, "purchase", {"potion": potion_id, "name": potion.name, "quantity": quantity, "cost": total, "balance": balance})


def use(guild_id, player_id, potion_id, action_id, member_ids=None, now=None, rng=random):
    potion = item(potion_id)
    now = time.time() if now is None else now
    with db.transaction() as conn:
        previous = prior_action(conn, guild_id, action_id, player_id, "use")
        if previous is not None:
            return dict(previous, replayed=True)
        eligible(guild_id, player_id)
        from player_state import require, visible
        require(guild_id, player_id, "use", now)
        bottles, effects = inventory(guild_id, player_id)
        if bottles.get(potion_id, 0) < 1:
            raise PotionError("You don't own that potion.")
        if effects.get(potion_id, 0):
            raise PotionError("That potion is already active. Your bottle was not consumed.")
        opposing = {"ward": "mirror", "mirror": "ward"}.get(potion_id)
        if opposing and effects.get(opposing, 0):
            raise PotionError("Ward and Mirror cannot be active together. Your bottle was not consumed.")
        returned = conn.execute("SELECT id,charges FROM returned_potions WHERE guild_id=? AND player_id=? AND potion_id=? ORDER BY charges,id LIMIT 1",(guild_id,player_id,potion_id)).fetchone()
        charges = returned[1] if returned else potion.charges
        result = {"potion": potion_id, "name": potion.name, "charges": charges, "recipients": []}
        if potion_id == "luna":
            cooldown = conn.execute("SELECT available_at FROM potion_cooldowns WHERE guild_id=? AND effect='luna'", (guild_id,)).fetchone()
            if cooldown and cooldown[0] > now:
                raise PotionCooldownError(f"Luna is resting. Try again in {max(1, int(cooldown[0]-now+0.999))} seconds; your potion is safe.")
            if member_ids is None:
                raise PotionError("Couldn't verify server members. Your potion is safe; please try again.")
            candidates = [row[0] for row in conn.execute("SELECT player_id FROM players WHERE guild_id=? AND active=1 AND player_id<>?", (guild_id, player_id)) if row[0] in member_ids and visible(guild_id,row[0],now)]
            if not candidates:
                raise PotionError("No other eligible players are available. Your potion was not consumed.")
            recipients = rng.sample(candidates, min(3, len(candidates)))
            conn.executemany("UPDATE players SET candy_in_bucket=candy_in_bucket+5 WHERE guild_id=? AND player_id=?", [(guild_id, recipient) for recipient in recipients])
            conn.execute("INSERT INTO potion_cooldowns VALUES(?,'luna',?) ON CONFLICT(guild_id,effect) DO UPDATE SET available_at=excluded.available_at", (guild_id, now + LUNA_COOLDOWN))
            conn.execute("INSERT INTO potion_stats(guild_id,player_id,luna_summons) VALUES(?,?,1) ON CONFLICT(guild_id,player_id) DO UPDATE SET luna_summons=luna_summons+1", (guild_id, player_id))
            gifted = 5 * len(recipients)
            conn.execute('UPDATE players SET treats_given=treats_given+1,total_candy_given=total_candy_given+? WHERE guild_id=? AND player_id=?',(gifted,guild_id,player_id))
            stats.add(conn,guild_id,player_id,'gifted',gifted,potion_id)
            stats.add(conn,guild_id,player_id,'triggered',1,potion_id)
            result["recipients"] = recipients
        else:
            conn.execute("INSERT INTO potion_effects VALUES(?,?,?,?) ON CONFLICT(guild_id,player_id,potion_id) DO UPDATE SET charges=excluded.charges", (guild_id, player_id, potion_id, charges))
        stats.add(conn,guild_id,player_id,"activated",1,potion_id)
        if returned:
            conn.execute("DELETE FROM returned_potions WHERE id=?",(returned[0],))
        else:
            conn.execute("UPDATE potion_inventory SET quantity=quantity-1 WHERE guild_id=? AND player_id=? AND potion_id=?", (guild_id, player_id, potion_id))
        return record_action(conn, guild_id, action_id, player_id, "use", result)


def consume_charge(conn, guild_id, player_id, potion_id):
    from player_state import visible
    if not visible(guild_id, player_id):
        return False
    consumed = conn.execute("UPDATE potion_effects SET charges=charges-1 WHERE guild_id=? AND player_id=? AND potion_id=? AND charges>0", (guild_id, player_id, potion_id)).rowcount == 1
    if consumed:
        stats.add(conn,guild_id,player_id,'triggered',1,potion_id)
    return consumed


def block_trick(guild_id, attacker_id, target_id):
    conn = db.get_db_connection()
    if consume_charge(conn, guild_id, target_id, "ward"):
        conn.execute("INSERT INTO potion_stats(guild_id,player_id,tricks_blocked) VALUES(?,?,1) ON CONFLICT(guild_id,player_id) DO UPDATE SET tricks_blocked=tricks_blocked+1", (guild_id, target_id))
        stats.add(conn,guild_id,target_id,"defended",1,"ward")
        audit(conn, guild_id, target_id, "ward_block", {"attacker": attacker_id})
        return True
    return False


def trick_rate(guild_id, player_id, base_rate):
    conn = db.get_db_connection()
    if consume_charge(conn, guild_id, player_id, "cunning"):
        audit(conn, guild_id, player_id, "cunning_charge", {"base_rate": base_rate})
        return max(base_rate, min(0.95, base_rate + 0.15))
    return base_rate


def can_manage(member, guild_id):
    if member.guild_permissions.manage_guild:
        return True
    row = db.get_db_connection().execute("SELECT role_id FROM potion_managers WHERE guild_id=?", (guild_id,)).fetchone()
    return bool(row and any(role.id == row[0] for role in member.roles))


def set_manager_role(guild_id, actor_id, role_id):
    with db.transaction() as conn:
        old = conn.execute("SELECT role_id FROM potion_managers WHERE guild_id=?", (guild_id,)).fetchone()
        conn.execute("INSERT INTO potion_managers VALUES(?,?) ON CONFLICT(guild_id) DO UPDATE SET role_id=excluded.role_id", (guild_id, role_id))
        audit(conn, guild_id, actor_id, "manager_role", {"old": old[0] if old else None, "new": role_id})


def configure(guild_id, actor_id, potion_id, price, enabled):
    item(potion_id)
    if type(price) is not int or not 1 <= price <= MAX_PRICE:
        raise PotionError(f"Price must be a whole number from 1 to {MAX_PRICE}.")
    with db.transaction() as conn:
        before = offer(guild_id, potion_id)
        conn.execute("INSERT INTO potion_prices VALUES(?,?,?,?) ON CONFLICT(guild_id,potion_id) DO UPDATE SET price=excluded.price, enabled=excluded.enabled", (guild_id, potion_id, price, int(enabled)))
        audit(conn, guild_id, actor_id, "shop_setting", {"potion": potion_id, "old": before, "new": [price, enabled]})


def reset_prices(guild_id, actor_id, potion_id=None):
    ids = [potion_id] if potion_id else list(CATALOG)
    with db.transaction() as conn:
        for key in ids:
            default = item(key)
            old = offer(guild_id, key)
            # Reset prices only; preserve sale availability.
            configure(guild_id, actor_id, key, default.price, old[1])


def clear_player(conn, guild_id, player_id):
    for table in ("player_metrics", "potion_inventory", "potion_effects", "potion_stats", "potion_actions", "returned_potions", "protection_credits"):
        conn.execute(f"DELETE FROM {table} WHERE guild_id=? AND player_id=?", (guild_id, player_id))


def clear_season(conn, guild_id):
    for table in ("player_metrics", "potion_inventory", "potion_effects", "potion_stats", "potion_actions", "potion_cooldowns", "potion_audit", "player_freezes", "player_rejoins", "returned_potions", "protection_credits", "player_protection", "protection_cooldowns"):
        conn.execute(f"DELETE FROM {table} WHERE guild_id=?", (guild_id,))
