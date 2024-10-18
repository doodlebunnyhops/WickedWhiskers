# All Active Commands

*Note they may not work perfectly, still in testing, please report bugs :hear:

<!-- TOC -->

- [All Active Commands](#all-active-commands)
  - [Moderator Commands](#moderator-commands)
  - [Player Commands](#player-commands)
- [Context Menu Commands](#context-menu-commands)

<!-- /TOC -->


### Moderator Commands

```bash
/bot : Moderator Commands
├── set : Set commands
│   ├── role : Set a role for access to restricted bot commands.
│   │   Arguments:
│   │   └── role : The role to set (Type: role)
│   ├── channel : Set the channel for either event or admin messages to be posted.
│   │   Arguments:
│   │   ├── channel_type : The type of channel to set (event or admin) (Type: string)
│   │   └── channel : The channel where the message type will be posted (Type: channel)
│   └── settings : Update the bot's settings.
├── get : get commands
│   ├── roles : Get all saved roles permitted to use restricted commands.
│   ├── join_game_msg : Gets the link to the message where you can join the game.
│   ├── channel : Get the channel where event or admin messages will be posted.
│   │   Arguments:
│   │   └── channel_type : The type of channel to get (event, admin, or both) (Type: string)
│   └── settings : Get the current settings for the bot.
├── remove : Remove commands
│   ├── join_game_msg : I cant remove messages :P
│   │   Arguments:
│   │   └── channel : The channel where the invite message will be ignored. (Type: channel)
│   ├── role : Remove a role from the games restricted commands
│   │   Arguments:
│   │   └── role : The role to be removed (Type: role)
│   └── channel : Remove the event or admin channel setting.
│       Arguments:
│       └── channel_type : The Channel Type to stop posting messages to. (Type: string)
├── update : Update commands
│   ├── join_game_msg : Update where react to join message will be posted.
│   │   Arguments:
│   │   └── channel : Channel where the invite message will be posted (Type: channel)
│   └── channel : Update the channel where event or admin messages will be posted.
│       Arguments:
│       ├── channel_type : The type of channel to update (event or admin) (Type: string)
│       └── channel : The channel to update the event or admin channel bot messages to. (Type: channel)
├── reset : Reset commands
│   └── player : Factory Reset a player
│       Arguments:
│       └── user : The player to be reset (Type: user)
└── send : Send commands
│   └── join_game_msg : Posts a message for players to join by reacting with a 🎃.
│       Arguments:
│       └── channel : Channel where the invite message will be posted (Type: channel)

/game : Game options and commands
├── set : Set commands
│   ├── settings : Update the game settings.
│   │   Arguments:
│   │   ├── potion_price : … (Type: integer)
│   │   ├── trick_success_rate : … (Type: number)
│   │   └── game_enabled : … (Type: boolean)
│   ├── cauldron : Set the amount of candy in the cauldron.
│   │   Arguments:
│   │   └── amount : … (Type: integer)
│   ├── player_stat : Set Player stat
│   │   Arguments:
│   │   ├── user : The player you want to modify (Type: user)
│   │   ├── stat : The stat you want to change (e.g., candy_in_bucket) (Type: string)
│   │   └── number : The value you want to set for the stat (Type: integer)
│   └── state : Enable or disable the game.
│       Arguments:
│       └── state : Enable or disable the game. (Type: string)
├── add : Add commands
│   └── player : Add a player to the game.
│       Arguments:
│       └── user : The player to be added (Type: user)
├── get : get commands
│   ├── settings : View the game settings.
│   ├── cauldron : View how much is in the cauldron.
│   └── player : View a player's stats.
│       Arguments:
│       ├── user : The user whose stats you want to view (Type: user)
│       └── get : The details you want to view (stats, hidden values, or both) (Type: string)
└── cast : Cast commands
    └── spell : Trigger a spell on the cauldron!
        Arguments:
        ├── witch : The witch to cast the spell (Type: string)
        └── winners : The number of winners (Type: string)
```


### Player Commands

```Bash
/trick : Trick a player into giving you candy!
    Arguments:
    └── member : The Member to trick (Type: string)
/treat : Treat a player with some candy!
    Arguments:
    ├── member : The player to treat with candy (Type: user)
    └── amount : The amount of candy to give (Type: integer)

/join : Join the game!

/whois : Learn about the Characters in the game!
    └── character : … (Type: string)
/whois : Learn about the Characters in the game!

/bucket : See how much candy you have!

/buy : Buy items from the shop
└── potion : Buy Potion for a chance to win a prize from the cauldron!
    Arguments:
    └── amount : … (Type: integer)

/shop : Buy items from the shop
    └── prices : View the prices of items in the shop

```
---
## Context Menu Commands

These are player specific commands

_Use by clicking on a server member -> select apps -> and these commands will show_

```bash
- Trick Player
- Treat Player
- Join Game
- Check Bucket
- Potion Shop 
```