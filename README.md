# WickedWhiskers
a discord bot that plays trick-or-treat

Current state of code is not functional! I'm working on a revamp of decorators and stewing on a balanced version to use ram/cpu with sqlite and classes.

## Commands

---

### Player Commands:

#### Player Interactions and Games

- **give_treat {user} {amount}**: Give candy to another player.
- **trick {user}**: Attempt to steal candy from another player by tricks!
- **risk_treats**: Gamble some of your candy.
- **buy_potion {amount}**: Buy potions for 10 candy pieces each.
  - when a moderator casts a spell, one or many players will win the candy in the cauldron.

#### Candy Management

- **stats**: Check a player's candy and stats.
  - optional {user} you can keep this blank or put in your username. You cannot check other player stats. 
- **candy_stash**: Check how much candy you have.
  
#### Game Participation

- **join**: Join the candy game and start collecting candy.
- **escape**: Opt out of the active game. Your progress will be saved for when you /return.
  - You will not receive any mentions while you've escaped.
  - You won't be able to participate in tricks, give treats, or the cauldron event, nor will other players be able to interact with you.
- **return**: Rejoin the game and resume your progress.

#### General Information

- **help**: Get a list of available commands and how to use them.
- **about**: Learn more about me!

---

### Moderator Commands (Restricted):

#### Player Management

- **give_ghoul_candy {user} {amount}**: Add candy to a player's stash. 
- **remove_ghoul_candy {user} {amount}**: Remove candy from a player's stash.
- **reset_ghoul {user}**: Reset a player's candy and stats to 0 and 50 candy pieces.
- **delete_ghoul {user}**: Delete a player from the game.
  - This will require the player to `/join` or join react 🎃 to come back in.
- **freeze {user}**: Freeze a player, making them inactive in the game.
  - This means the player won't be able to participate in tricks, give treats, or the cauldron event, nor will other players be able to interact with them. 
  - The player cannot rejoin. A game moderator must unfreeze them.
- **unfreeze {user}**: Unfreeze a player, allowing them to participate in the game again.
- **stats {user}**: Check a player's candy and stats.
- **ghoul_count**: Check the total number of players and total of active players.


#### Game Management

- **cauldron**: Check how much candy is in the lottery cauldron.
- **cast_spell {mode} {spirit} {num_players}**: Cast a spell to find the winner of the cauldron.
  - All Arguments are optional.
  - Mode:
    - 'Single': Only one winner will be chosen.
    - 'Many': DEFAULT Many winners will be chosen.
      - if  num_players is not set, it will default to Single Mode.
  - spirit
    - 'Fair': DEFAULT Takes into account tickets purchased to give those players a higher probability of winning.
    - 'Evil': If players bought a ticket...too bad everyone has the same chance now!
  - 'num_players':
    - DEFAULT = 1 
    - If Many Mode is selected, a set number of players can win, and winnings will be evenly distributed to these players.
- **top_ghouls**: See the top players with the most candy.

---

#### Server Management

- **set_role_access {role}**: Set moderator command access for a role.
  - This will allow users in this role permission to use restricted commands.
  - Someone with Manage Server privileges will have to initiate this first!
- **game_invite**: Creates a message inviting players to join the game by reacting with a 🎃.
  - The message will be posted in the channel the command was run
  - It's recommended that a channel be set up that allows only those who will run this command and the bot to post to it. This way, there is no clutter for users to react to and join.
- **set_crypt {channel}**: Set the channel where event messages will be posted.
  - Suggested to be the channel where players will interact with the bot.
- **set_lair {channel}**: Set the channel where role-based/admin commands will post.
  - Suggested as a private channel for moderators. This is where the bot logs specific actions like deleting a ghoul will be posted.
- **spooky_channels**: Show the event, admin, and game_invite channels set for the server.

## Attribution

This project was created by **doodlebunnyhops**.

If you plan to reuse, modify, or distribute any part of this code, please follow these guidelines:

1. **Include a reference to this repository**: [Repository URL]
2. **Clearly attribute the author**: doodlebunnyhops
3. **Suggested formats**:
   - "Based on the original work by doodlebunnyhops (https://github.com/doodlebunnyhops)"
   - "Original creator: doodlebunnyhops"

For more detailed attribution guidelines, see the `ATTRIBUTION.md` file.
