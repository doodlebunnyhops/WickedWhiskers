# Pumpkin smashing

Use `/smash_pumpkin amount:<wager>` with a positive whole number no larger than your current bucket. You cannot lose more than your wager. There is **no separate entry fee**: each result is a net gain or loss. Unclaimed earnings do not count as bucket candy.

## Outcome chances

| Outcome | Base chance |
| --- | ---: |
| Big-win roll | 10% |
| Ordinary win | 30% |
| Break even | 20% |
| Ordinary loss | 30% |
| Big loss | 10% |

With at least **three active, unfrozen players holding positive candy**, compare the player’s bucket with the median of those balances in this server (including their own). Witch’s Veil players are included because they can smash. Zero balances, inactive records, and current freezes are excluded; expired freezes count normally.

`boost = 0.05 × max(0, 1 − bucket / median)`

Add this to ordinary-win probability and subtract it from break-even probability. Big-win and loss chances stay fixed. A player at half the median gets +2.5 percentage points; players at or above it get none. Below three qualifying players, boost is zero. Potion spending and treating can deliberately change a player’s standing. The cauldron and unclaimed income never enter this calculation.

## Variable amounts

Take `risk = wager / bucket` before settling the smash. Independently sample a uniform multiplier from the appropriate range:

| Outcome | Lower multiplier | Upper multiplier |
| --- | --- | --- |
| Big win | `1 − 0.5 × risk` | `1 + 0.5 × risk` |
| Ordinary win/loss | `0.4 − 0.2 × risk` | `0.6 + 0.2 × risk` |
| Big loss | `1` | `2` |
| Break even | `0` | `0` |

Multiply by the wager and round to the nearest whole candy, with halves rounded up and a minimum of 1 for a win/loss. Losses are capped at the wager, never taking additional candy from the bucket. The legacy big-loss multiplier is still sampled, but the cap makes its settled loss exactly the wager. Rounded endpoints are not equally likely. There is no penalty or bonus based on previous rolls.

For a 50-candy bucket:

| Wager | Ordinary win/loss | Big win | Big loss after cap |
| --- | --- | --- | --- |
| 5 | 2–3 | 5 | 5 |
| 10 | 4–6 | 9–11 | 10 |
| 25 | 8–18 | 19–31 | 25 |
| 50 | 10–40 | 25–75 | 50 |

An all-in big loss still empties the bucket. Normal and big-win ranges overlap at high risk: announcement wording uses the actual amount. Gains at least as large as the wager use the jackpot narration; smaller gains use ordinary narration. Losses at least the wager use cursed-pumpkin narration; any full drain uses the empty-bucket announcement. The saved outcome retains the actual selected category for auditing.

With the wager cap applied, before rounding and the median boost, average net change is 0% of the wager. The ordinary-win boost improves that average; this is not a guarantee for any individual run.

## Cauldron and messages

After a win, a separate 30% chance creates a copy of the actual winnings in the cauldron; the player keeps their win. After a loss, a 90% chance sends the actual lost candy to the cauldron, with no additional deduction. Break-even results do neither. Protected players have identical mechanics but neutral narration rather than witches spotting them.

Public results show wager and signed net change, without a remaining balance, except that a full drain can be announced. Completed smashes do not keep a duplicate private success reply. Narration uses `smash_pumpkin` in `messages.json` through `messages.py`.

Balance, pumpkin stats, pool contributions, and the interaction receipt settle atomically. Replaying a saved interaction cannot reroll or pay again. The receipt includes pre-roll risk, applied ordinary-win boost, comparison-player count, outcome, and actual amount. Announcement failure does not undo or repeat settlement.

The wager statistic tracks wager volume, not an entry fee; win/loss statistics track actual gains/losses. Existing historical stats are not rewritten. [Passive earnings](passive-earnings.md) provide a separate, manually collected return to play.
