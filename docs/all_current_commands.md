# Current command reference

Updated 2026-10-11 for `feature/potion-shop`. Command paths and options below are generated from the registered command definitions. This is an offline review, not a live Discord acceptance test.

Use commands in a server. `<option>` is required; `[option]` is optional. Use Discord’s choice pickers; do not type the angle brackets. `/bot`, `/game` and `/shop` groups are not executable on their own.

Game moderator means Manage Server or a role configured with `/bot add role`. Shop manager means Manage Server or the separate role configured with `/bot set shop_manager_role`. Only Manage Server can change that shop role. Players have no administrative access requirement, but gameplay eligibility still applies. Application permission checks do not guarantee command-picker visibility.

## Player commands

| Command | Options | Access | Purpose |
|---|---|---|---|
| `/bucket` | None | Player | See how much candy you have! |
| `/help` | None | Player | Open your private player guide and available moderator help. |
| `/inventory` | None | Player | View your potion bottles and active effects |
| `/join` | None | Player | Join the game! |
| `/leave` | None | Player | Leave the game, forfeiting progress with a one-hour rejoin delay. |
| `/mentions` | [enabled: boolean] | Player | Choose whether game announcements may mention you in this server. |
| `/shop browse` | None | Player | Open the potion shop modal |
| `/smash_pumpkin` | <amount: integer> | Player | Smash a pumpkin for candy! |
| `/treat` | <member: user>; <amount: integer> | Player | Treat a player with some candy! |
| `/trick` | <member: user> | Player | Trick a player into giving you candy! |
| `/use` | None | Player | Open the potion activation modal |
| `/whois` | <character: Luna, Raven> | Player | Learn about the Characters in the game! |

## Bot setup

| Command | Options | Access | Purpose |
|---|---|---|---|
| `/bot add role` | <role: role> | Game moderator | Set a role for access to restricted bot commands. |
| `/bot get channel` | <channel_type: Event, Admin, Both> | Game moderator | Get the channel where event or admin messages will be posted. |
| `/bot get join_message` | None | Game moderator | Gets the link to the message where you can join the game. |
| `/bot get roles` | None | Game moderator | Get all saved roles permitted to use restricted commands. |
| `/bot get settings` | None | Game moderator | Get the current settings for the bot. |
| `/bot post join` | <channel: channel> | Game moderator | Publish, refresh or move the pumpkin reaction join message |
| `/bot post shop` | <channel: channel> | Shop manager | Post a permanent Open Shop button |
| `/bot remove channel` | <channel_type: Event, Admin> | Game moderator | Remove the event or admin channel setting. |
| `/bot remove join_message` | None | Game moderator | Remove the saved reaction join message |
| `/bot remove role` | <role: role> | Game moderator | Remove a role from the games restricted commands |
| `/bot set channel` | <channel_type: Event, Admin>; <channel: channel> | Game moderator | Set the channel for either event or admin messages to be posted. |
| `/bot set settings` | None | Game moderator | Update the bot's settings. |
| `/bot set shop_manager_role` | [role: role] | Manage Server | Set or clear the shop-manager role |

## Game management

| Command | Options | Access | Purpose |
|---|---|---|---|
| `/game add player` | <user: user> | Game moderator | Add a player to the game. |
| `/game candy` | <player: user>; <action: Give, Take>; <amount: integer>; <include_moderator: boolean> | Game moderator | Give or take player candy without affecting gameplay or cauldron stats. |
| `/game cast spell` | <witch: Luna, Raven>; <winners: Many, One> | Game moderator | Trigger a spell on the cauldron! |
| `/game freeze` | <player: user>; [minutes: integer]; [reason: string]; [update: boolean] | Game moderator | Freeze a player and return their active potions to inventory. |
| `/game get auto_cauldron` | None | Game moderator | Inspect automatic cauldron settings and blockers |
| `/game get cauldron` | None | Game moderator | View how much is in the cauldron. |
| `/game get cauldron_eligibility` | None | Game moderator | Inspect eligibility for each cauldron outcome |
| `/game get leaderboard` | <type: Top Tricksters, Top Treaters, Top Thieves, Most Generous, Most Evil, Most Sweet, Highest Risk Takers, Candy Hoarders, Potion Collector, Biggest Spender, Master of Potions, Luna’s Favorites, Untouchable, Cauldron Contributors, Pumpkin Smashers, All> | Game moderator | View the leaderboard. |
| `/game get player` | <user: user>; <get: Stats, Hidden Values, All> | Game moderator | View a player's stats. |
| `/game get settings` | None | Game moderator | View the game settings. |
| `/game get slowmode` | None | Game moderator | View the action cooldowns for this server |
| `/game manage shop` | None | Shop manager | Manage this server's potion prices and availability |
| `/game reset bucket` | <user: user> | Game moderator | Reset one joined player’s bucket to 50 candy without clearing stats |
| `/game reset buckets` | <scope: Selected players, All joined players> | Game moderator | Reset selected or all joined players’ buckets to 50; confirmation required |
| `/game reset player` | <user: user> | Game moderator | Full player reset: clears progress, inventory, effects and freeze; confirmation required |
| `/game set auto_cauldron` | [enabled: boolean]; [trigger: Interval, Threshold, Either]; [interval_minutes: integer]; [candy_threshold: integer]; [witch: Luna, Raven, Random]; [winners: One, Many, Random]; [minimum_gap_minutes: integer] | Game moderator | Configure automatic cauldron spells; disabled by default |
| `/game set cauldron` | <amount: integer> | Game moderator | Set the amount of candy in the cauldron. |
| `/game set player_stat` | <user: user>; <stat: Candy, Successful Tricks, Failed Tricks, Treats Given>; <number: integer> | Game moderator | Set Player stat |
| `/game set settings` | None | Game moderator | Update the game settings. |
| `/game set slowmode` | [trick: integer]; [treat: integer]; [smash: integer] | Game moderator | Set separate player cooldowns in seconds; 0 disables. Omit values to view. |
| `/game set state` | <state: Enable, Disable> | Game moderator | Enable or disable the game. |
| `/game unfreeze` | <player: user> | Game moderator | Remove a moderator freeze without resetting the player. |

