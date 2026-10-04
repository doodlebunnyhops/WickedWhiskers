# Pumpkin smashing

Use `/smash_pumpkin amount:<wager>`. The wager must be a positive whole number no larger than your current bucket. There is **no separate entry fee**. Each result below is the actual net change to your bucket.

| Outcome | Chance | Net change | Example: wager 10 |
| --- | --- | --- | --- |
| Big win | 10% | +wager | +10 |
| Small reward | 30% | +half wager, rounded up | +5 |
| Break even | 20% | 0 | 0 |
| Normal loss | 30% | −half wager, rounded up | −5 |
| Big loss | 10% | −twice wager, capped at bucket balance | −20, or everything left if less |

Small rewards and normal losses have equal odds and equal magnitude. This is still a risky game: before the loss cap, average net return is −10% of the wager because big losses are larger than big wins.

A big loss can drain the entire bucket. With 15 candy and a wager of 10, a big loss takes 15, leaving zero. It never creates a negative balance. Any loss that leaves zero uses the empty-bucket message, including a normal loss of a player's final single candy.

Luna has a 30% chance after a win to create a copy of the winnings in the cauldron. The player keeps the full win. Raven has a 90% chance after a loss to send the actual lost candy into the cauldron; this is not another charge. Break-even results do not trigger either contribution.

The private reply and event-channel embed show the wager, signed net change, and remaining bucket. Messages and variations are editable under `smash_pumpkin` in `discord-bot/utils/messages.json`, loaded through `MessageLoader` in `messages.py`. Magical narration is appended so it cannot hide an empty-bucket outcome.

Balance, statistics, cauldron contributions, and the interaction receipt are saved in one database transaction. Replaying the same Discord interaction does not settle it or announce it again. Paused games, inactive/frozen players, and invalid wagers are rejected. An announcement failure does not undo a saved payout.

For statistics, `total_candy_spent_on_pumpkins` records cumulative wager volume, not an extra fee. `total_candy_won_from_pumpkins` and `total_candy_lost_on_pumpkins` record actual net gains and losses. Existing historical statistics are not rewritten.
