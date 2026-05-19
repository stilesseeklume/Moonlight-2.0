#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ENV_FILE="/Users/zhenliu/Moonlight/.claude/scripts/inner-monologue/.env"
if [ -f "$ENV_FILE" ]; then
  set -a; source "$ENV_FILE"; set +a
fi
/usr/bin/python3 "$SCRIPT_DIR/review.py"
