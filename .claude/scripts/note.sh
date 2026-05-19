#!/bin/bash
# 用法：bash note.sh "Hugo 说下周四可以吃饭"
# 把一条现实事件写进 notes/inbox.md，下次对话月光会读到并更新 timeline

VAULT="/Users/zhenliu/Moonlight"
INBOX="$VAULT/notes/inbox.md"
NOW=$(date '+%Y-%m-%d %H:%M')

mkdir -p "$VAULT/notes"

if [ -z "$1" ]; then
    echo "用法：bash $(basename $0) \"发生了什么事\""
    exit 1
fi

echo "- [$NOW] $1" >> "$INBOX"
echo "✅ 已记录：$1"
echo "   → $INBOX"
echo "   → 下次对话月光会读到并更新 timeline"