## Entry points and interfaces

- User context menus: **Trick Player** and **Treat Player**. The latter opens a treat-amount modal. Join Game, Check Bucket and Potion Shop context menus are removed.
- `/bot set settings`: channel selectors and additive moderator-role selector; Manage Server members also see the shop-manager role selector. Selections save immediately.
- `/game set settings`: pause/resume, slowmode, cauldron balance and automatic-casting controls. They share validation and storage with individual commands. No unused probability input is exposed.
- `/shop browse` and `/inventory`: access Witch’s Veil. `/shop protection` is removed.
- Posted shop entrance: persistent **Open Shop** and **Inventory** buttons. Inventory also includes an **Open Shop** button.
- 🎃 on the saved invitation: join through normal eligibility checks. Bots cannot join; unreacting does not leave.

## Resets and administrative candy

`/game reset bucket` sets one joined player’s candy to 50. `/game reset buckets` chooses up to 25 players or snapshots all joined players, then asks for confirmation. Only records still joined at confirmation are changed. These commands preserve stats, inventory, effects, freezes, saved earnings and participation; they do not affect gameplay counters or the cauldron.

`/game reset player` is a separate full reset with confirmation. It clears progress, inventory, effects, freeze and unclaimed earnings, restores 50 candy, and leaves the player joined. Mention preferences and cooldowns persist. There is no bulk full-player reset.

`/game candy` gives or takes a positive amount without changing gameplay counters or cauldron eligibility. Taking more than the bucket holds is rejected. `include_moderator` controls attribution in the Event announcement; bucket balance is never announced. The internal audit retains the moderator identity. See [moderator guide](moderator_commands.md).

## Automatic casting

Default off. Interval, Threshold or Either triggers; Luna/Raven/Random; One/Many/Random; five-minute default minimum gap. Settings and successful-cast timestamps survive restarts. Pauses, empty pools, missing event permissions and absent eligible players block payouts. There is no catch-up burst. Manual successful casts reset the timer. See [automatic cauldron](auto-cauldron.md) for validation, timing and failure handling.

## Responses and visibility

Completed tricks, treats and smashes have one public result; validation errors remain private. Shop, inventory, bucket and help are private. Moderator-only help topics remain hidden from players. Mention preferences are per player/server and affect public announcements without changing payouts.

Leaderboard All is private outside Admin. Known legacy limitation: individual boards can currently be public in Event, beyond the intended Candy Hoarders-only policy. Use Admin or another channel for sensitive boards. See [audit](command-audit.md).

## Removed paths

The previous `/bot candy`, `/bot reset player`, `/bot set role`, `/bot send join_game_msg`, `/bot update ...`, `/shop manage`, `/shop post`, `/shop manager_role`, and `/shop protection` paths are replaced as shown above. Restarting syncs the configured registration scope. Old development registrations in a different scope still require the existing cleanup helper; this update does not clear unrelated scopes.

See [player guide](player_commands.md), [moderator guide](moderator_commands.md), [potion catalog](potion-shop.md), [freeze and Veil rules](freeze-and-protection.md), and [passive earnings](passive-earnings.md).
