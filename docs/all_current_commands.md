# Current command reference

Reviewed 2026-10-06 against `feature/potion-shop`. The tables describe implemented behavior, including known limitations. This is a source/registration review, not a live Discord acceptance test.

`<argument>` is required; `[argument]` is optional. In Discord, choose the named argument and its offered value; do not type angle brackets. Group names such as `/bot`, `/game`, and `/shop` alone are not executable commands. Use these commands in a server.

## Permissions

- **Player/public:** no administrative permission requirement. Gameplay can still require an active player, enabled game, sufficient candy, and eligible targets.
- **Game moderator:** Discord **Manage Server** (`manage_guild`) OR a role configured with `/bot set role`.
- **Shop manager:** Manage Server OR the dedicated role configured with `/shop manager_role`. A game-moderator role does not automatically grant shop-management access.
- **Manage Server:** required to appoint/clear the shop-manager role.

The access column describes application checks, not guaranteed visibility in Discord’s command picker. Server command permissions and channel access can further restrict use. `/bot get join_game_msg` is an exception to the otherwise restricted `/bot` commands.

## Player and shop commands

| Command | Access | Current behavior |
| --- | --- | --- |
| `/help` | Player/public | Private topic guide; moderator topics appear only for game moderators. |
| `/leave` | Player/public | Confirmation before forfeiting progress; one-hour rejoin delay; freezes persist. |
| `/shop protection` | Player/public | Buy timed Witch’s Veil, inspect its timer, or confirm ending it early. |
| `/join` | Player/public | Join with 50 candy; enforce pause, freeze, and one-hour rejoin delay. |
| `/trick <member>` | Player/public | Attempt to take candy from another active player; special events and active potion effects can change the outcome. |
| `/treat <member> <amount>` | Player/public | Give candy to another active player; special events may alter the cost/reward. |
| `/whois <character>` | Player/public | Show Luna or Raven character information. |
| `/bucket` | Player/public | Show your candy and total unactivated potion bottles. |
| `/smash_pumpkin <amount>` | Player/public | Wager candy on a pumpkin; no entry fee, losses capped at your bucket. See [pumpkin rules](pumpkin-smashing.md). |
| `/shop browse` | Player/public | Open your private potion-selection and quantity modal, then review and confirm checkout. |
| `/shop manage` | Shop manager | Show this server’s catalog; use controls and a modal to change prices or sale availability. |
| `/shop manager_role [role]` | Manage Server | Set the dedicated shop-manager role. Omit role to clear it. |
| `/shop post <channel>` | Shop manager | Post persistent Open Shop and Inventory buttons in a text channel. |
| `/inventory` | Player/public | Show your bottles and active effects; includes an activation control. |
| `/use` | Player/public | Open your potion-activation modal. |

## Bot configuration

| Command | Access | Current behavior |
| --- | --- | --- |
| `/bot set role <role>` | Game moderator | Grant a role access to game-moderator commands. |
| `/bot set channel <channel_type> <channel>` | Game moderator | Configure an Event or Admin text channel; use update for an existing live channel. |
| `/bot set settings` | Game moderator | Open legacy channel/role name-entry modal. Optional fields are broken; prefer individual commands. |
| `/bot get roles` | Game moderator | List roles granted game-moderator access. |
| `/bot get join_game_msg` | Player/public | Show the configured invite message. No game-moderator permission check is applied. |
| `/bot get channel <channel_type>` | Game moderator | Show configured Event/Admin channel. Both can return early when either is missing. |
| `/bot get settings` | Game moderator | Show channels, invite and access roles. Event/Admin mapping was fixed in d35f8a3. |
| `/bot remove join_game_msg <channel>` | Game moderator | Placeholder: tells you to delete the message manually. Does not delete it or clear its database mapping. |
| `/bot remove role <role>` | Game moderator | Broken: calls a nonexistent database helper; confirmation does not mean access was removed. |
| `/bot remove channel <channel_type>` | Game moderator | Clear the Event or Admin channel setting. A deleted channel can cause a lookup error. |
| `/bot update join_game_msg <channel>` | Game moderator | Post a replacement invite after the old message is deleted. Fails when no prior settings exist. |
| `/bot update channel <channel_type> <channel>` | Game moderator | Replace an existing Event or Admin channel setting. |
| `/bot reset player <user>` | Game moderator | Immediately reset an existing player to 50 candy, active/unfrozen, cleared counters, potion inventory and effects. No confirmation. |
| `/bot send join_game_msg <channel>` | Game moderator | Create and store a react-to-join invitation; refuses to duplicate an existing accessible invite. |

