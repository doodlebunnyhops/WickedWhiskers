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

### Player and Candy Management
- **/add player**
  - **Action:** Adds a new player.

- **/add player candy [amount]**
  - **Action:** Adds a specific amount of candy to a player.
  - **Example:** `/add player candy 20`

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

- **/set channel type:[event|admin] [channel name]**
  - **Action:** Sets the event or admin channel where the bot will respond to player interactions.
  - **Example:** `/set channel type:event #event_channel`

- **/set role_access [role]**
  - **Action:** Assigns a role that has access to server management commands.
  - **Example:** `/set role_access @Admin`

- **/remove role_access [role]**
  - **Action:** Removes the server management access from a role.
  - **Example:** `/remove role_access @Moderator`

---

### Cauldron Event Management

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

---

### Reset and Game Management

- **/reset player [player]**
  - **Action:** Resets all stats for a player.
  - **Example:** `/reset player @Player`

- **/reset player [player] [option:tricks_done|treats_given|candy_count|etc.]**
  - **Action:** Resets specific stats for a player.
  - **Example:** `/reset player @Player candy_count`

- **/reset game**
  - **Action:** Wipes everything, resetting the entire game and clearing all player data.

- **/dump cauldron**
  - **Action:** Empties the cauldron, resetting it to 0 candy.

---

### Moderator-Only Stat Commands

- **/view stats tricks [type:action|candy count] [count by:successful|failed|total]**
  - **Action:** Displays statistics related to tricks, either by action count or candy count, and broken down by successful, failed, or total.
  - **Options:**
    - `type: action` → Displays the number of trick actions performed.
    - `type: candy count` → Displays the total candy involved in tricks.
    - `count by: successful` → Shows only successful tricks.
    - `count by: failed` → Shows only failed tricks.
    - `count by: total` → Shows the total of all trick actions.
  - **Example:** `/view stats tricks type:action count by:successful`

- **/view stats treats [type:action|candy]**
  - **Action:** Displays statistics related to treats, either by the number of actions or the total amount of candy given.
  - **Options:**
    - `type: action` → Displays how many treat actions were performed.
    - `type: candy` → Displays how much candy was given in total.
  - **Example:** `/view stats treats type:candy`

- **/view player count [active|inactive|frozen]**
  - **Action:** Displays the total number of players based on their status: active, inactive, or frozen.
  - **Options:**
    - `active` → Shows the count of active players.
    - `inactive` → Shows the count of inactive players.
    - `frozen` → Shows the count of frozen players.
    - `total` → Shows the total count of players.
  - **Example:** `/view player count active`

