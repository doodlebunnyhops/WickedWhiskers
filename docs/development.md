# Development and hosting

Use Python 3.10+ and install the repository’s pinned requirements (discord.py 2.7.1 and python-dotenv 1.1.1). SQLite support is included in Python; do not install `sqlite3` with pip.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Place `.env` in the repo root or `discord-bot/` (the latter takes precedence):

```dotenv
DISCORD_API_TOKEN=your_bot_token
# Optional development server only:
# GUILD=123456789012345678
# Optional numeric feedback channel:
# FEEDBACK_CH=123456789012345678
```

Keep credentials out of version control. Omit `GUILD` entirely for global synchronization across installations; blank or `None` strings are invalid. A numeric GUILD selects development-guild synchronization. Startup syncs the command tree. Old guild registrations may coexist with global registrations when switching modes; removing GUILD alone does not delete those remote registrations.

Run from the bot directory so database and log paths remain consistent:

```sh
cd discord-bot
mkdir -p logs
../.venv/bin/python bot.py
```

For a managed Linux service, use the [service installer guide](systemd.md). Run only one instance against the same token/database.

## Installation and access

Install to a server with the `bot` and `applications.commands` scopes. Gameplay is designed for servers, not direct messages. Channel permissions: View Channel, Send Messages, Embed Links; join invitations additionally need Add Reactions and Read Message History; cauldron attachments need Attach Files. Members need Use Application Commands. Administrator is unnecessary. See [moderator setup](moderator_commands.md).

The current code uses `discord.Intents.all()`, including privileged Members, Presence, and Message Content. Deployment must authorize the intents the code requests. Context menus do not inherently require Presence, and sending embeds does not require Message Content. The current member-departure listener and full member reconciliation rely on member access. The planned reduced-intent implementation is deferred; this documentation update does not change it.

## Data and updates

`candy_game.db` is relative to the process working directory. Startup initializes the schema, including potion, participation, audit, and seasonal metric tables. No manual migration is needed for the current feature tables and existing records are retained. Newly introduced counters are not backfilled from old receipts.

Back up the stopped bot’s database before updating. Deleting it resets all guilds in that database, including server settings, shop prices, players, freezes, and audit history. An admin player reset and a player leaving have different scopes; see [participation rules](freeze-and-protection.md). WAL/index tuning and a database worker are deferred, not installed by this guide.

## Tests and live checks

From the repository root:

```sh
.venv/bin/python -m pip install pytest
.venv/bin/python -m pytest -q
```

The tests use isolated databases and mocked Discord operations. Verify real modal rendering, channel permissions, event delivery, winner mentions, private-response cleanup, and persistent buttons in a test server before a season. Command synchronization can succeed even when channel permissions prevent posting.

Player-facing narration is primarily in `discord-bot/utils/messages.json`, loaded by `utils/messages.py`; see [message guide](gameplay-messages.md). Restart after changes. Image URLs are centralized as described in the [artwork guide](artwork.md).

The passive-income update creates earnings, UTC daily accounting, and claim tables at startup. Existing players begin accruing from installation, without backfill. No Discord intent changes or periodic earning job are required. Review [earnings lifecycle](passive-earnings.md) and [pumpkin formulas](pumpkin-smashing.md) when upgrading.
