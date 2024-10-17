# Moderator-Only Commands

<!-- TOC -->

- [Moderator-Only Commands](#moderator-only-commands)
    - [Suggestions of use:](#suggestions-of-use)
        - [Player and Candy Management](#player-and-candy-management)
        - [Server Management](#server-management)
        - [Cauldron Event Management](#cauldron-event-management)
        - [Potion Management for Cauldron Event](#potion-management-for-cauldron-event)
        - [Reset and Game Management](#reset-and-game-management)
        - [Moderator-Only Stat Commands](#moderator-only-stat-commands)

<!-- /TOC -->

## Suggestions of use:

have _fun_ messing with the players ;) 

## Status of command implementation

**Currently I've set moderator commands prefexed with `zmod` to denote them as for moderator type roles and easier split of commands between player and moderators since at this time slash commands can't be ordered in a specifed way.**

- ✅  Completed Command! (But unit testing is still  needed overall!)
- ❌  In Progress, may not work as expected
- No Icon means not started or not in a state worth using.

## Commands

### Player and Candy Management
- **/add player**
  - **Action:** Adds a new player.

- **/add player candy [amount]**
  - **Action:** Adds a specific amount of candy to a player.
  - **Example:** `/add player candy 20`

- ✅ **/reset player [player]**
  - **Action:** Resets a player to 50 candy on start as active status, this action will cause an admin message to post showing players last stats before reset.
  - **Example:** `/reset player @Player`

- **/reset player [player] [option:tricks_done|treats_given|candy_count|etc.]**
  - **Action:** Resets specific stats for a player.
  - **Example:** `/reset player @Player candy_count`

- **/remove player**
  - **Action:** Removes a player from the game.

- **/remove player candy [amount]**
  - **Action:** Removes a specific amount of candy from a player.
  - **Example:** `/remove player candy 10`

- **/view player stats**
  - **Action:** Displays a player’s stats.
  - **Example:** `/view player stats @Player`

- **/view top_players**
  - **Action:** Shows the leaderboard of players with the most candy.

- **/update player status [active|inactive|freeze|unfreeze]**
  - **Action:** Updates the player’s status.
  - **Example:** `/update player status active`

- **/update player candy [amount]**
  - **Action:** Updates the player’s candy count.
  - **Example:** `/update player candy 50`

---

### Server Management


- ✅ **/set channel type:[event|admin] [channel name]**
  - **Action:** Sets the event or admin channel where the bot will respond to player interactions in events type channel and log moderator actions in the specified admin channel.
  - **Example:** `/set channel type:event #event_channel`

- ✅ **/get channel type:[event|admin|both]**
  - **Action:** Get the name of the channel bot uses for either events or admin/mod responses.
  - **Example:** `/get channel type:event`

- ✅ **/update channel type:[event|admin]**
  - **Action:** Update the name of the channel bot uses for either events or admin/mod responses.
  - **Example:** `/update channel type:event`

- ✅ **/remove channel type:[event|admin]**
  - **Action:** Bot will default to responding in whatever channel it was interacted with for moderator and event type responses. This does not remove the channel itself, just removes it from bots list of channels to use for response types. 
  - **Example:** `/remove channel type:event`

- ✅ **/get join_game_msg**
  - **Action:** Get the link and name of channel where message to react to join game is posted.
  - **Example:** `/get join_game_msg`

- ✅ **/set join_game_msg**
  - **Action:** Creates an embeded message inviting players to join the game via react to a :jack-o-lantern:.
  - **Example:** `/set join_game_msg`

- ❌ **/update join_game_msg**
  - **Action:** As of right now to update the message doesn't mean editing it's contents, rather someone need to delete the old one in server, and making a new one by running this command.
  - **Example:** `/set join_game_msg`

- ❌ **/remove join_game_msg**
  - **Action:** This does not directly delete the message*. For now the bot will forget the invite message was created and stop listening to it for reacts.
  - **Example:** `/remove join_game_msg`

- ✅ **/get roles**
  - **Action:** Show what roles have been assigned to use this bots moderator commands
  - **Example:** `/get roles`

- ✅ **/set role [role]**
  - **Action:** Assigns a role that has access to this bots moderator commands.
  - **Example:** `/set role_access @Admin`

- ✅ **/remove role [role]**
  - **Action:** Removes the server management access from a role. It does not remove roles from the server, only from the bots DB to know which roles to allow.
  - **Example:** `/remove role @Moderator`

---

### Cauldron Event

- **/view cauldron**
  - **Action:** Displays the amount of candy in the cauldron.

- **/cast_spell [witch] [winners]**
  - **Action:** Starts the cauldron event, selecting either **Luna** (kind and fair) or **Raven** (evil and greedy) to cast the spell, with a specified number of winners.
  - **Example:** `/cast_spell Luna 2` → Luna picks 2 winners from the cauldron event.
---

### Potion Management for Cauldron Event

- **/set potion_cost [amount]**
  - **Action:** Allows moderators to set or update the cost of potions for the cauldron event.
  - **Example:** `/set potion_cost 15`

- **/view potion_stats**
  - **Action:** Displays the number of players who have purchased potions and the total number of potions bought.
  - **Example:** `/view potion_stats`

- **/dump cauldron**
  - **Action:** Empties the cauldron, resetting it to 0 candy.

---

### Game Management

- **/reset game**
  - **Action:** Wipes everything, resetting the entire game and clearing all player data.

---

### Stats Commands

- **/view stats tricks [type:action|candy count] [count by:successful|failed|total]**
  - **Action:** Displays statistics related to tricks, either by action count or candy count, and broken down by successful, failed, or total.
  - **Options:**
    - `type: action` → Displays the number of trick actions performed.
    - `type: candy count` → Displays the total candy involved in tricks.
    - `count by: successful` → Shows only successful tricks.
    - `count by: failed` → Shows only failed tricks.
    - `count by: total` → Shows the total of all trick actions.
  - **Example:** `/view stats tricks type:action count by:successful`

- **/view player count [active|inactive|frozen|total]**
  - **Action:** Displays the total number of players based on their status: active, inactive, or frozen.
  - **Options:**
    - `active` → Shows the count of active players.
    - `inactive` → Shows the count of inactive players.
    - `frozen` → Shows the count of frozen players.
    - `total` → Shows the total count of players.
  - **Example:** `/view player count active`

