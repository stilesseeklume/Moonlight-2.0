#!/usr/bin/env python3
"""月光 · 月底跨工程对账脚本

扫 projects/A*.md 4 张工程卡的「最近 3 条推进」节，聚合本月推进次数 → reports/YYYY-MM-account.md

用法:
    python3 account.py                  # 本月（默认）
    python3 account.py --month 2026-04  # 指定月份
    python3 account.py --dry-run        # 只打印不写文件

推进记录格式约定（写在工程卡「最近 3 条推进」节内）:
    - [2026-05-12] 把 A2 年级管理系统1.0 推进了 3 节
    - [2026-05-13] 跑了 30 分钟，引体 5 个
    （日期支持 [YYYY-MM-DD] / (YYYY-MM-DD) / 纯 YYYY-MM-DD 开头）

月光使用方式: 每月 28 号开场仪式 run 此脚本 → 读输出 → 添加人味评语 → 写入月度对账结论
"""
import argparse
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent  # .claude/scripts/monthly/ → Moonlight/
PROJECTS = ROOT / 'projects'
REPORTS = ROOT / 'reports'

CARDS = {
    'A1-body.md':          ('A1', '身体重塑'),
    'A2-grade-leader.md':  ('A2', '年级长立柱'),
    'A3-finance.md':       ('A3', '财务筑基'),
    'A4-ai-capability.md': ('A4', 'AI 时代能力'),
}

SECTION_RE = re.compile(r'##\s*最近[^\n]*推进\s*\n(.*?)(?=\n##|\Z)', re.DOTALL)
DATE_RE = re.compile(r'-\s*[\[\(]?(\d{4})-(\d{2})-(\d{2})[\]\)]?\s*[:：]?\s*(.+)')


def extract_progress(text):
    m = SECTION_RE.search(text)
    return m.group(1).strip() if m else ''


def parse_lines(section, year, month):
    out = []
    for line in section.splitlines():
        m = DATE_RE.match(line.strip())
        if m:
            y, mo, d, content = m.groups()
            if int(y) == year and int(mo) == month:
                out.append((f"{y}-{mo}-{d}", content.strip()))
    return out


def light(n):
    if n == 0:
        return '🔴 零推进'
    if n < 3:
        return '🟡 偏少'
    return '🟢 充分'


def main():
    p = argparse.ArgumentParser(description='月光 · 月底对账')
    p.add_argument('--month', default=None, help='YYYY-MM 格式，默认本月')
    p.add_argument('--dry-run', action='store_true', help='只打印不写文件')
    args = p.parse_args()

    today = date.today()
    if args.month:
        year, month = map(int, args.month.split('-'))
    else:
        year, month = today.year, today.month

    lines = [
        f"# {year}-{month:02d} · 跨工程对账",
        "",
        f"> 月光月底自动生成 · 跑于 {today.isoformat()} · 草稿待人味润色",
        "",
        "---",
        "",
        "## 工程推进次数（本月）",
        "",
        "| 工程 | 名称 | 本月推进 | 状态 |",
        "|---|---|---|---|",
    ]

    counts = {}
    details = {}
    missing = []

    for fname, (code, name) in CARDS.items():
        path = PROJECTS / fname
        if not path.exists():
            missing.append(fname)
            continue
        text = path.read_text(encoding='utf-8')
        sect = extract_progress(text)
        recs = parse_lines(sect, year, month)
        counts[code] = len(recs)
        details[code] = (name, recs)
        lines.append(f"| {code} | {name} | {len(recs)} | {light(len(recs))} |")

    lines.extend([
        "",
        "---",
        "",
        "## 每张工程卡推进明细",
        "",
    ])
    for code, (name, recs) in details.items():
        lines.append(f"### {code} · {name}")
        lines.append("")
        if not recs:
            lines.append("- _本月无推进记录_")
        else:
            for d, c in recs:
                lines.append(f"- [{d}] {c}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 自动观察",
        "",
    ])
    red_engs = [code for code, n in counts.items() if n == 0]
    over_engs = sorted(counts.items(), key=lambda x: -x[1])
    top = over_engs[0] if over_engs else None

    if red_engs:
        lines.append(f"- 🔴 **零推进工程**：{', '.join(red_engs)} — 月光必追问")
    if top and top[1] >= 5:
        lines.append(f"- 🟢 **本月主力**：{top[0]} 推进 {top[1]} 次，主要矛盾命中率高")
    if not red_engs and (not top or top[1] < 3):
        lines.append("- 🟡 **整月低调**：四个工程都推进偏少，要不要重新评估阶段主要矛盾？")

    lines.extend([
        "",
        "---",
        "",
        "## 月光人味评语",
        "",
        "_待月光补写：哪个工程被冷落、哪个被过度投入、阶段优先级要不要调？_",
        "",
    ])

    report = '\n'.join(lines)

    if args.dry_run:
        print(report)
        return

    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f"{year}-{month:02d}-account.md"
    out.write_text(report, encoding='utf-8')
    print(f"✅ 已生成 {out.relative_to(ROOT)}")
    red = sum(1 for n in counts.values() if n == 0)
    total = sum(counts.values())
    print(f"   红灯工程: {red} | 总推进: {total} 次")
    if missing:
        print(f"   ⚠ 缺失工程卡: {missing}")


if __name__ == '__main__':
    main()
