# Current implementation limitations

Reviewed 2026-10-06 against `feature/potion-shop`. This replaces the old October 4 audit: cauldron payouts, freeze controls, shared enrollment, slash help, and the All leaderboard now exist. Source review is not a live Discord acceptance test.

| Finding | Current impact / workaround |
| --- | --- |
| Leaderboard privacy differs from the agreed policy | Every individual category can be public in Event, although only Candy Hoarders was requested. All is private outside Admin. Invoke sensitive boards in Admin or another channel until fixed. |
| `/bot remove role` calls a nonexistent `remove_role_by_guild` helper | It can announce success without revoking access. Remove the Discord role from members; do not trust this command’s confirmation. |
| `/bot set settings` has broken optional fields | Empty role fails validation; empty invite can reference an uninitialized variable; successful submission clears the invite message ID. Use individual channel/role commands. |
| Stored trick-success setting is ineffective | Actual odds use the player formula. `/game set settings` also pauses play if optional `game_enabled` is omitted. Use `/game set state` for pause/resume. |
| `/game set player_stat` accepts negative values | Supply only valid nonnegative values. Prefer `/bot candy` for Give/Take adjustments; it validates amounts and keeps gameplay counters unchanged. |
| Legacy invitation/channel error paths remain | Invite removal is instruction-only; update assumes prior settings. Both-channel display can stop at a missing channel, and removal assumes a resolvable saved channel. Use initial setup commands for a new server. |
| Player reset is immediate | No confirmation step; requires an existing player. Reset clears progress and restrictions as documented. |
| `/bot get join_game_msg` has no moderator check | It is publicly callable despite the `/bot` grouping. |
| Membership and scale work is deferred | The bot currently requests all intents and resets departing players, with reconnect membership reconciliation. On-demand verification, preserving departed data, and large-guild optimization are not implemented. |

Candy creation in magical scenarios is intentional. Potion purchases are perks, not pool contributions or tickets. Many cauldron winners are distinct players. Ward/Mirror protection and frozen/Veil exclusions have their own rules; see the [potion](potion-interactions.md) and [participation](freeze-and-protection.md) guides.

Completed trick/treat/smash actions now publish one public result; private validation errors remain. Announcement failure after a saved transaction is reported privately and is not a reason to repeat the gameplay action.
