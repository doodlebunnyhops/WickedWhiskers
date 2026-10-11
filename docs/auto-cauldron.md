# Automatic cauldron spells

Automatic casting is **off by default** and configured independently per server. Existing manual `/game cast spell` behavior and eligibility are shared by automatic draws: active, unfrozen database players (including Veiled players); the existing weighted selection and full-pool payout; distinct winners and mention preferences; witch artwork and themed event announcements. Membership verification changes remain deferred.

## Configuration

Use `/game set auto_cauldron`, or open **Automatic cauldron** from `/game set settings`. Both call the same settings service. The interface stages dropdown choices until **Save settings** opens the numeric modal; **Turn on / off** applies to the saved configuration. Settings controls are private and recheck the owner, server and current moderator access.

| Option | Meaning |
|---|---|
| `enabled` | Explicit on/off switch. Omitted preserves the current value; default off. |
| `trigger` | Interval, Threshold, or Either. Default Interval. |
| `interval_minutes` | Positive whole minutes; required to enable Interval or Either. |
| `candy_threshold` | Positive whole candy; required to enable Threshold or Either. |
| `witch` | Luna, Raven, Random. Default Random, equal chance each cast. |
| `winners` | One, Many, Random. Default Random, equal chance of One or Many; Many then uses existing winner-count rules. |
| `minimum_gap_minutes` | Positive whole minutes between successful casts before an automatic draw; default 5. |

Omitted settings remain unchanged. Numeric settings accept 1–2147483647. Turning automation off preserves its configuration. Enabling requires an accessible configured Event channel with View Channel, Send Messages, Embed Links and Attach Files. Configure that with `/bot set channel`.

Examples:

```
/game set auto_cauldron enabled:True trigger:Interval interval_minutes:120
/game set auto_cauldron enabled:True trigger:Threshold candy_threshold:10000 witch:Random winners:Many
/game set auto_cauldron enabled:True trigger:Either interval_minutes:120 candy_threshold:10000
/game set auto_cauldron enabled:False
/game get auto_cauldron
```

Discord offers display names for choices; use the option pickers.

## Timing and safeguards

- A single background loop checks enabled servers approximately every 30 seconds. Network delays may extend this.
- Enabling starts a fresh interval. Every successful manual or automatic payout resets the interval and minimum-gap clock.
- A threshold already met may trigger at the next poll, subject to the minimum gap.
- Pause, empty pools, no eligible players, and missing channel permissions prevent automatic payouts. They do not switch automation off. Empty/ineligible draws preserve the pool and retry later.
- Persistent timestamps survive restarts. After downtime or a pause there is at most one overdue draw, with no catch-up burst.
- A transaction rechecks due status, selects winners, writes payouts, empties the pool, records the receipt and updates the clock together. Concurrent workers or a manual cast cannot award the same pool twice.
- Discord posting follows the committed payout. If sending fails, candy stays awarded, the error is logged, and that draw is not automatically retried. No duplicate awards to compensate for a missing announcement.
- `/game get auto_cauldron` shows the saved choices, next interval timestamp and current blockers. Threshold timing depends on the pool and cannot predict an exact time.

Startup creates the `auto_cauldron` table and enabled-server index automatically. No manual migration or player reset is required. Existing cauldron receipts and event history remain in use.
