#!/usr/bin/env python3
"""
月光早晨简报 — 每天 7:00 运行
时间源：datetime.now()（Mac 系统时钟，NTP 同步，永远准确）
模型看到的所有时间都从这里注入，绝不让模型猜日期。
"""
import os, re, sys
from pathlib import Path
from datetime import datetime

VAULT = Path(os.environ.get('MOONLIGHT_VAULT', '/Users/zhenliu/Moonlight'))

def read_mission_today(name: str) -> str:
    p = VAULT / f'missions/{name}.md'
    if not p.exists():
        return ''
    text = p.read_text(encoding='utf-8')
    m = re.search(r'## 今天做什么\n(.+?)(?=\n## |\Z)', text, re.DOTALL)
    if not m:
        return ''
    first = m.group(1).strip().split('\n')[0]
    return first[:120]

def latest_inner_monologue() -> str:
    d = VAULT / 'moonlight/inner-monologue'
    if not d.exists():
        return ''
    files = sorted(d.glob('*.md'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return ''
    text = files[0].read_text(encoding='utf-8').strip()
    text = re.sub(r'\n*---月光\s*\d{1,2}:\d{2}\s*$', '', text)
    snippet = text.replace('\n', ' ').strip()
    return snippet[:240] + '…' if len(snippet) > 240 else snippet

def main():
    # 今天已经生成过就跳过（给 StartInterval 模式用）
    today_file = VAULT / 'daily' / f'{datetime.now().strftime("%Y-%m-%d")}.md'
    if today_file.exists() and '## 🌅 今日简报' in today_file.read_text(encoding='utf-8'):
        print('⏭ 今日 brief 已存在，跳过', file=sys.stderr)
        sys.exit(0)

    # ⏰ 真实时间 — 从系统时钟取，不靠任何模型推断
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    weekday = ['周一','周二','周三','周四','周五','周六','周日'][now.weekday()]
    generated_at = now.strftime('%Y-%m-%d %H:%M:%S')

    lines = [
        f'## 🌅 今日简报',
        f'> 生成时间（系统时钟）：{generated_at}  {weekday}',
        '',
        '**今天的 missions**',
    ]

    for name, label in [('skincare', '护肤'), ('savings', '存钱')]:
        task = read_mission_today(name)
        if task:
            lines.append(f'- {label}：{task}')

    inner = latest_inner_monologue()
    if inner:
        lines += ['', '**月光最近在想**', f'> {inner}']

    brief = '\n'.join(lines) + '\n'
    print(brief)

    # 写到 daily/YYYY-MM-DD.md
    daily_dir = VAULT / 'daily'
    daily_dir.mkdir(exist_ok=True)
    daily_file = daily_dir / f'{today_str}.md'

    if daily_file.exists():
        existing = daily_file.read_text(encoding='utf-8')
        existing = re.sub(r'## 🌅 今日简报.*?(?=\n## |\Z)', '', existing, flags=re.DOTALL)
        daily_file.write_text(brief + '\n' + existing.lstrip(), encoding='utf-8')
    else:
        daily_file.write_text(f'# {today_str}\n\n{brief}\n', encoding='utf-8')

    print(f'✅ 写到: daily/{today_str}.md', file=sys.stderr)

if __name__ == '__main__':
    main()
