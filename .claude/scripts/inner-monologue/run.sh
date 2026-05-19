#!/bin/bash
# 月光 inner-monologue cron wrapper — 加载 .env 后跑 think.py
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 加载 .env
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a
  source "$SCRIPT_DIR/.env"
  set +a
fi

# 跑独白
/usr/bin/python3 "$SCRIPT_DIR/think.py"
