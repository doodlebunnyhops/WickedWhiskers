# Potion shop

Current for `feature/potion-shop`, reviewed 2026-10-06. Uses pinned discord.py 2.7.1. Startup creates feature tables without requiring a seasonal reset.

## Commands and modals

- `/shop browse`: private catalog modal, potion selector and quantity (1–100).
- Submitting produces a private checkout with the complete effect, cost and resulting balance.
- Confirm Purchase charges the caller and grants bottles. Cancel does not charge.
- `/inventory`: quantities and active charges; Use Potion opens an activation modal.
- `/use`: directly opens the activation modal.
- `/shop manage`: select a potion, then edit price and sale availability in a modal.
- `/shop manager_role`: Manage Server members can set or clear a regular shop-manager role.
- `/shop post`: posts persistent Open Shop and Inventory buttons, re-registered at startup.
- The existing right-click Potion Shop opens the caller's shop, ignoring the clicked member.

Discord slash-command groups cannot also act as a standalone root command. Use `/shop browse` or the Open Shop button, rather than `/shop` alone.

## Catalog

| ID | Potion | Default price | Effect |
| --- | --- | --- | --- |
| ward | Witch's Ward | 5 | Block the next incoming player trick, consuming one charge. |
| cunning | Raven's Cunning | 5 | Add 15 percentage points to the next 3 eligible initial trick rolls; cap the boosted rate at 95% without lowering a higher base rate. |
| luna | Luna's Calling | 10 | Give 5 candy each to up to 3 distinct other eligible server members; shared 60-second server cooldown. |
| mirror | Mirror Brew | 10 | Redirect one incoming attempt; a successful self-hit feeds the cauldron. |
| sticky | Sticky Fingers | 8 | Double candy on the next 3 ordinary successful thefts, capped by the target’s candy. |
| second_chance | Second Chance | 8 | Reroll one failed initial trick roll at the same effective chance. |
| favor | Luna’s Favor | 5 | Add half an ordinary treat, rounded down, up to 5 extra candy. |
| veil | Witch’s Veil | 50 + 5/minute | Immediate timed protection; 5–30 minutes, then a 60-minute personal cooldown. |

See [potion interactions](potion-interactions.md) for targeting, stacking, rounding, and charge rules. Prices above are defaults; check your server’s checkout.

Bottled purchases do not activate effects, fund the cauldron, or provide entries. Bottled effects persist across restarts without time expiry; duplicate active effects are rejected without consuming inventory. Spare bottles can be held.

Witch’s Veil is the timed exception: it activates on confirmed purchase. `/shop protection` offers exact-duration or candy-budget checkout and early cancellation. Budget cancellation refunds unspent reserved time; fixed-duration cancellation forfeits it. Both consume the purchase and start the agreed cooldown. Freezing has separate return/refund rules. See [complete Veil rules](freeze-and-protection.md).

## Interactions

Validation precedes protection; Ward blocks and Mirror redirects before the success roll. Ward and Mirror cannot coexist. A Ward blocks the entire trick, including empty-bucket scenarios, and records a separate blocked-trick statistic. It does not consume the attacker's Cunning charge. An empty, unprotected bucket runs its existing scenarios without consuming Cunning. Ordinary success and recovery/special branches remain unchanged in probability.

Ward does not block gifts, Luna rewards, pumpkin losses or cauldron events. Cunning affects only the initial trick success roll. Frozen/inactive players and paused games cannot purchase or activate potions; frozen players cannot be trick participants.

Luna excludes the summoner, bots, departed members, inactive players, frozen players, and players under Witch’s Veil. Failed member verification, no recipients, or an active cooldown preserves the bottle. Fewer recipients still receive 5 each. Generated candy does not trigger another treat event. A successful summon credits the summoner with one kindness action and the actual candy distributed in generosity/potion statistics; recipients receive no kindness credit. Duplicate use requests do not award candy twice.

Existing Luna cauldron-fill gifts now grant **one Witch's Ward bottle to both players**. This is the explicitly documented first-release choice for formerly unnamed gifts.

## Server management

