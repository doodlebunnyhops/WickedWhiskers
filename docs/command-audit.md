# Current implementation limitations

Reviewed 2026-10-11 against `feature/potion-shop`. This replaces the old October 4 audit: cauldron payouts, freeze controls, shared enrollment, slash help, and the All leaderboard now exist. Source review is not a live Discord acceptance test.

| Finding | Current impact / workaround |
| --- | --- |
| Leaderboard privacy differs from the agreed policy | Every individual category can be public in Event, although only Candy Hoarders was requested. All is private outside Admin. Invoke sensitive boards in Admin or another channel until fixed. |
| `/game set player_stat` accepts negative values | Supply only valid nonnegative values. Prefer `/game candy` for Give/Take adjustments; it validates amounts and keeps gameplay counters unchanged. |
| Legacy channel display paths remain | Both-channel display can stop at a missing channel, and channel removal assumes a resolvable saved channel. Invitation posting/removal is now implemented. |
| Membership and scale work is deferred | The bot currently requests all intents and resets departing players, with reconnect membership reconciliation. On-demand verification, preserving departed data, and large-guild optimization are not implemented. |

Candy creation in magical scenarios is intentional. Potion purchases are perks, not pool contributions or tickets. Many cauldron winners are distinct players. Ward/Mirror protection and frozen/Veil exclusions have their own rules; see the [potion](potion-interactions.md) and [participation](freeze-and-protection.md) guides.

Completed trick/treat/smash actions now publish one public result; private validation errors remain. Announcement failure after a saved transaction is reported privately and is not a reason to repeat the gameplay action.

The command reorganization fixes role revocation, replaces legacy settings forms, restricts join-message inspection to moderators, and adds confirmed full resets and separate bucket-only resets. See [automatic cauldron](auto-cauldron.md) for scheduling and delivery limits.
