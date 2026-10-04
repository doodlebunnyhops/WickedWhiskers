# In-Discord help

Run `/help` in a server. The reply is private and opens on Playing. Use the topic menu to replace the current page rather than receiving a long command dump.

Everyone sees:

- **Playing:** joining, tricks, treats, shopping, inventory, bucket, and pumpkin smashing.
- **Potions:** buying versus activating, each potion's effect, and important interactions.

Members with **Manage Server** or a game-moderator role registered through `/bot set role` also see:

- **Server setup:** event/admin channels, join invitation, automatic pumpkin reaction, shop entrance, recommended channel permissions, role access, and enabling play.
- **Management:** viewing and setting stats, giving/taking candy, leaderboard, shop management permissions, and pausing/resuming.
- **Cauldron events:** checking eligibility and pool, replacing the pool amount, and casting with a witch and One/Many winners.

A shop-manager role alone does not expose game-moderator help. The guide documents that shop permissions are separate. Help does not require joining the game or enabling gameplay, so moderators can use it during setup. Opening it changes no game state.

Only the requester can operate the menu. Moderator access is rechecked when selecting a restricted topic. Menus expire after ten minutes; run `/help` again to reopen.

All page text, topic labels, descriptions, footer, and interaction replies are defined under `help` in `discord-bot/utils/messages.json` and read using `messages.py`. The command is loaded before synchronization for both global and configured-guild operation.

The bot seeds 🎃 (`:jack_o_lantern:`) on new or relocated join invitations. Running `/bot send join_game_msg` again restores it on the existing invitation. Give the bot Add Reactions and Read Message History even when @everyone cannot add new reactions. Reactions from bots, including the bot's own seed reaction, never enroll them.
