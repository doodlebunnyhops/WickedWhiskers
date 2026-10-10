# Freezes, Witch's Veil, and leaving the game

All settings and player state are isolated by server. Times are stored in the database and checked at action time, so restarting the bot does not extend protection or remove freezes/cooldowns. Existing player data is retained when the new tables are created; no seasonal reset is required to install this feature.

## Moderator freeze

- `/game freeze player:@Player minutes:60 reason:...` freezes for 60 minutes. Omit minutes for an indefinite freeze.
- Add `update:True` to explicitly replace an existing freeze's duration and reason. Repeating a freeze never returns the same potion twice.
- `/game unfreeze player:@Player` removes the freeze without resetting progress or bypassing a leave/rejoin delay.
- Manage Server or a role configured with `/bot set role` is required. A shop-manager role alone is insufficient.

Frozen players cannot trick, treat, smash pumpkins, shop, activate potions, be targeted, receive witch gifts, or win cauldron draws. They can read help, inventory, and their bucket. Candy and stats are preserved.

Active charged potions return to inventory with only their remaining charges. Returned partial bottles are listed individually and used before fresh bottles. A potion that already acted immediately, such as Luna's Calling, is not returned.

Active Witch's Veil ends on freezing. Its potion is returned as a bottle credit covering one future potion fee, and its unused time allowance is refunded, for either purchase mode. The current started minute remains spent. A new time allowance must be purchased to reuse the returned bottle. The agreed personal cooldown starts when the freeze ends the protection.

The event channel receives a randomized witch announcement identifying only the frozen player and status. It never contains the moderator, reason, duration, bucket, or returned items. Freeze reasons and moderator identity remain in the internal audit. Blocked player actions privately show the reason, full expiry timestamp, relative time, and restrictions. Indefinite freezes say they last until a moderator unfreezes the player. Reaction-join failures are delivered by DM because reaction events cannot receive ephemeral replies; if DMs are disabled, use `/join` for private feedback.

Freezes survive leaving/rejoining the game or server. `/bot reset player` is an explicit administrative fresh start: it clears the freeze and rejoin delay, restores 50 candy, and clears inventory/effects/stats. Existing potion cooldowns remain.

## Witch's Veil

Open `/shop protection`, choose Witch's Veil in `/shop browse`, or use its button in `/inventory`. Protection activates immediately on confirmed purchase. Ordinary potions retain their normal buy-then-use workflow.

| Default | Value |
| --- | --- |
| Potion fee | 50 candy |
| Time price | 5 candy per minute |
| Minimum duration | 5 minutes |
| Maximum duration | 30 minutes |
| Personal cooldown | 60 minutes after protection ends |

Two modes are available:

- **Exact duration:** enter minutes. Pay the fee and all time upfront. Ending early consumes the potion and forfeits unused time.
- **Candy budget:** enter candy to reserve for time, excluding the potion fee. It must be a multiple of the per-minute price and fund an allowed duration. The reserve is deducted upfront, so pumpkin losses and other purchases cannot spend it. Each started minute costs a full minute. Ending early consumes the potion and refunds only the unspent time reserve.

Both modes show the complete quote before confirmation. No stacking, extension, automatic renewal, or extra withdrawals are allowed. Unused charged effects wait without losing charges. Timers continue while offline. Early ending requires confirmation and starts the full personal cooldown; another activation requires another purchase. A rejected or repeated checkout cannot charge twice.

While protected:

- No outgoing or incoming tricks or treats, other potion activation, Luna's Calling gifts, or cauldron winnings.
- Shopping, inventory, bucket, and pumpkin smashing remain available.
- Pumpkin odds, gains, losses, and magical contributions to the cauldron are unchanged. Special narration attributes the contribution to the pumpkin/cauldron rather than witches seeing the player; protected pumpkin posts do not use a witch narrator/image.
- Existing Ward, Mirror, Cunning, and other effects do not trigger or lose charges.

Under `/shop manage`, **Witch's Veil settings** lets Manage Server members or the designated shop-manager role configure the fee, rate, minimum/maximum minutes, cooldown, purchase modes, and sale availability. Values must be positive integers; minimum cannot exceed maximum. Active spells retain the agreed rate, duration, refund policy, and cooldown. Changing settings invalidates an unpaid quote, requiring the player to review it again. Returned bottle credits still cover the next potion fee, but time funding uses the current shop settings.

## Leaving and rejoining

`/leave` requires explicit confirmation. It clears all current candy, stats, inventory, active effects, returned bottles, and protection reserves without refund. It does not remove any freeze, erase existing cooldowns, reclaim prior contributions from the shared cauldron, or erase the audit history.

Leaving the Discord server applies the same reset and one-hour rejoin delay. The bot reconciles missing active members when it reconnects after downtime; for departures missed while offline, the delay begins when the departure is detected. Member verification must succeed before that reconciliation changes records.

`/join`, the join reaction, and moderator `/game add player` all enforce freezes and the one-hour rejoin delay. Once eligible, joining grants a fresh 50 candy exactly once. Joining an existing active record cannot grant another starting balance. Removing the 🎃 reaction never leaves the game.

## Messages and help

All new player-facing text is under `participation` in `discord-bot/utils/messages.json`, using the existing `messages.py` loader. Protected pumpkin variants use `smash_pumpkin.*.hidden_*`. `/help` documents the new player actions, potion, freeze controls, and event exclusions while retaining moderator-only topics.

## Passive earnings

Freezes stop earning and collection without confiscating the saved reserve. Eligible partial-minute progress survives; earning resumes at timed expiry. Veil does not stop either earning or collection. Leaving the game/guild or a moderator reset forfeits saved earnings and partial progress; daily totals and claim history remain to prevent allowance resets. Paused game time does not earn. See [passive earnings](passive-earnings.md).
