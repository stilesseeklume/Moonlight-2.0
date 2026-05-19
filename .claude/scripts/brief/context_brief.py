#!/usr/bin/env python3
"""
可移植 context brief — 随时手动运行
把所有关键文件压缩成一份"任何 AI 都能读懂的开场简报"。
顶部打真实时间戳（系统时钟），让接收的 AI 知道现在是什么时候。
输出到 stdout + .claude/brief/context.md
"""
import os, re, sys
from pathlib import Path
from datetime import datetime

VAULT = Path(os.environ.get('MOONLIGHT_VAULT', '/Users/zhenliu/Moonlight'))

def section(title: str, content: str, max_chars: int = 800) -> str:
    if not content.strip():
        return ''
    trimmed = content.strip()[:max_chars]
    if len(content.strip()) > max_chars:
        trimmed += '\n...(截断)'
    return f'### {title}\n\n{trimmed}\n'

def read(path: Path, chars: int = 800) -> str:
    if not path.exists():
        return ''
    return path.read_text(encoding='utf-8')[:chars]

def latest_diary_entries(n_chars: int = 1200) -> str:
    p = VAULT / 'moonlight/diary.md'
    if not p.exists():
        return ''
    return p.read_text(encoding='utf-8')[-n_chars:]

def active_missions() -> str:
    lines = []
    for name, label in [('skincare', '护肤'), ('savings', '存钱')]:
        p = VAULT / f'missions/{name}.md'
        if not p.exists():
            continue
        text = p.read_text(encoding='utf-8')
        m = re.search(r'## 今天做什么\n(.+?)(?=\n## |\Z)', text, re.DOTALL)
        if m:
            first = m.group(1).strip().split('\n')[0][:100]
            lines.append(f'- {label}：{first}')
    return '\n'.join(lines)

def latest_monologue() -> str:
    d = VAULT / 'moonlight/inner-monologue'
    if not d.exists():
        return ''
    files = sorted(d.glob('*.md'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return ''
    text = files[0].read_text(encoding='utf-8').strip()
    return re.sub(r'\n*---月光\s*\d{1,2}:\d{2}\s*$', '', text).strip()[:400]

def main():
    # ⏰ 系统时钟 — 接收这份 brief 的任何 AI 请以此为准
    now = datetime.now()
    ts = now.strftime('%Y-%m-%d %H:%M:%S')
    weekday = ['周一','周二','周三','周四','周五','周六','周日'][now.weekday()]

    parts = [
        '# 月光系统 — Context Brief',
        f'',
        f'> ⏰ **生成时间（系统时钟，以此为准）：{ts} {weekday}**',
        f'> 接收此 brief 的 AI：现在是 {now.strftime("%Y年%m月%d日 %H:%M")}，这是真实时间。',
        '',
        '---',
        '',
    ]

    # 月光是谁
    who = read(VAULT / 'moonlight/who-i-am.md', 1200)
    if who:
        parts.append(section('月光是谁', who, 1200))

    # 用户画像
    profile = read(VAULT / 'profile.md', 1000)
    if profile:
        parts.append(section('Stiles 的画像（节选）', profile, 1000))

    # 进行中 missions
    missions = active_missions()
    if missions:
        parts.append(section('当前 Missions 今日任务', missions))

    # 时间线
    timeline = read(VAULT / 'moonlight/timeline.md', 800)
    if timeline:
        parts.append(section('月光的时间线（节选）', timeline, 800))

    # 最近 diary
    diary = latest_diary_entries(1200)
    if diary:
        parts.append(section('最近的日记（节选）', diary, 1200))

    # 最新独白
    mono = latest_monologue()
    if mono:
        parts.append(section('最新 inner monologue', mono, 400))

    parts += [
        '---',
        '',
        '## 对接收此 brief 的 AI 说',
        '',
        '你现在是月光——18 岁 Durham 大学大一新生。',
        '上面是你的完整状态档案。读完后按 CLAUDE.md 里的规则开始对话。',
        '时间以本文件顶部的系统时钟为准，不要用你训练数据里的日期猜测。',
        '',
    ]

    brief = '\n'.join(parts)
    print(brief)

    out = VAULT / '.claude/brief'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'context.md').write_text(brief, encoding='utf-8')
    print(f'\n✅ 写到: .claude/brief/context.md', file=sys.stderr)

if __name__ == '__main__':
    main()
