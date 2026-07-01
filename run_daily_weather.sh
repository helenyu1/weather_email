#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"

if [[ -f "$SCRIPT_DIR/.env" ]]; then
  set -a
  source "$SCRIPT_DIR/.env"
  set +a
fi

exec /usr/bin/python3 "$SCRIPT_DIR/daily_shanghai_weather.py"
