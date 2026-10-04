# WickedWhiskers

Potion shop implementation: see [setup, commands, effects, and testing](docs/potion-shop.md).

There are a lot of commands that haven't been implemented yet! If you're looking to contribute there's plenty to do here :D and then enjoy the discord bot game! 

Hacktoberfest 2024 is ON!

## What is WickedWhiskers

This is a discord bot that enabls players in your server to interact in a halloween themed game.  `/trick` members out of their candy or `/treat` them with some?

Buy named potions for gameplay perks: block a trick, boost your next tricks, or summon Luna to share candy. Purchases do not fund the cauldron or grant entries. `/game cast spell` selects distinct active players, favoring treating for Luna and successful tricks for Raven and awards them the full pool. See [cauldron limitations](docs/potion-shop.md#cauldron-and-other-limits).

Pumpkin smashing is registered as `/smash_pumpkin amount:<number>`, but its accounting still needs repair before a live season. See the [command audit](docs/command-audit.md).


## Commands

- [Moderator](docs/moderator_commands.md): Setup, permissions, game controls, and shop management.
- [Player](/docs/player_commands.md)
- [All current commands](docs/all_current_commands.md): 37 slash commands, five member-menu actions, arguments, and limitations.
- [Command audit](docs/command-audit.md): Confirmed bugs, incomplete behavior, and suggested repairs.


## Development

So glad you want to help! Refer to these docs on setup for dev.
   - [Development requirements and setup](/docs/development.md)
   - [Contributing Guidlines](CONTRIBUTION.md)

## Attribution

This project was created by **doodlebunnyhops**.

If you plan to reuse, modify, or distribute any part of this code, please follow these guidelines:

1. **Include a reference to this repository**: [Repository URL]
2. **Clearly attribute the author**: doodlebunnyhops
3. **Suggested formats**:
   - "Based on the original work by doodlebunnyhops (https://github.com/doodlebunnyhops)"
   - "Original creator: doodlebunnyhops"

For more detailed attribution guidelines, see the `ATTRIBUTION.md` file.

## Linux service

Use the [systemd setup guide](docs/systemd.md) to install the bot as a boot-started service with crash recovery and journal logs. From this checkout, run `bash scripts/install-service.sh` as your normal bot account.