Prices and availability are isolated per server. Manage Server or a designated shop-manager role can edit them; gameplay moderator roles do not automatically receive this access. Only Manage Server can appoint the shop-manager role. Permissions are checked again when controls are used.

Prices must be integer candy amounts from 1 to 1,000,000. Default-price resets preserve sale availability. Turning off sales does not invalidate owned bottles. If the price changes during checkout, the buyer must confirm the revised order. Configuration changes are audited. Bottled effects are fixed. Witch’s Veil settings also expose fee, time rate, allowed durations, cooldown, and purchase modes.

## Persistence and accounting

`potion_inventory`, `potion_effects`, `potion_prices`, `potion_managers`, `potion_cooldowns`, `potion_actions`, `potion_audit`, and `potion_stats` hold the new data. Purchase and use IDs make repeated processing idempotent. Synchronous transactions contain no Discord/network awaits. Candy, bottle counts, effect charges, and history commit or roll back together.

Trick resolution now commits effects, transfers and statistics before Discord announcements. Treat resolution (including the right-click modal) groups its writes too. A failed announcement cannot undo a saved reward or consume an additional bottle; a historical transaction record remains for investigation. Automatic announcement retries are not implemented.

Legacy `potions_purchased` and `potion_price` columns remain for compatibility with older data helpers, but are not used as inventory or shop pricing. Player-data displays derive bottle counts from the new inventory. All seven bottled potions use the same shop and inventory; Veil has its own timed checkout. The old generic shop command is replaced. Old generic price controls direct managers to `/shop manage`.

Deleting the seasonal database clears all state, including server overrides. The existing programmatic `reset_game(guild_id)` clears player potion state, histories, cooldowns and the pool while retaining server shop configuration. Player reset/deletion clears that player's potion state.

## Relevant bug fixes

- Right-click purchases cannot debit the selected member.
- Reclaim-one trick deducts the net theft from the target and records net stolen candy.
- Recovery theft is bounded by the target's balance.
- Shared failed-trick pool contributions match actual deductions; unequal-loss narration uses actual amounts.
- Ordinary failed tricks record loss against the thief.
- Candy rain handles tuple player rows and numeric increments correctly.
- Paused bucket response is awaited.
- Game settings use the actual shared database; pausing a new guild creates its settings row.
- The game-enabled setting now maps correctly to game-disabled storage.

## Cauldron and other limits

`/game cast spell witch:Luna|Raven winners:One|Many` now uses active-player eligibility and distinct weighted selection. It awards the full pool and posts a witch-image embed to the configured Event channel. See the formulas below.

## Verification

Install pinned requirements plus pytest, then run `python -m pytest -q` from the repository root. Use a test Discord server to check modal appearance, permissions, event posting, winner mentions, private-response cleanup, and persistent buttons after restart. Offline tests do not establish live Discord delivery.

See [current limitations](command-audit.md) and [deferred work](../TODO.md).

## Cauldron eligibility diagnostics

Use `/game get cauldron_eligibility` (game-moderator access, no arguments) for a private report of active database players, the pool balance, and candidates/weights for each Luna/Raven outcome. It makes no draw and changes no data. Up to five candidate IDs per outcome are displayed with remaining counts. Active records may include departed members, the draw uses saved winner IDs for mentions.

Active database players qualify unless frozen or under Witch’s Veil, independent of potion purchases and pool balance. Luna normal/fumble weight = 1 + treats given; Raven normal/explosion weight = 1 + successful tricks. Luna special weight = 1 + max(0, treats given − successful tricks); Raven rage reverses that difference. Negative stats are treated as zero. Every outcome retains baseline weight 1; when nobody has a positive special-outcome difference, all players have equal chances. Normal/first special/second special probabilities remain 76.5%/15%/8.5%. One selects one player; Many chooses a random count from 2 through the number of distinct eligible players (or 1 when only one player or one candy is available), then draws with weights without replacement. Selected players cannot repeat. The report and draw share these formulas. The full pool is awarded atomically: equal shares, with remainder pieces assigned in draw order. Many caps its random winner count at the smaller of eligible-player count and available candy, so every winner receives at least one. The pool becomes zero. Discord interaction IDs prevent duplicate payouts, and cauldron_draws plus cauldron_event record each completed draw.

