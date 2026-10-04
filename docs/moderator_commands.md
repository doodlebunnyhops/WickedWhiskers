# Moderator and server setup guide

Current for `feature/potion-shop`, reviewed 2026-10-04. The [complete command reference](all_current_commands.md) lists all 36 slash commands and exact argument choices. Read the [audit](command-audit.md) before a live season.

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
- `/game get leaderboard type:<category>`: list up to ten ranked players. The All option is broken; Evil/Sweet formatting incorrectly treats raw scores as percentages.
- `/game get cauldron`: inspect the pool. `/game set cauldron amount:<nonnegative integer>` replaces its balance.
- `/game cast spell witch:Luna|Raven winners:One|Many`: restored original selection and announcement, without payouts. Luna still uses legacy potion-purchase counts; new perk purchases do not update those counts.

There is no registered full-season reset, freeze/unfreeze, or remove-player command. Seasonal database deletion is an operational reset, not a slash command, and also clears server configuration and shop price overrides.

## Shop administration

`/shop manage` provides a potion selector and edit modal. Prices are integers from 1 to 1,000,000 candy, isolated per server. Default-price resets preserve availability. Turning off sales preserves owned bottles. Editing effect strength/duration is not exposed through this UI.

`/shop manager_role role:<role>` appoints one regular role; omit role to clear it. Manage Server retains access. Permissions are rechecked when controls are used. See [potion-shop details](potion-shop.md) for transaction and effect rules.
