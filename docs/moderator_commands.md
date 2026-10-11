# Moderator and server setup guide

Updated 2026-10-11 for `feature/potion-shop`. See the [complete command reference](all_current_commands.md) for exact options and the [audit](command-audit.md) for remaining limitations.

## Access and Discord setup

Game moderation requires **Manage Server** or a role registered with `/bot add role`. Shop management is separate: `/game manage shop` and `/bot post shop` require Manage Server or the dedicated shop-manager role. Only Manage Server can appoint that role using `/bot set shop_manager_role` (omit `role` to clear it). Moving commands does not grant additional permissions.

1. `/bot set settings` opens channel and role selectors. Alternatively set channels individually:
   - `/bot set channel channel_type:Event channel:#play`
   - `/bot set channel channel_type:Admin channel:#mod-log`
2. `/bot add role role:@Game-Moderator` adds moderator access. `/bot get roles` lists roles; `/bot remove role` revokes one.
3. `/bot get settings` verifies assignments. `/bot set channel` replaces an existing assignment; `/bot remove channel` clears one.
4. `/bot post join channel:#join` publishes or refreshes the 🎃 invitation. Choosing a different channel moves it and deletes the previous message when possible. The saved target changes to the new message; old reactions no longer enroll players. `/bot get join_message` retrieves it; `/bot remove join_message` deletes it and clears its mapping.
5. `/bot set shop_manager_role role:@Shop-Manager`, optionally, then `/game manage shop` to configure prices and availability.
6. `/bot post shop channel:#shop` posts persistent **Open Shop** and **Inventory** buttons.
7. `/game set state state:Enable` enables play.

Give the bot View Channel, Send Messages, and Embed Links in announcement channels. Join invitations need Add Reactions and Read Message History; cauldron attachments need Attach Files. Administrator is not required. The bot can delete its own invitation without Manage Messages. Members need Use Application Commands in gameplay channels.

For #join and #shop, deny @everyone Send Messages and Add Reactions, retaining View Channel and Read Message History. Allow the bot to post and seed 🎃. Players can click the existing reaction; removing it does not leave the game. Bots cannot enroll.

## Shared game settings

`/game set settings` opens a private panel for pause/resume, action slowmode, cauldron balance and automatic spells. Its controls use the same validation and saved settings as individual commands. Editing one setting does not pause play or overwrite unrelated settings. Controls expire after five minutes and recheck permissions on use. `/game get settings` shows current values. Shop configuration remains available through `/game manage shop`.

- `/game set state state:Disable|Enable` pauses/resumes normal gameplay and passive earnings. Automatic spells do not run while paused.
- `/game set slowmode trick:10 treat:5 smash:15` sets independent per-player cooldowns, default 0 (off), range 0–86400 seconds. Omitted values are preserved. `/game get slowmode` inspects them. Changing an action's value clears its timers; ordinary resets do not. Failed completed attempts count; invalid requests do not. No gameplay moderator bypass.
- `/game set cauldron amount:1000` replaces the pool balance; `/game get cauldron` inspects it.
- `/game set auto_cauldron` and `/game get auto_cauldron` configure/inspect automatic casting. See [schedule rules and examples](auto-cauldron.md).

## Player management and resets

- `/game add player user:@Player` uses shared enrollment checks.
- `/game get player user:@Player get:Stats|Hidden Values|All` privately shows stats, inventory, potion activity, pumpkin activity, passive earnings and cauldron contributions/rewards.
- `/game set player_stat user:@Player stat:<choice> number:<integer>` overwrites Candy, Successful Tricks, Failed Tricks or Treats Given. Use nonnegative values; range validation for this legacy command remains outstanding.
- `/game candy player:@Player action:Give|Take amount:100 include_moderator:False` adjusts only candy, requires a positive amount and rejects overdrafts. The Event announcement includes player and amount, optionally the moderator, never the bucket balance. It does not count toward gameplay stats or cauldron weights. Internal audit always records the actor.
- `/game freeze` and `/game unfreeze` control participation. Frozen players keep progress; remaining potion charges return to inventory. Public messages omit the moderator and reason. See [freeze rules](freeze-and-protection.md).

| Reset | Effect |
|---|---|
| `/game reset bucket user:@Player` | Set one joined player's candy to 50. |
| `/game reset buckets scope:Selected players` | Select up to 25 users, then confirm. Only still-joined records are changed. |
| `/game reset buckets scope:All joined players` | Confirm the set of joined players captured when the command opens. New joiners are not added to an open confirmation. |
| `/game reset player user:@Player` | Separate full reset, with confirmation: fresh 50-candy bucket; clears stats, bottles, effects, earnings, freeze and rejoin delay; player remains joined. |

**Bucket-only resets preserve** participation, stats, inventory, effects, freezes, saved earnings and the cauldron. They do not count as earned/lost candy or change cauldron weights. Full player resets preserve mention preferences and cooldowns. Confirmations are private, bound to the moderator/server, expire after five minutes and reject revoked permissions. There is no bulk full-player reset or registered full-season reset.

## Cauldron and reports

`/game cast spell witch:Luna|Raven winners:One|Many` awards the full pool among distinct eligible players. Frozen and Veiled players do not qualify. Purchases provide perks, not entries. Results post in Event with the witch artwork and winner mentions, respecting mention opt-outs. A manual successful cast resets the automatic timer.

`/game get cauldron_eligibility` provides a private report without drawing. `/game get leaderboard` supports the existing category boards and All selector. All is private outside Admin. **Known limitation:** the current implementation permits every individual category in Event, although the intended policy is Candy Hoarders only; use Admin or another channel for sensitive boards until that separate fix. Commands do not forward boards to a different channel.

Luna's Calling credits its summoner with one kindness action and actual distributed candy. Favor adds its bonus candy without another action. Receiving candy adds no kindness credit. Sweetness/evilness retain their formulas. Potion boards distinguish purchases, spending, activations and charges actually triggered; do not sum them as independent gameplay actions. See [potion details](potion-interactions.md).

If announcement delivery fails after a saved payout or candy adjustment, do not repeat the command to retry the message: a new interaction is a new operation. Existing idempotency receipts prevent replay of the same request.

The bot's currently requested intents and membership reconciliation are unchanged; reduced-intent and large-guild work remain deferred. Database feature tables are created at startup without resetting current players.
