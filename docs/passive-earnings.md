# Passive candy earnings

Joined, unfrozen players earn **1 candy per 10 eligible minutes**, regardless of Discord presence or Witch’s Veil. No gameplay action is needed to earn. Existing gateway intents and member-departure handling are unchanged.

- Maximum **100 candy per UTC day**; the limit resets at midnight UTC.
- Maximum **300 saved, unclaimed candy** per player per server.
- Open `/bucket` and press **Collect earned candy** to transfer the whole reserve into your bucket. Checking the bucket never collects automatically.
- While saved earnings are full, accrual stops. Capped time is discarded rather than awarded after collecting.
- Collecting frees reserve space but does not reset the daily limit.
- Unclaimed candy cannot be stolen, spent, wagered, or counted toward pumpkin wealth comparisons or Candy Hoarders. Once collected it is ordinary bucket candy.

## Eligibility and lifecycle

Offline/invisible status does not matter. Timestamps persist through restarts. A ten-minute block is accumulated from eligible time; checking or collecting preserves incomplete progress. Earnings crossing a UTC boundary are divided by eligible elapsed time on each side, with the completed block at that boundary booked to the interval ending there.

Pausing the game or freezing a player stops earning and collection, without confiscating already saved candy. Partial progress is preserved. Timed freeze expiry resumes eligibility at the saved expiry even if the bot was offline. Overlapping pauses/freezes never earn candy during blocked time.

Leaving the game or guild forfeits unclaimed earnings and partial progress. The current departure listener and reconnect reconciliation perform this on detected departures; no new intents or presence tracking are added. Moderator player reset/deletion also forfeits the reserve. Rejoining/resetting preserves daily earning totals and claim history, preventing another daily allowance. A seasonal database deletion clears these records along with everything else.

A player starting with an empty bucket can collect without first completing an action. A rejected gameplay action does not claim income. Witch’s Veil permits earning and collection. A frozen player may inspect the bucket but cannot collect until unfrozen.

## Records and integrity

`passive_earnings` stores the timestamp, partial eligible seconds, reserve, lifetime earned, collected, and forfeited totals. `passive_earning_days` stores actual candy accrued by UTC day. `passive_claims` stores player, server, interaction ID, amount, and claim timestamp. The private `/game get player` Stats/All report includes these accounting totals.

Transfers and claim receipts commit together. Replayed successful interactions cannot award again, and clicking an old button cannot duplicate an already emptied reserve. Overflow rejects the claim without losing saved candy. Passive earnings do not increment treating, kindness, theft, cauldron weights/contributions, or potion metrics.

Startup creates the tables and enrolls existing records from installation time, with no retroactive season earnings. New players start earning when they join. No periodic job is needed: accrual is calculated on inspection/claim and settled before participation changes. A pause/resume transition settles the guild’s player accounts once so offline elapsed time is classified correctly; it does not poll players continuously.

## Messages

Text and button labels use `passive_income` in `discord-bot/utils/messages.json` through `messages.py`. The private bucket displays saved earnings, today’s earned total, reset time, and pause/freeze/cap status. The collection view expires after ten minutes; reopen `/bucket` for fresh controls.
