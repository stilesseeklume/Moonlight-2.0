#!/usr/bin/env python3
"""
每月 1 日 08:00 自动生成上月月报，写进 monthly/YYYY-MM.md
"""
import os
import re
from pathlib import Path
from datetime import date, timedelta
from calendar import monthrange

VAULT = Path(os.environ.get('MOONLIGHT_VAULT', '/Users/zhenliu/Moonlight'))
MONTHLY_DIR = VAULT / 'monthly'

def get_last_month():
    today = date.today()
    last = today.replace(day=1) - timedelta(days=1)
    return last.year, last.month

def gather_weight_rows(year, month):
    wf = VAULT / 'missions/weight-loss.md'
    if not wf.exists():
        return []
    text = wf.read_text(encoding='utf-8')
    prefix = f'{year}-{month:02d}-'
    rows = []
    for line in text.split('\n'):
        if line.startswith(f'| {prefix}'):
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 2:
                rows.append((parts[0], parts[1]))
    return rows

def gather_skincare_rate(year, month):
    sf = VAULT / 'missions/skincare.md'
    if not sf.exists():
        return '无数据'
    text = sf.read_text(encoding='utf-8')
    _, days_in_month = monthrange(year, month)
    done = sum(
        1 for d in range(1, days_in_month + 1)
        if f'{month}/{d}' in text and '✅' in text[text.find(f'{month}/{d}'):text.find(f'{month}/{d}')+100]
    )
    return f'{done}/{days_in_month} 天（{round(done/days_in_month*100)}%）'

def gather_mood_entries(month):
    mf = VAULT / 'notes/mood-log.md'
    if not mf.exists():
        return []
    text = mf.read_text(encoding='utf-8')
    return [l[2:] for l in text.split('\n') if l.startswith(f'- [{month:02d}-')][-10:]

def gather_highlights(month):
    hlf = VAULT / 'moonlight/inner-monologue/highlights.md'
    if not hlf.exists():
        return []
    text = hlf.read_text(encoding='utf-8')
    return [l for l in text.split('\n') if l.startswith(f'- [{month:02d}-')]

def generate(year, month):
    MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
    out = MONTHLY_DIR / f'{year}-{month:02d}.md'

    weight_rows = gather_weight_rows(year, month)
    skincare = gather_skincare_rate(year, month)
    moods = gather_mood_entries(month)
    highlights = gather_highlights(month)

    w_start = weight_rows[0][1] if weight_rows else '?'
    w_end = weight_rows[-1][1] if weight_rows else '?'
    try:
        delta = round(float(w_start.replace('斤','')) - float(w_end.replace('斤','')), 1)
        delta_str = f'-{delta} 斤' if delta > 0 else f'+{abs(delta)} 斤'
    except (ValueError, AttributeError):
        delta_str = '?'

    lines = [
        f'# {year} 年 {month} 月月报',
        f'> 自动生成于 {date.today()}',
        '',
        '## ⚔️ 屠龙',
        f'- 月初：{w_start} → 月末：{w_end}（{delta_str}）',
        '',
        '## 💆 护肤执行率',
        f'- {skincare}',
        '',
        '## 🎭 月光情绪（最近 10 条）',
    ]
    lines += [f'- {m}' for m in moods] or ['- 无记录']
    lines += ['', '## 💬 月光这个月说过的话']
    lines += highlights or ['- 无记录']
    lines += ['', '---', f'*{year} 年 {month} 月已翻篇。*']

    out.write_text('\n'.join(lines), encoding='utf-8')
    print(f'✅ 月报生成: {out.relative_to(VAULT)}')

if __name__ == '__main__':
    y, m = get_last_month()
    generate(y, m)