## Game administration

| Command | Access | Current behavior |
| --- | --- | --- |
| `/game set settings <trick_success_rate> [game_enabled]` | Game moderator | Store rate (0–100) and enabled state. Omitted game_enabled defaults to false and pauses the game. Stored rate is not used by the actual trick calculation. |
| `/game set cauldron <amount>` | Game moderator | Replace the cauldron balance with this nonnegative amount; does not add to it. |
| `/game set player_stat <user> <stat> <number>` | Game moderator | Set an active player’s chosen stat to an absolute value. Negative values are currently accepted. |
| `/game set state <state>` | Game moderator | Enable or pause gameplay. Joining also respects the pause. |
| `/game add player <user>` | Game moderator | Enroll/reactivate a player through the shared join checks, including freeze and rejoin delay. |
| `/game get settings` | Game moderator | Show pause state and stored trick rate; directs pricing changes to /shop manage. |
| `/game get cauldron` | Game moderator | Show the shared cauldron balance. |
| `/game get player <user> <get>` | Game moderator | Show player stats, hidden values, or both. Hidden trick rate excludes active Cunning bonus. |
| `/game get leaderboard <type>` | Game moderator | Show up to 10 results per category. All provides category navigation, private outside the admin channel. Single boards are visible in event/admin channels and private elsewhere. |
| `/game cast spell <witch> <winners>` | Game moderator | Award the full pool to One or Many distinct eligible players; post witch embed and winner mentions in Event. |
| `/game get cauldron_eligibility` | Game moderator | Private, read-only eligibility and weight report. |
| `/game freeze <player> [minutes] [reason] [update]` | Game moderator | Freeze indefinitely or for 1–525600 minutes; return remaining active potion charges. `update` defaults false. |
| `/game unfreeze <player>` | Game moderator | Remove freeze while preserving progress and any rejoin delay. |
| `/bot candy <player> <action> <amount> <include_moderator>` | Game moderator | Give or Take positive candy; required boolean controls moderator attribution in Event. See below. |

## Arguments and choices

Argument names below are exactly those registered with Discord. Text channels are required by channel arguments; role arguments use the role picker, user/member arguments the user picker.

| Command | Arguments |
| --- | --- |
| `/bot set role` | `role`: role |
| `/bot set channel` | `channel_type`: Event, Admin; `channel`: channel |
| `/bot get channel` | `channel_type`: Event, Admin, Both |
| `/bot remove join_game_msg` | `channel`: channel |
| `/bot remove role` | `role`: role |
| `/bot remove channel` | `channel_type`: Event, Admin |
| `/bot update join_game_msg` | `channel`: channel |
| `/bot update channel` | `channel_type`: Event, Admin; `channel`: channel |
| `/bot reset player` | `user`: user |
| `/bot send join_game_msg` | `channel`: channel |
| `/game cast spell` | `witch`: Luna, Raven; `winners`: One, Many |
| `/game freeze` | `player`: member; `minutes`: integer (optional); `reason`: text (optional); `update`: boolean (optional) |
| `/game unfreeze` | `player`: member |
| `/bot candy` | `player`: member; `action`: Give, Take; `amount`: positive integer; `include_moderator`: boolean |
| `/game set settings` | `trick_success_rate`: number; `game_enabled`: boolean (optional) |
| `/game set cauldron` | `amount`: integer |
| `/game set player_stat` | `user`: user; `stat`: Candy, Successful Tricks, Failed Tricks, Treats Given; `number`: integer |
| `/game set state` | `state`: Enable, Disable |
| `/game add player` | `user`: user |
| `/game get player` | `user`: user; `get`: Stats, Hidden Values, All |
| `/game get leaderboard` | `type`: Top Tricksters, Top Treaters, Top Thieves, Most Generous, Most Evil, Most Sweet, Highest Risk Takers, Candy Hoarders, Potion Collector, Biggest Spender, Master of Potions, Luna’s Favorites, Untouchable, Cauldron Contributors, Pumpkin Smashers, All |
| `/trick` | `member`: user |
| `/treat` | `member`: user; `amount`: integer |
| `/whois` | `character`: Luna, Raven |
| `/smash_pumpkin` | `amount`: integer |
| `/shop manager_role` | `role`: role (optional) |
| `/shop post` | `channel`: channel |

