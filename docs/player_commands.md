# Player commands

Current for `feature/potion-shop`, reviewed 2026-10-04. See the [complete reference](all_current_commands.md) for exact arguments and [known limitations](command-audit.md).

## Playing

1. Use `/join` to enter with 50 candy, or react 🎃 to the server’s game invitation.
2. Use `/bucket` to check your candy and unactivated potion count.
3. Use `/trick member:<player>` to attempt a theft, or `/treat member:<player> amount:<number>` to give candy. Both players must be active and must be different people. Special Luna/Raven scenarios can change rewards and costs.
4. Use `/whois character:Luna` or `character:Raven` for character information.

`/smash_pumpkin amount:<number>` is available, but its balance calculations still need repair. Do not assume “break even” means a zero net cost; see the audit before using it in a live season.

There are no registered `/escape`, `/return`, `/stats`, or `/view potions` commands. Leaderboards currently require a game moderator through `/game get leaderboard`.

## Potion shop and modals

Use `/shop browse`, a posted **Open Shop** button, or the **Potion Shop** member context menu. Select a potion and quantity (1–100) in the private modal, submit, then review the price, effect and resulting balance before **Confirm Purchase**. Cancel does not spend candy. If a price changes, the revised order needs confirmation.

Purchases always use your own candy and inventory—even when you opened the shop by selecting another member. Buying a bottle does not activate it. Use `/inventory` to view bottles and active effects, then **Use Potion**, or open `/use` directly to select and activate a bottle.

| Potion | Default candy price | Effect |
| --- | --- | --- |
| Witch’s Ward | 5 | Block the next incoming player trick. |
| Raven’s Cunning | 5 | Add 15 percentage points to the next 3 eligible initial trick rolls, capped at 95% without lowering a higher base rate. |
| Luna’s Calling | 10 | Give 5 candy each to up to 3 distinct other eligible members. Shared 60-second server cooldown. |

Your server may change prices or disable sales. Disabled sales do not invalidate bottles already owned. Ward and Cunning can coexist; activating an already-active copy is rejected without consuming the spare bottle. Effects survive restart and have no time expiry. A Ward-blocked attempt or an empty unprotected bucket does not spend a Cunning charge.

Luna excludes the summoner, bots, departed, frozen and inactive players. No recipients, failed member verification, or an active cooldown preserves the bottle. Purchase/use is blocked while paused or for frozen/inactive players. `/inventory` remains a read-only way to inspect your state.

Potions grant perks; purchases do not fund the cauldron or enter a prize draw. All active players qualify for the moderator cauldron draw. Luna favors treating and Raven favors successful tricks. Winners are distinct; the command currently announces names without paying out candy.

## Member menus

Right-click/long-press a member → **Apps**. **Trick Player** targets that member; **Treat Player** opens an amount modal for them. **Join Game** must target yourself. **Check Bucket** and **Potion Shop** always use your own account.
