

## Player Commands

<!-- TOC -->

- [Player Commands](#player-commands)
- [Suggestions](#suggestions)
- [Status of command implementation](#status-of-command-implementation)
    - [Player Interactions](#player-interactions)
    - [Joining and Leaving the Game](#joining-and-leaving-the-game)
    - [Checking Stats and Candy](#checking-stats-and-candy)
    - [Smashing Pumpkins for Risk](#smashing-pumpkins-for-risk)
    - [Potion CMDs for Cauldron Event](#potion-cmds-for-cauldron-event)

<!-- /TOC -->

## Suggestions

:eyes: you may be tempted to just leave the game to pause your progress but moderators can reinstate you ;)...or freeze your game permanently and you'll lose your bought potions if the spell is cast while you are away.

## Status of command implementation

- ✅  Completed Command! (But unit testing is still  needed overall!)
- ❌  In Progress, may not work as expected
- No Icon means not started or not in a state worth using.

### 1. Player Interactions

- ✅ **/trick [target_player]**
  - **Action:** Attempts to trick another player out of their candy.
  - **Example:** `/trick @Player`
  - ✅**VARIANT** Player can right click on another member -> select app -> bot -> trick to initate a trick attempt agaisnt that member.

- ✅ **/treat [target_player] [amount]**
  - **Action:** Gives candy to another player.
  - **Example:** `/treat @Player 10`
  - ✅ **VARIANT**: Players can also join by clicking on themselves to open the context menu.

---

### 2. Joining and Leaving the Game

- ✅ **/join**
  - **Action:** Joins the game and sets the player’s status to active.
  - ✅ **VARIANT**: Players can also join by clicking on themselves to open the context menu.

- **/escape**
  - **Action:** Leaves the game but saves player data, setting the player’s status to inactive. While escaped you can still lose your potions purchased if the spell is casted - but you will not receive winnings for being inactive.

- **/return**
  - **Action:** Reinstates a player’s status to active, allowing them to participate again.

---

### 3. Checking Stats and Candy

- **/stats**
  - **Action:** Displays the player’s personal stats (like candy count, tricks, treats, etc.).

- ✅ **/bucket**
  - **Action:** Shows how much candy the player currently has.
  - ✅ **VARIANT**: Players can also join by clicking on themselves to open the context menu.

---

### 4. Smashing Pumpkins for Risk

- **/smash_pumpkin [amount]**
  - **Action:** Risks a certain amount of candy for a chance to win or lose candy.
  - **Example:** `/smash_pumpkin 10`

---

### 5. Potion CMDs for Cauldron Event

- **/buy potion [amount]**
  - **Action:** Players purchase a potion (ticket) to participate in the cauldron event. One potion costs 10 candy by default.
  - **Example:** `/buy_potion`

- **/view potions**
  - **Action:** Displays the total number of potions a player currently owns.
  - **Example:** `/view potions`
