#!/bin/bash
# 月光 launchd 全量安装 — 跑一次装所有定时任务

set -e

VAULT="/Users/zhenliu/Moonlight"
LAUNCHD="$VAULT/.claude/launchd"
AGENTS="$HOME/Library/LaunchAgents"
LOGS="$VAULT/.claude/logs"

echo "📁 建目录..."
mkdir -p "$LOGS" "$AGENTS"

install_plist() {
    local label="$1"
    local file="$LAUNCHD/${label}.plist"
    if [ ! -f "$file" ]; then
        echo "⚠ $label: plist 不存在，跳过"
        return
    fi
    echo "📋 安装 $label..."
    cp "$file" "$AGENTS/"
    launchctl list | grep -q "$label" && \
        launchctl unload "$AGENTS/${label}.plist" 2>/dev/null || true
    launchctl load "$AGENTS/${label}.plist"
}

install_plist "com.moonlight.think"      # 内心独白           每 3 小时
install_plist "com.moonlight.morning"    # 早晨简报           每 6 小时
install_plist "com.moonlight.diary"      # 日记自动补写       每 6 小时
install_plist "com.moonlight.weekly"     # 周日时间线回顾     每 12 小时

echo ""
echo "✅ 全部安装完成"
echo ""
echo "已注册的 moonlight jobs："
launchctl list | grep moonlight
echo ""
echo "手动测试各脚本："
echo "  内心独白：bash $VAULT/.claude/scripts/inner-monologue/run.sh"
echo "  早晨简报：bash $VAULT/.claude/scripts/brief/run.sh"
echo "  日记补写：bash $VAULT/.claude/scripts/diary/run.sh"
echo "  周日回顾：bash $VAULT/.claude/scripts/weekly/run.sh"
echo "  context brief（随时）：python3 $VAULT/.claude/scripts/brief/context_brief.py"
