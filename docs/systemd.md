# Run WickedWhiskers as a Linux systemd service

The installer uses your existing checkout and `.env`, creates a Python virtual environment, installs pinned requirements, installs `wickedwhiskers.service`, and enables it at boot. It runs as a non-root account and restarts after a crash. It does not clone, pull, reset the game, change credentials, or migrate/delete the database.

## First setup

Use a Linux host with systemd, Python 3.10+ and Python venv/pip support. Run the installer as the account that owns and normally runs the bot. Stop your manually running bot first so only one instance uses its token/database.

From your checkout:

```bash
git pull --ff-only origin feature/potion-shop
bash scripts/install-service.sh
```

The script asks for sudo when installing the system unit. If running directly as root, specify the existing non-root account:

```bash
bash scripts/install-service.sh --user your-linux-user
```

The service uses `discord-bot/` as its working directory, `.venv/bin/python -u bot.py` as its process, and `discord-bot/candy_game.db` for the live game. Ensure that is your current database before starting. If the old database is in the repo root, the installer refuses to start a fresh game over it: stop the old bot, back up the database and any sidecar files, and move them together into `discord-bot/`. If both locations contain databases, identify which is current yourself; the service always uses the one in `discord-bot/`.

Keep your existing `.env` in `discord-bot/` or the repo root. If both exist, `discord-bot/.env` takes precedence. `settings.py` loads it with python-dotenv; the unit does not embed or print the token. Required:

```dotenv
DISCORD_API_TOKEN=your_bot_token
```

For global commands across your servers, remove `GUILD` entirely. Do not set it to blank or the string `None`. To sync only to a development server, set `GUILD` to its numeric ID. `FEEDBACK_CH` is optional; if present it must be numeric. Protect the `.env` from other accounts, e.g. `chmod 600 discord-bot/.env` if that is its location.

Paths containing spaces or special characters are currently rejected. The service user must be able to traverse the checkout, read the code and `.env`, and write the database and logs. The installer does not recursively change ownership or permissions.

## Optional arguments

```bash
bash scripts/install-service.sh --python /usr/bin/python3.12
bash scripts/install-service.sh --venv /absolute/path/to/existing/venv
bash scripts/install-service.sh --no-start
```

`--no-start` installs and enables boot startup but leaves the bot stopped now. An existing venv is reused; requirements are installed into it. Stop an already-running system service before rerunning the installer. If dependencies change, stop, pull, rerun the installer and inspect the logs.

## Common commands

```bash
sudo systemctl status wickedwhiskers
sudo journalctl -u wickedwhiskers -f
sudo systemctl restart wickedwhiskers
sudo systemctl stop wickedwhiskers
sudo systemctl start wickedwhiskers
```

For ordinary code or message edits:

```bash
sudo systemctl stop wickedwhiskers
git pull --ff-only origin feature/potion-shop
sudo systemctl start wickedwhiskers
```

Check the journal for the Discord ready/login message. A successful `systemctl start` alone does not verify the token, intents, channel permissions or command sync. Console logs go to the journal; existing application logging also writes `discord-bot/logs/infos.log` (overwritten by the bot at startup).

After five rapid failed starts, systemd stops retrying. Fix the cause, then:

```bash
sudo systemctl reset-failed wickedwhiskers
sudo systemctl start wickedwhiskers
```

## End of season or uninstall

Stop and prevent boot startup without deleting data:

```bash
sudo systemctl disable --now wickedwhiskers
```

To remove the service definition afterward:

```bash
sudo rm /etc/systemd/system/wickedwhiskers.service
sudo systemctl daemon-reload
```

The checkout, `.env`, virtual environment and seasonal database remain. Never delete a live database as part of service setup.
