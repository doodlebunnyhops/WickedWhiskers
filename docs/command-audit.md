# Command audit — 2026-10-04

Scope: `feature/potion-shop` at `d35f8a3fdba12f7c1e8ac257fb7af2ea67504b79`. The live application command objects were inspected with login/sync mocked: 36 slash leaves, five member context menus, default `!help`. Handler and database source was reviewed; these findings are not a claim of live Discord testing. This documentation change does not fix the issues below.

## Confirmed defects

| Priority | Finding and impact | Source | Suggested repair |
| --- | --- | --- | --- |
| High | `/bot remove role` calls missing `remove_role_by_guild` after announcing removal. Access remains. | `discord-bot/cogs/mod_commands/remove.py`, `db_utils.py` | Call existing `delete_role_by_guild` with its correct signature; confirm only after success. |
| High | Pumpkin entry is deducted before resolution; “break even” does not refund it, ordinary losses deduct again and can make a balance negative. | `discord-bot/utils/player.py`, `smash_pumpkin` | Agree net wager outcomes, settle once atomically, bound losses, and make narration match net changes. This is separate from intentional magical rewards. |
| Medium | `/game get leaderboard type:All` passes `all` to a query map with no such entry, raising ValueError. Evil/Sweet raw counts are also rendered as percentages. | `cogs/game_commands/get.py`, `db_utils.py:get_leaderboard_query` | Implement aggregate display or remove All; use correct units. |
| Medium | `/bot set settings` marks role/invite optional, but blank role fails validation and blank invite leaves an unbound variable. Successful submission also clears the invite message ID. | `modals/settings.py:Bot` | Use channel/role selectors; define empty-field semantics and preserve unrelated invite state. |
| Medium | Configured `trick_success_rate` is stored/displayed, but actual thief-rate calculation uses its own formula. | `cogs/game_commands/set.py`, `utils/player.py` | Define how the server rate modifies the formula, or remove the ineffective setting. |
| Medium | React-to-join does not check paused state; inactive existing players follow an insert path rather than reactivation. | `bot.py:on_raw_reaction_add`, join/add handlers, `db_utils.py` | Share one enrollment service with explicit pause/reactivation behavior. |
| Medium | `/game set player_stat` accepts negative candy/stat values. | `cogs/game_commands/set.py` | Validate supported ranges before writing. |
| Medium | Invite update without prior settings continues after responding and tries to unpack None. Settings display can fail when the saved invite message is gone/inaccessible. | `cogs/mod_commands/update.py`, `get.py` | Return or create cleanly; handle missing/inaccessible messages without failing the whole display. |
| Medium | Reset assumes a player exists; removing a channel assumes the saved channel still resolves. | `cogs/mod_commands/reset.py`, `remove.py` | Guard missing records/channels before formatting or mutating. |

## Incomplete behavior and decisions to make

- `/bot remove join_game_msg` is a registered instruction-only placeholder. Decide whether it should delete the message, clear its mapping, or both.
- `/game cast spell` is intentionally unavailable. Potions are perks, not tickets. Implement independent eligibility, distinct winners and actual payouts before enabling it.
- `/game set settings` defaults optional `game_enabled` to false. This is current behavior, but surprising: changing a rate alone pauses play. Prefer an optional “leave unchanged” state.
- `/bot get join_game_msg` has no moderator permission check. The group name does not enforce one. Decide whether public access is intended.
- `/bot get channel` with Both returns early when a setting is absent. Show each configured/missing channel independently.
- Frozen checks differ by activity: tricks and potion actions reject frozen players, while treats do not. Define the intended freeze scope before changing behavior.
- Check Bucket deliberately returns the caller’s bucket even when invoked on another member. Decide whether its label should make that clearer. Potion Shop must remain caller-owned.
- Reset is immediate and destructive without confirmation; add a confirmation view. Its existing message still mentions unavailable `/freeze` and misleading rejoin guidance.
- Other runtime text still mentions unregistered `/return` and old commands. Documentation repair does not repair those messages; audit `utils/messages.json` and embedded strings next.

## Intentional behavior preserved

Luna/Raven special scenarios may create candy, cover treat costs, copy pumpkin rewards into the pool, or grant a named Ward bottle. Do not classify candy creation alone as a transfer bug. Potion purchases do not contribute to the pool. Multiple cauldron winners means distinct players, not repeated tickets for one player. Ward/Cunning inventory and effects are separate from any future cauldron eligibility.

## Recommended order

1. Repair role removal and pumpkin accounting before relying on them in a live season.
2. Repair leaderboard/settings/invite error paths and range validation.
3. Unify enrollment and agree freeze/pause behavior; add destructive-action confirmation.
4. Replace stale runtime guidance and add an in-bot slash-command help entry (default `!help` does not document these slash commands).
5. Implement the separate cauldron draw and payout flow; consider a public leaderboard command if players should inspect rankings themselves.

The command reference now separates actual registration from incomplete behavior, documents all arguments/choices and permission boundaries, and removes ticket-shop and unregistered-command instructions. The Event/Admin settings-display mapping reported earlier was already fixed in `d35f8a3`; no database rewrite is required for that fix.