## User context menus and other entry points

Right-click/long-press a server member, then open **Apps**:

| Action | Behavior |
| --- | --- |
| Join Game | Join yourself; selecting someone else is rejected. |
| Trick Player | Trick the selected member. |
| Treat Player | Open an amount-entry modal targeting the selected member. |
| Check Bucket | Show your own bucket, regardless of the selected member. |
| Potion Shop | Open your own shop, regardless of the selected member. Purchases debit only you. |

The posted **Open Shop** and **Inventory** buttons open private views and survive bot restarts. Reacting with 🎃 to the configured invite enrolls a player through the shared join checks. Removing the reaction does not leave; bots cannot join. Default discord.py `!help` is registered, but is a prefix-command helper, not this slash-command reference; delivery also depends on message-content access.

## Old documentation that no longer applies

`/buy potion`, `/shop prices`, `/escape`, `/return`, `/stats`, `/view potions`, `/freeze`, `/reset game`, `/dump cauldron`, `/cast_spell`, `/remove player`, `/update player status`, `/view player count`, and `/add player candy` are **not registered** in this branch. Some messages/helpers still mention old commands. A Python helper is not automatically a Discord command.

The current cast path is `/game cast spell witch:Luna|Raven winners:One|Many`. Use `/game freeze` and `/game unfreeze`, not standalone `/freeze`. Prices use `/shop manage`; Witch’s Veil uses `/shop protection`. `/game set player_stat` does not expose Potions Purchased.

See [player guide](player_commands.md), [moderator guide](moderator_commands.md), [command audit](command-audit.md), and [potion design and behavior](potion-shop.md).


## Moderator candy adjustments

`/bot candy player:<member> action:Give|Take amount:<positive integer> include_moderator:True|False`

Requires Manage Server or a role registered with `/bot set role`. The include_moderator option is required each time: True names the moderator in the event announcement; False omits them. The player and amount are always shown. No bucket balance is included in announcements or confirmations.

Give creates candy for the selected player; it does not deduct from the moderator. Take removes exactly the requested amount and rejects requests exceeding the player's balance. Zero and negative amounts are rejected. The player must already have a game record in this server. Administrative corrections remain available while gameplay is paused or a player is frozen/inactive.

These changes affect only the selected player's balance. They do not increment tricks, treats, sweetness/evilness counters, or cauldron contributions, and do not change cauldron selection weights or the pool. Moderator identity is still recorded in the internal audit even when omitted from the public announcement.

Configure an event channel and grant the bot View Channel, Send Messages, and Embed Links before use. If Discord rejects the announcement after the adjustment has saved, the moderator receives a private warning; do not issue another command to retry the post, since a new command is a new adjustment. Replaying the same interaction cannot apply the adjustment twice.

All new responses use `mod_candy` in `discord-bot/utils/messages.json` through `messages.py`.

## Public results and privacy

Completed tricks, treats, and pumpkin smashes post one public result; their temporary private acknowledgement is removed after delivery. Validation failures remain private. See [message behavior](gameplay-messages.md). Bucket, inventory, help, and checkout stay private.

Leaderboard privacy currently differs from the requested policy: **every individual board**, not just Candy Hoarders, can be public in the Event channel. All stays private outside Admin. See [outstanding issues](command-audit.md).
