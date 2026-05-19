#!/usr/bin/env python3
"""
月光体检 — 扫过去 30 天，看月光自己有没有失职。

铁律检查：
- A 类小喇叭：每次对话 ≥1 条（数 dialogues + diary 中的 A 类条目）
- B 类发现：每次对话 ≥1 张卡片
- 导师产出：每次对话 ≥1 张卡片
- timeline 每周日刷新
- growth 每月 ≥1 条月光雷达
- reading-log 每周 ≥1 篇真读笔记

输出：
- stdout 打报告
- 写 `growth/checkup-history.md` 累积
- 失职项数量给 morning brief 用（红字告警）
"""
import os
import re
import sys
import json
from pathlib import Path
from datetime import date, datetime, timedelta
from collections import Counter

VAULT = Path(os.environ.get('MOONLIGHT_VAULT', '/Users/zhenliu/Moonlight'))

def days_ago(d: date) -> int:
    return (date.today() - d).days

def parse_diary_entries() -> list[dict]:
    """返回 [{'date': date, 'text': str}, ...]"""
    f = VAULT / 'moonlight/diary.md'
    if not f.exists():
        return []
    text = f.read_text(encoding='utf-8')
    entries = []
    parts = re.split(r'^## (\d{4}-\d{2}-\d{2})$', text, flags=re.MULTILINE)
    for i in range(1, len(parts), 2):
        try:
            d = datetime.strptime(parts[i], '%Y-%m-%d').date()
            entries.append({'date': d, 'text': parts[i+1] if i+1 < len(parts) else ''})
        except ValueError:
            continue
    return entries

def count_articles_recent(days: int) -> list[Path]:
    cutoff = date.today() - timedelta(days=days)
    out = []
    art_dir = VAULT / 'material/articles'
    if not art_dir.exists():
        return out
    for p in art_dir.glob('*.md'):
        if p.name == 'articles.md':
            continue
        try:
            text = p.read_text(encoding='utf-8')
            m = re.search(r'created:\s*(\d{4}-\d{2}-\d{2})', text)
            if m:
                d = datetime.strptime(m.group(1), '%Y-%m-%d').date()
                if d >= cutoff:
                    out.append(p)
        except Exception:
            pass
    return out

def count_dialogues_recent(days: int) -> list[Path]:
    cutoff = date.today() - timedelta(days=days)
    out = []
    d = VAULT / 'dialogues'
    if not d.exists():
        return out
    for p in d.glob('*.md'):
        # 文件名形如 YYYY-MM-DD-xxx.md
        m = re.match(r'(\d{4}-\d{2}-\d{2})', p.stem)
        if m:
            try:
                dt = datetime.strptime(m.group(1), '%Y-%m-%d').date()
                if dt >= cutoff:
                    out.append(p)
            except ValueError:
                pass
    return out

def count_reading_log_entries(days: int) -> int:
    f = VAULT / 'moonlight/reading-log.md'
    if not f.exists():
        return 0
    text = f.read_text(encoding='utf-8')
    cutoff = date.today() - timedelta(days=days)
    n = 0
    # 笔记标题形如 ### YYYY-MM-DD · 标题
    for m in re.finditer(r'^### (\d{4}-\d{2}-\d{2}) ·', text, re.MULTILINE):
        try:
            d = datetime.strptime(m.group(1), '%Y-%m-%d').date()
            if d >= cutoff:
                n += 1
        except ValueError:
            pass
    return n

def check_timeline_freshness() -> tuple[bool, int]:
    """timeline 是否在最近一个周日刷新过"""
    f = VAULT / 'moonlight/timeline.md'
    if not f.exists():
        return False, 999
    mtime = datetime.fromtimestamp(f.stat().st_mtime).date()
    days = (date.today() - mtime).days
    # 找最近的周日
    today = date.today()
    last_sunday = today - timedelta(days=(today.weekday() + 1) % 7)
    return mtime >= last_sunday - timedelta(days=1), days

def check_growth_monthly() -> dict[str, bool]:
    """每个 growth 文件本月有没有月光雷达条目"""
    out = {}
    g_dir = VAULT / 'growth'
    if not g_dir.exists():
        return out
    today = date.today()
    month_str = today.strftime('%Y-%m')
    for p in g_dir.glob('*.md'):
        if p.name == 'README.md':
            continue
        text = p.read_text(encoding='utf-8')
        # 找 ### 2026-XX 节
        out[p.stem] = month_str in text
    return out

