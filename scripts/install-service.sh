#!/usr/bin/env bash
# Install from an existing checkout. Never copies or deletes the seasonal database.
set -euo pipefail

usage() {
    cat <<'USAGE'
Usage: bash scripts/install-service.sh [--user USER] [--python PYTHON] [--venv PATH] [--no-start]

Defaults: run the service as the invoking account (SUDO_USER under sudo), use
python3, and install dependencies in <repo>/.venv. Enables and starts the service.
--no-start installs and enables the service without starting it.
Run as your usual bot account; sudo is used only for systemd installation.
If running directly as root, supply --user with a non-root account owning the repo.
USAGE
}
die() { printf 'Error: %s\n' "$*" >&2; exit 1; }

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
bot_dir="$repo_dir/discord-bot"
service_user="${SUDO_USER:-$(id -un)}"
python_bin=python3
venv_dir="$repo_dir/.venv"
start_service=true
while (($#)); do
    case "$1" in
        --user|--python|--venv)
            (($# >= 2)) || die "$1 needs a value"
            case "$1" in
                --user) service_user=$2 ;;
                --python) python_bin=$2 ;;
                --venv) venv_dir=$2 ;;
            esac
            shift 2 ;;
        --no-start) start_service=false; shift ;;
        -h|--help) usage; exit 0 ;;
        *) die "Unknown option: $1 (use --help)" ;;
    esac
done
[[ $(uname -s) == Linux ]] || die 'This installer requires Linux with systemd.'
[[ -d /run/systemd/system ]] || die 'systemd must be running as the system service manager.'
command -v systemctl >/dev/null || die 'systemctl is required.'
command -v systemd-analyze >/dev/null || die 'systemd-analyze is required.'
id "$service_user" >/dev/null 2>&1 || die "Unknown account: $service_user"
[[ $(id -u "$service_user") != 0 ]] || die 'Choose a non-root bot account with --user.'
service_group=$(id -gn "$service_user")
if ((EUID != 0)); then
    [[ $service_user == "$(id -un)" ]] || die 'Use sudo when installing for a different account.'
    command -v sudo >/dev/null || die 'sudo is required to install the system service.'
else
    command -v runuser >/dev/null || die 'runuser is required when installing as root.'
fi
[[ $service_user =~ ^[a-zA-Z0-9_.-]+$ && $service_group =~ ^[a-zA-Z0-9_.-]+$ ]] || die 'Unsupported account/group name.'
[[ $venv_dir == /* ]] || venv_dir="$PWD/$venv_dir"
# Keep template substitution unambiguous for systemd directives and ExecStart.
for path in "$repo_dir" "$venv_dir"; do
    [[ $path =~ ^/[a-zA-Z0-9_./-]+$ ]] || die 'Checkout and venv paths must not contain spaces or special characters.'
done
python_bin=$(command -v "$python_bin") || die 'Python was not found. Use --python /path/to/python3.'
[[ -f "$bot_dir/bot.py" && -f "$repo_dir/requirements.txt" ]] || die 'Run from a complete WickedWhiskers checkout.'
if systemctl is-active --quiet wickedwhiskers.service; then
    die 'Stop the existing service before reinstalling: sudo systemctl stop wickedwhiskers'
fi
if [[ -f "$repo_dir/candy_game.db" && ! -f "$bot_dir/candy_game.db" ]]; then
    die 'Found candy_game.db in the repo root. Stop the old bot and move the existing database (and any SQLite sidecar files) into discord-bot/ before installing; no data was moved.'
fi
if [[ -f "$bot_dir/.env" ]]; then
    env_file="$bot_dir/.env"
elif [[ -f "$repo_dir/.env" ]]; then
    env_file="$repo_dir/.env"
else
    die 'Keep your existing .env in discord-bot/ or the repo root. It must contain DISCORD_API_TOKEN.'
fi
as_user() {
    if ((EUID == 0)); then runuser -u "$service_user" -- "$@"; else "$@"; fi
}
as_root() {
    if ((EUID == 0)); then "$@"; else sudo -- "$@"; fi
}
as_user test -r "$env_file" || die 'The service account cannot read the .env file.'
as_user test -w "$bot_dir" || die 'The service account needs write access to discord-bot/ for SQLite and logs.'
if [[ -f "$bot_dir/candy_game.db" ]]; then
    as_user test -w "$bot_dir/candy_game.db" || die 'The service account cannot write the existing database.'
fi
as_user "$python_bin" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' || die 'Use Python 3.10 or newer.'
if [[ ! -x "$venv_dir/bin/python" ]]; then
    as_user "$python_bin" -m venv "$venv_dir" || die 'Could not create venv. Install your distribution’s Python venv package and check directory ownership.'
fi
as_user "$venv_dir/bin/python" -m pip install -r "$repo_dir/requirements.txt"
# Validate configuration without importing settings (which creates logs) or exposing the token.
as_user "$venv_dir/bin/python" - "$env_file" <<'PY'
import sys
from dotenv import dotenv_values
config = dotenv_values(sys.argv[1])
if not (config.get('DISCORD_API_TOKEN') or '').strip():
    sys.exit('DISCORD_API_TOKEN is missing or empty in .env.')
for name in ('GUILD', 'FEEDBACK_CH'):
    if name in config and (not config[name] or not config[name].isdigit()):
        sys.exit(f'{name} must be a numeric ID when present. Remove GUILD entirely for global commands.')
PY
as_user mkdir -p "$bot_dir/logs"
as_user test -w "$bot_dir/logs" || die 'The service account cannot write to discord-bot/logs.'
if [[ -f "$bot_dir/logs/infos.log" ]]; then
    as_user test -w "$bot_dir/logs/infos.log" || die 'The service account cannot write the existing infos.log.'
fi
unit_tmp=$(mktemp -d)
trap 'rm -rf -- "$unit_tmp"' EXIT
"$python_bin" - "$repo_dir/deploy/systemd/wickedwhiskers.service" "$unit_tmp/wickedwhiskers.service" "$service_user" "$service_group" "$bot_dir" "$venv_dir/bin/python" <<'PY'
from pathlib import Path
import sys
source, target, user, group, bot, python = sys.argv[1:]
unit = Path(source).read_text()
for key, value in {'SERVICE_USER':user, 'SERVICE_GROUP':group, 'BOT_DIRECTORY':bot, 'PYTHON':python}.items():
    unit = unit.replace('@' + key + '@', value)
Path(target).write_text(unit)
PY
systemd-analyze verify "$unit_tmp/wickedwhiskers.service"
as_root install -m 0644 "$unit_tmp/wickedwhiskers.service" /etc/systemd/system/wickedwhiskers.service
as_root systemctl daemon-reload
as_root systemctl enable wickedwhiskers.service
if [[ $start_service == true ]]; then
    as_root systemctl start wickedwhiskers.service
    as_root systemctl --no-pager --full status wickedwhiskers.service
else
    printf 'Installed and enabled. Start when ready: sudo systemctl start wickedwhiskers\n'
fi
printf 'Follow logs: sudo journalctl -u wickedwhiskers -f\n'
printf 'Database location: %s/candy_game.db\n' "$bot_dir"
printf 'A started service is not proof of Discord login; check the journal for the ready message.\n'
