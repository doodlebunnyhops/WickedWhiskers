# Player guide

Run `/help` for a private guide. In a server using #join, #play, and #shop, react to 🎃 in #join, play in #play, and use the shop buttons in #shop. Channel names are server choices; commands can be used wherever permitted.

| Command | What it does |
| --- | --- |
| `/join` | Start with 50 candy. The bot also accepts 🎃 on the configured join message. |
| `/trick member:@Player` | Attempt to steal candy; witches and potions can change the result. |
| `/treat member:@Player amount:5` | Offer candy to another player; special magical outcomes can alter the cost or gift. |
| `/smash_pumpkin amount:5` | Wager candy. There is no separate entry fee, and losses can empty your bucket. |
| `/bucket` | Privately check candy, bottles, and saved earnings; use Collect earned candy to transfer your reserve. |
| `/shop browse` | Select a potion and quantity, then review and confirm your private checkout. |
| `/inventory` | Privately see bottles, returned partial bottles, and active effects; open Use Potion or protection controls. |
| `/use` | Open the potion activation modal. |
| `/shop protection` | Buy Witch’s Veil, check its timer, or confirm ending it early. |
| `/whois character:Luna` | Meet Luna or Raven. |
| `/leave` | Confirm forfeiting progress and begin a one-hour rejoin delay. |
| `/help` | Open the private topic menu. |

Completed tricks, treats, and pumpkin smashes publish their result without a duplicate private success message. Errors and eligibility failures stay private. Potion effects appear alongside the public result; repeated references to a player use their name after their first mention. Public results do not reveal remaining bucket balances, except they may say a bucket was emptied. See [pumpkin odds](pumpkin-smashing.md).

## Potions

[The catalog](potion-shop.md#catalog) lists all seven bottled potions and Witch’s Veil with default prices. Your server can charge different prices or stop selling an item.

Buy ordinary bottles, then activate them with `/use` or Inventory. Buying alone does not enable an effect. Spare bottles can be held; duplicate active effects cannot stack. Effects persist through restarts and usually last until their charges trigger. Ward and Mirror cannot coexist. Offensive effects can combine; see [exact interactions](potion-interactions.md).

Luna’s Calling immediately gives 5 candy each to up to three other eligible members. Its 60-second cooldown is shared across the server. A cooldown rejection, failed membership verification, or no eligible recipients does not consume your bottle. A successful summon credits you with one kindness action and the candy actually gifted.

Witch’s Veil activates on confirmed purchase. While hidden, you cannot trick, treat, use other potions, receive witch gifts, or win cauldron draws. You can buy potions, inspect your inventory/bucket, and smash pumpkins. Pumpkin losses can still feed the cauldron. [Time pricing and refund rules](freeze-and-protection.md#witchs-veil) differ between exact-duration and candy-budget purchases.

## Leaving and freezes

Removing the 🎃 reaction does not leave the game. `/leave` clears your candy, stats, inventory, and effects after confirmation. Rejoining is a fresh start after one hour. The current bot also resets progress on a server departure, including departures detected after reconnecting.

A moderator freeze preserves your progress and returns remaining active potion charges to inventory, but prevents gameplay, purchases, targeting, and witch rewards. You can still inspect help, inventory, and your bucket. Blocked actions privately explain the reason and expiry. Leaving or rejoining does not remove a freeze. See [full participation rules](freeze-and-protection.md).

## Other ways to play

Right-click or long-press a member, then choose Apps for Join Game, Trick Player, Treat Player, Check Bucket, or Potion Shop. Bucket and shop always belong to you, regardless of whose menu you opened. Join Game must target yourself. The persistent shop message has both Open Shop and Inventory buttons.

## Earn candy over time

Joined, unfrozen players earn 1 candy per 10 minutes, even offline or under Witch’s Veil. Maximum 100 per UTC day and 300 saved. Collect from `/bucket`; unclaimed candy stays protected and cannot be wagered. Full reserves stop earning without backdated catch-up. Pauses/freezes stop earning and collection. Leaving or a moderator reset forfeits saved earnings. See [full rules](passive-earnings.md).
