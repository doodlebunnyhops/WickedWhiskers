# Outstanding and deferred work

Current behavior is documented in the [command reference](docs/all_current_commands.md). See the [current audit](docs/command-audit.md) for verified limitations; this list is not a list of available commands.

## Outstanding corrections

- Restrict public individual leaderboards outside Admin to Candy Hoarders.
- Repair moderator role removal and legacy settings/invitation/channel error paths.
- Validate stat-setting ranges and add confirmation to destructive player reset.
- Resolve the ineffective stored trick-success setting without silently changing game probabilities.

## Deferred by discussion

- Large-guild optimization: membership checks, event delivery, database indexing/journal settings, and workload testing.
- Preserve departed members’ game data and verify membership on targeting/reward; keep freezes intact. Current code still resets on departure.
- Reduce gateway intents after membership handling is redesigned.
- Per-server customizable success/failure probabilities.
- A redesigned rich game/server settings interface; the current legacy settings modal remains limited.

## Implemented

Potion shop and per-server pricing; seven bottled potions and timed Witch’s Veil; inventory buttons; cauldron eligibility and distinct payouts; balanced pumpkin outcomes; moderator candy adjustments; freeze/unfreeze and confirmed leaving; role-aware help; expanded stats/boards; centralized artwork; public gameplay message cleanup.

Historical concepts in [idea.md](docs/idea.md) are brainstorming, not registered commands or committed features.
