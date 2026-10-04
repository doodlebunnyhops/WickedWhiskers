# Moderator and server setup guide

Current for `feature/potion-shop`, reviewed 2026-10-04. The [complete command reference](all_current_commands.md) lists all 37 slash commands and exact argument choices. Read the [audit](command-audit.md) before a live season.

## Access

Game-moderator commands require **Manage Server** or a role registered with `/bot set role`. This is independent of the dedicated shop-manager role. `/shop manage` and `/shop post` require Manage Server or that shop role; `/shop manager_role` itself requires Manage Server. `/bot get join_game_msg` currently has no moderator check.

## Initial setup

1. `/bot set channel channel_type:Event channel:#game-events`
2. `/bot set channel channel_type:Admin channel:#game-admin`
3. Optionally `/bot set role role:@Game-Moderator`.
4. `/bot get settings` to verify channel/role mappings.
5. `/bot send join_game_msg channel:#join-the-game` to create the reaction invitation.
6. Optionally `/shop manager_role role:@Shop-Manager`, then `/shop manage` to set this server’s prices and sale availability.
7. `/shop post channel:#potion-shop` for the persistent entrance button.
8. `/game set state state:Enable` to enable gameplay.

Use Discord’s named option pickers; channel/role names above are examples. Ensure the bot can view/send in the selected channels and access invite-message history. Prefer the individual channel/role commands: the legacy `/bot set settings` modal mishandles blank optional fields.

## Channel and invitation maintenance

Use `/bot update channel channel_type:Event|Admin channel:<channel>` for an existing setting and `/bot remove channel channel_type:Event|Admin` to clear it. `/bot get channel` offers Event, Admin, or Both; Both has a missing-channel display limitation.

`/bot get join_game_msg` retrieves the invitation. `/bot update join_game_msg channel:<channel>` requires deletion of the old invite first; use `/bot send join_game_msg` for initial setup. `/bot remove join_game_msg` only gives manual-deletion instructions; it does not remove the message or clear saved IDs.

`/bot get roles` lists game-moderator roles. **`/bot remove role` is broken and can announce success without removing access.** Until repaired, remove the Discord role from affected members or adjust Discord command access; do not rely on its success message.

## Game controls and reports

- `/game set state state:Disable|Enable`: pause/resume gameplay. The reaction join handler currently bypasses pausing; pause is not a universal stop on every action.
- `/game get settings`: inspect settings. `/game set settings trick_success_rate:<0–100> [game_enabled:<boolean>]` stores values, but the configured rate does not drive actual trick odds. Omitting game_enabled pauses the game. Prefer the explicit state command for pause/resume.
- `/game add player user:<member>`: enroll a player. Inactive existing records need a reactivation fix.
- `/game get player user:<member> get:Stats|Hidden Values|All`: inspect a player. Hidden trick rate is the base calculation, without active Cunning.
- `/game set player_stat user:<member> stat:<choice> number:<integer>`: overwrite Candy, Successful Tricks, Failed Tricks, or Treats Given. This is an absolute value, not an increment; avoid negative values (currently unvalidated).
- `/bot reset player user:<member>`: immediately reset an existing player to 50 candy, active/unfrozen status, cleared counters, bottles and effects. There is no confirmation step and unregistered players cause an error.
- `/game get leaderboard type:<category>`: list up to ten ranked players. All opens eight category pages with a selector and Previous/Next. Only the invoking moderator can change pages; controls expire after three minutes. Rankings are a snapshot at invocation. Sweetness = candy given / (given + stolen); evilness = candy stolen / (given + stolen), both displayed as percentages and zero when neither exists.
- `/game get cauldron`: inspect the pool. `/game set cauldron amount:<nonnegative integer>` replaces its balance.
- `/game cast spell witch:Luna|Raven winners:One|Many`: select distinct active players with treating/tricking preferences, splitting the full pool among them. Potions do not affect eligibility.

There is no registered full-season reset, freeze/unfreeze, or remove-player command. Seasonal database deletion is an operational reset, not a slash command, and also clears server configuration and shop price overrides.

## Shop administration

`/shop manage` provides a potion selector and edit modal. Prices are integers from 1 to 1,000,000 candy, isolated per server. Default-price resets preserve availability. Turning off sales preserves owned bottles. Editing effect strength/duration is not exposed through this UI.

`/shop manager_role role:<role>` appoints one regular role; omit role to clear it. Manage Server retains access. Permissions are rechecked when controls are used. See [potion-shop details](potion-shop.md) for transaction and effect rules.

## Cauldron eligibility diagnostics

Use `/game get cauldron_eligibility` (game-moderator access, no arguments) for a private report of active database players, the pool balance, and candidates/weights for each Luna/Raven outcome. It makes no draw and changes no data. Up to five candidate IDs per outcome are displayed with remaining counts. Active records may include departed members, the draw shows a player-ID fallback if the member is not cached.

All active database players qualify, independent of potion purchases and pool balance. Luna normal/fumble weight = 1 + treats given; Raven normal/explosion weight = 1 + successful tricks. Luna special weight = 1 + max(0, treats given − successful tricks); Raven rage reverses that difference. Negative stats are treated as zero. Every outcome retains baseline weight 1; when nobody has a positive special-outcome difference, all players have equal chances. Normal/first special/second special probabilities remain 76.5%/15%/8.5%. One selects one player; Many chooses a random count from 2 through the number of distinct active players (or 1 when only one player or one candy is available), then draws with weights without replacement. Selected players cannot repeat. The report and draw share these formulas. The full pool is awarded atomically: equal shares, with remainder pieces assigned in draw order. Many caps its random winner count at the smaller of active-player count and available candy, so every winner receives at least one. The pool becomes zero. Discord interaction IDs prevent duplicate payouts, and cauldron_draws plus cauldron_event record each completed draw.


## Moderator candy adjustments

`/bot candy player:<member> action:Give|Take amount:<positive integer> include_moderator:True|False`

Requires Manage Server or a role registered with `/bot set role`. The include_moderator option is required each time: True names the moderator in the event announcement; False omits them. The player and amount are always shown. No bucket balance is included in announcements or confirmations.

Give creates candy for the selected player; it does not deduct from the moderator. Take removes exactly the requested amount and rejects requests exceeding the player's balance. Zero and negative amounts are rejected. The player must already have a game record in this server. Administrative corrections remain available while gameplay is paused or a player is frozen/inactive.

These changes affect only the selected player's balance. They do not increment tricks, treats, sweetness/evilness counters, or cauldron contributions, and do not change cauldron selection weights or the pool. Moderator identity is still recorded in the internal audit even when omitted from the public announcement.

Configure an event channel and grant the bot View Channel, Send Messages, and Embed Links before use. If Discord rejects the announcement after the adjustment has saved, the moderator receives a private warning; do not issue another command to retry the post, since a new command is a new adjustment. Replaying the same interaction cannot apply the adjustment twice.

All new responses use `mod_candy` in `discord-bot/utils/messages.json` through `messages.py`.