def report() -> dict:
    today = date.today()
    diary = parse_diary_entries()
    last_30 = [e for e in diary if days_ago(e['date']) <= 30]
    last_7 = [e for e in diary if days_ago(e['date']) <= 7]

    articles_30 = count_articles_recent(30)
    articles_7 = count_articles_recent(7)
    dialogues_7 = count_dialogues_recent(7)
    reading_7 = count_reading_log_entries(7)

    timeline_fresh, timeline_age = check_timeline_freshness()
    growth_status = check_growth_monthly()

    failures = []

    # 铁律 1：每周 ≥ 1 张卡片
    if len(articles_7) == 0:
        failures.append(f'本周新卡片 = 0（应 ≥ 1，最近卡片：{articles_30[-1].name if articles_30 else "无"}）')

    # 铁律 2：reading-log 每周 ≥ 1 篇
    if reading_7 == 0:
        failures.append('本周 reading-log 笔记 = 0（应 ≥ 1）')

    # 铁律 3：timeline 周更
    if not timeline_fresh:
        failures.append(f'timeline.md 上次刷新 {timeline_age} 天前（应每周日更新）')

    # 铁律 4：growth 月雷达
    growth_failures = [k for k, v in growth_status.items() if not v]
    if growth_failures:
        failures.append(f'本月 growth 雷达失职：{", ".join(growth_failures)}')

    # 铁律 5：diary 至少每 3 天一条
    if last_7:
        max_gap = 0
        sorted_days = sorted([e['date'] for e in last_7])
        for i in range(1, len(sorted_days)):
            gap = (sorted_days[i] - sorted_days[i-1]).days
            max_gap = max(max_gap, gap)
        if max_gap > 3:
            failures.append(f'diary 最大间隔 {max_gap} 天（应 ≤ 3）')

    return {
        'date': today.isoformat(),
        'last_30_days': {
            'diary_entries': len(last_30),
            'articles': len(articles_30),
            'dialogues': len(dialogues_30) if (dialogues_30 := count_dialogues_recent(30)) else 0,
        },
        'last_7_days': {
            'diary_entries': len(last_7),
            'articles': len(articles_7),
            'dialogues': len(dialogues_7),
            'reading_log_notes': reading_7,
        },
        'timeline': {
            'fresh': timeline_fresh,
            'age_days': timeline_age,
        },
        'growth_monthly': growth_status,
        'failures': failures,
        'pass': len(failures) == 0,
    }

def render(r: dict) -> str:
    lines = [f'# 月光体检 · {r["date"]}', '']
    lines.append(f'## 30 天概况')
    d30 = r['last_30_days']
    lines.append(f'- diary 条目：{d30["diary_entries"]}')
    lines.append(f'- 卡片产出：{d30["articles"]}')
    lines.append(f'- dialogues：{d30["dialogues"]}')
    lines.append('')
    lines.append(f'## 7 天概况')
    d7 = r['last_7_days']
    lines.append(f'- diary 条目：{d7["diary_entries"]}')
    lines.append(f'- 新卡片：{d7["articles"]}')
    lines.append(f'- dialogues：{d7["dialogues"]}')
    lines.append(f'- reading-log 笔记：{d7["reading_log_notes"]}')
    lines.append('')
    lines.append(f'## 维护状态')
    lines.append(f'- timeline.md：{"✅ 新鲜" if r["timeline"]["fresh"] else "⚠ 过期"}（{r["timeline"]["age_days"]} 天前刷新）')
    for k, v in r['growth_monthly'].items():
        lines.append(f'- growth/{k}：{"✅" if v else "🚨"} 本月雷达')
    lines.append('')
    if r['failures']:
        lines.append('## 🚨 失职项')
        for f in r['failures']:
            lines.append(f'- {f}')
    else:
        lines.append('## ✅ 全部铁律 PASS')
    lines.append('')
    return '\n'.join(lines)

def main():
    r = report()
    md = render(r)
    print(md)

    # 写 history
    hist = VAULT / 'growth/checkup-history.md'
    hist.parent.mkdir(parents=True, exist_ok=True)
    if hist.exists():
        existing = hist.read_text(encoding='utf-8')
    else:
        existing = '# 月光体检历史\n\n> 自动生成。每次跑 `health_check.py` 追加一条。\n\n'
    hist.write_text(existing + '\n---\n\n' + md, encoding='utf-8')

    # JSON 给 brief 用
    json_out = VAULT / '.claude/scripts/checkup/latest.json'
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(r, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

    if not r['pass']:
        sys.exit(1)  # cron 监控用

if __name__ == '__main__':
    main()
