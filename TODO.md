# Outstanding and deferred work

Current behavior is documented in the [command reference](docs/all_current_commands.md). See the [current audit](docs/command-audit.md) for verified limitations; this list is not a list of available commands.

## Outstanding corrections

- Restrict public individual leaderboards outside Admin to Candy Hoarders.
- Improve legacy channel display/removal handling when saved channels no longer exist.
- Validate stat-setting ranges. Full player reset now requires confirmation.

## Deferred by discussion

- Large-guild optimization: membership checks, event delivery, database indexing/journal settings, and workload testing.
- Preserve departed members’ game data and verify membership on targeting/reward; keep freezes intact. Current code still resets on departure.
- Reduce gateway intents after membership handling is redesigned.
- Per-server customizable success/failure probabilities.

## Implemented

Shared bot/game settings interfaces; organized command groups; confirmed full-player resets and independent bucket-only resets; persistent automatic cauldron casting with interval/threshold triggers; repaired role revocation and join-message posting/removal.

Potion shop and per-server pricing; seven bottled potions and timed Witch’s Veil; inventory buttons; cauldron eligibility and distinct payouts; balanced pumpkin outcomes; moderator candy adjustments; freeze/unfreeze and confirmed leaving; role-aware help; expanded stats/boards; centralized artwork; public gameplay message cleanup.

Historical concepts in [idea.md](docs/idea.md) are brainstorming, not registered commands or committed features.
