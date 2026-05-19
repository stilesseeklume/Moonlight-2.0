#!/usr/bin/env python3
"""
计算护肤连续打卡天数，写进 today.md 关键数据区块
每天 22:00 跑一次（com.moonlight.skincare launchd）
"""
import os
import re
from pathlib import Path
from datetime import date, timedelta

VAULT = Path(os.environ.get('MOONLIGHT_VAULT', '/Users/zhenliu/Moonlight'))
SKINCARE_FILE = VAULT / 'missions/skincare.md'
TODAY_FILE = VAULT / 'notes/today.md'

def calc_streak() -> int:
    if not SKINCARE_FILE.exists():
        return 0
    text = SKINCARE_FILE.read_text(encoding='utf-8')
    today = date.today()
    done_dates = set()
    for line in text.split('\n'):
        if not line.startswith('|'):
            continue
        parts = [p.strip() for p in line.split('|') if p.strip()]
        if len(parts) < 2:
            continue
        date_str = parts[0]
        rest = ''.join(parts[1:])
        if '✅' not in rest:
            continue
        # 格式：M/D 或 YYYY-MM-DD
        try:
            if '/' in date_str:
                m, d = map(int, date_str.split('/'))
                done_dates.add(date(today.year, m, d))
            elif '-' in date_str and len(date_str) == 10:
                done_dates.add(date.fromisoformat(date_str))
        except (ValueError, TypeError):
            continue

    streak = 0
    check = today
    while check in done_dates:
        streak += 1
        check -= timedelta(days=1)
    return streak

def update_today_md(streak: int):
    if not TODAY_FILE.exists():
        return
    text = TODAY_FILE.read_text(encoding='utf-8')
    value = f'{streak} 天连续' if streak > 0 else '今天还没打卡'
    pattern = r'(- \*\*护肤 streak\*\*：).*'
    new_text = re.sub(pattern, rf'\g<1>{value}', text)
    if new_text == text:
        # 插入到关键数据末尾（屠龙进度行后）
        new_text = re.sub(
            r'(- \*\*屠龙进度\*\*：.*\n)',
            rf'\1- **护肤 streak**：{value}\n',
            text
        )
    TODAY_FILE.write_text(new_text, encoding='utf-8')
    print(f'✅ 护肤 streak: {value}')

if __name__ == '__main__':
    s = calc_streak()
    update_today_md(s)
