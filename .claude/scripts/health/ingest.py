#!/usr/bin/env python3
"""
月光 Health Ingest — 兼容中英文 column + 小时/日 聚合
从 iCloud Drive 拉 Health Auto Export 的 CSV，
写进 missions/weight-loss.md + Daily Note。
"""
import os
import sys
import csv
import re
from pathlib import Path
from datetime import datetime, date
from collections import defaultdict

ICLOUD_ROOT = Path.home() / 'Library/Mobile Documents/com~apple~CloudDocs'
HEALTH_EXPORT_DIR = Path.home() / 'Library/Mobile Documents/iCloud~com~ifunography~HealthExport/Documents'
VAULT = Path(os.environ.get('MOONLIGHT_VAULT', '/Users/zhenliu/Moonlight'))
WEIGHT_FILE = VAULT / 'missions/weight-loss.md'
DAILY_DIR = VAULT / 'daily'

KG_TO_JIN = 2.0

# === 中英文 column 映射 ===
COL_DATE = ['Date', '日期/时间', 'Date/Time', '日期']
COL_WEIGHT_KG = ['Body Mass (kg)', '体重 (千克)', 'Weight (kg)']
COL_SLEEP_HR = [
    'Sleep Analysis [Asleep] (hr)', '睡眠分析 [睡眠时长] (小时)',
    'Sleep Analysis [In Bed] (hr)', '睡眠分析 [在床上] (小时)',
    'Sleep Analysis [Total] (小时)', '睡眠分析 [Total] (小时)',
]
COL_STEPS = ['Step Count (count)', '步数 (步)', '步数 (count)']
COL_BODY_FAT = ['Body Fat Percentage (%)', '体脂百分比 (%)']
COL_RESTING_HR = ['Resting Heart Rate (count/min)', '静息心率 (bpm)']

def find_col(headers, candidates):
    for c in candidates:
        if c in headers:
            return c
    return None

def find_csv() -> 'Path | None':
    """优先查 ifunography HealthExport app 的 iCloud 目录"""
    # 主路径：Health Auto Export app (ifunography)
    if HEALTH_EXPORT_DIR.exists():
        csvs = sorted(HEALTH_EXPORT_DIR.rglob('*.csv'), key=lambda p: p.stat().st_mtime, reverse=True)
        if csvs:
            return csvs[0]
    # fallback: 原始 iCloud Drive
    if ICLOUD_ROOT.exists():
        candidates = list(ICLOUD_ROOT.rglob('HealthAutoExport*.csv'))
        candidates += list(ICLOUD_ROOT.rglob('Health*Export*.csv'))
        candidates += list(ICLOUD_ROOT.rglob('HealthMetrics*.csv'))
        if candidates:
            return max(candidates, key=lambda p: p.stat().st_mtime)
    return None

def parse_date(s):
    """支持 '2026-05-06', '2026/5/6 0:00', '2026-05-06T00:00:00' 等"""
    s = s.strip()
    for fmt in ('%Y/%m/%d %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # ISO fallback
    try:
        return datetime.fromisoformat(s.replace('/', '-').split('T')[0]).date()
    except (ValueError, IndexError):
        pass
    try:
        return datetime.fromisoformat(s[:10].replace('/', '-')).date()
    except ValueError:
        return None

def parse_csv(path):
    """返回 {date: {'weight_jin', 'sleep_hr', 'steps', 'body_fat', 'resting_hr'}}"""
    with open(path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        col_date = find_col(headers, COL_DATE)
        col_weight = find_col(headers, COL_WEIGHT_KG)
        col_sleep = find_col(headers, COL_SLEEP_HR)
        col_steps = find_col(headers, COL_STEPS)
        col_fat = find_col(headers, COL_BODY_FAT)
        col_rhr = find_col(headers, COL_RESTING_HR)

        if not col_date:
            print(f'❌ CSV 没找到日期列。已知 headers: {headers[:5]}...')
            return {}

        # 按 date 收集，因为 CSV 可能是小时粒度
        per_day = defaultdict(lambda: {'weights': [], 'sleeps': [], 'steps_sum': 0,
                                        'fats': [], 'rhrs': []})
        for row in reader:
            d = parse_date(row.get(col_date, ''))
            if not d:
                continue
            def fnum(col):
                if not col:
                    return None
                v = row.get(col, '').strip()
                if not v:
                    return None
                try:
                    return float(v)
                except ValueError:
                    return None

            w = fnum(col_weight)
            if w:
                per_day[d]['weights'].append(w)
            s = fnum(col_sleep)
            if s:
                per_day[d]['sleeps'].append(s)
            st = fnum(col_steps)
            if st:
                per_day[d]['steps_sum'] += int(st)
            f = fnum(col_fat)
            if f:
                per_day[d]['fats'].append(f)
            rhr = fnum(col_rhr)
            if rhr:
                per_day[d]['rhrs'].append(rhr)

    # 聚合：体重取均值（忽略离谱波动）；睡眠取最大（一天一次主睡眠）；步数累加
    out = {}
    for d, agg in per_day.items():
        rec = {}
        if agg['weights']:
            avg_kg = sum(agg['weights']) / len(agg['weights'])
            rec['weight_jin'] = round(avg_kg * KG_TO_JIN, 1)
        if agg['sleeps']:
            rec['sleep_hr'] = round(max(agg['sleeps']), 1)
        if agg['steps_sum']:
            rec['steps'] = agg['steps_sum']
        if agg['fats']:
            rec['body_fat'] = round(sum(agg['fats']) / len(agg['fats']), 1)
        if agg['rhrs']:
            rec['resting_hr'] = round(sum(agg['rhrs']) / len(agg['rhrs']), 0)
        if rec:
            out[d] = rec
    return out

def latest_logged_weight_date() -> date | None:
    """读取 missions/weight-loss.md 里的最新体重日期。"""
    if not WEIGHT_FILE.exists():
        return None
    text = WEIGHT_FILE.read_text(encoding='utf-8')
    dates = []
    for m in re.finditer(r'^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*[\d.]+\s*\|', text, re.MULTILINE):
        try:
            dates.append(datetime.strptime(m.group(1), '%Y-%m-%d').date())
        except ValueError:
            continue
    return max(dates) if dates else None

def upsert_weight_row(text: str, target_date: date, weight_jin: float) -> str:
    """在进度表里更新或插入目标日期的体重行。"""
    date_str = target_date.strftime('%Y-%m-%d')
    new_row = f'| {date_str} | {weight_jin:g} | 自动同步 |'
    row_re = re.compile(rf'^\|\s*{re.escape(date_str)}\s*\|.*$', re.MULTILINE)
    if row_re.search(text):
        return row_re.sub(new_row, text, count=1)

    reward_match = re.search(r'^## 奖励系统', text, re.MULTILINE)
    if reward_match:
        before = text[:reward_match.start()].rstrip('\n')
        after = text[reward_match.start():].lstrip('\n')
        return before + '\n' + new_row + '\n\n' + after

    return text.rstrip('\n') + '\n' + new_row + '\n'

MOONLIGHT_FILE = VAULT / 'Moonlight.md'
PEAK_JIN = 213.0
TARGET_JIN = 166.0
DEADLINE = date(2026, 6, 7)

def update_weight_md(data):
    if not WEIGHT_FILE.exists():
        print(f'⚠ {WEIGHT_FILE} 不存在')
        return
    text = WEIGHT_FILE.read_text(encoding='utf-8')
    weight_days = sorted([d for d in data if 'weight_jin' in data[d]], reverse=True)
    if not weight_days:
        print('⚠ 数据里没体重')
        return
    latest = weight_days[0]
    new_weight = data[latest]['weight_jin']

    # 1. 更新 header blockquote: > 当前 XXX 斤 → 目标 166 斤 · 截止 2026-06-07 · 剩 XX 天
    days_left = max(0, (DEADLINE - date.today()).days)
    text = re.sub(
        r'(> 当前\s*)[\d.]+(\s*斤 → 目标 166 斤 · 截止 2026-06-07 · 剩\s*)\d+(\s*天)',
        rf'\g<1>{new_weight:g}\g<2>{days_left}\g<3>',
        text
    )

    # 2. 在 ## 进度 表里更新/插入对应日期的行
    text = upsert_weight_row(text, latest, new_weight)

    WEIGHT_FILE.write_text(text, encoding='utf-8')
    print(f'✅ missions/weight-loss.md 更新: {latest} = {new_weight:g} 斤')
    return latest, new_weight

def update_moonlight_md(weight_jin: float):
    if not MOONLIGHT_FILE.exists():
        print(f'⚠ {MOONLIGHT_FILE} 不存在')
        return
    text = MOONLIGHT_FILE.read_text(encoding='utf-8')
    total = PEAK_JIN - TARGET_JIN  # 47
    slain = round(PEAK_JIN - weight_jin, 1)
    remaining = round(weight_jin - TARGET_JIN, 1)
    hp_int = round(slain)
    filled = round(slain / total * 30)
    filled = max(0, min(30, filled))
    bar = '█' * filled + '░' * (30 - filled)

    text = re.sub(
        r'HP <code>[█░]+</code> \d+/47',
        f'HP <code>{bar}</code> {hp_int}/47',
        text
    )
    text = re.sub(
        r'213 → [\d.]+ → 166 · 已砍 [\d.]+ 斤 · 剩 [\d.]+ 斤',
        f'213 → {weight_jin:g} → 166 · 已砍 {slain} 斤 · 剩 {remaining} 斤',
        text
    )
    MOONLIGHT_FILE.write_text(text, encoding='utf-8')
    print(f'✅ Moonlight.md 仪表盘更新: HP {hp_int}/47 · 剩 {remaining} 斤')

TODAY_FILE = VAULT / 'notes/today.md'

def update_today_md(data):
    today = date.today()
    rec = data.get(today)
    if not rec:
        print('⚠ CSV 里没有今天的数据，notes/today.md 不更新')
        return

    updates = []
    if 'steps' in rec:
        updates.append(('步数', f'{rec["steps"]:,} 步'))
    if 'sleep_hr' in rec:
        s = rec['sleep_hr']
        flag = '🚨' if s < 5.5 else ('⚠' if s < 7 else '✅')
        updates.append(('睡眠', f'{s} 小时 {flag}'))

    if not TODAY_FILE.exists() or not updates:
        return

    text = TODAY_FILE.read_text(encoding='utf-8')
    for label, value in updates:
        pattern = rf'(- \*\*{label}\*\*：).*'
        new_text = re.sub(pattern, rf'\g<1>{value} · 自动同步', text)
        if new_text == text:
            text = re.sub(
                r'(- \*\*体重\*\*：.*\n)',
                rf'\1- **{label}**：{value} · 自动同步\n',
                text
            )
        else:
            text = new_text
    TODAY_FILE.write_text(text, encoding='utf-8')
    print(f'✅ today.md 更新: {", ".join(l for l, _ in updates)}')

def update_daily_note(data):
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    rec = data.get(today)
    if not rec:
        # 用最新一天
        if not data:
            return
        latest = max(data.keys())
        rec = data[latest]
        target = latest
    else:
        target = today

    note_path = DAILY_DIR / f'{target.strftime("%Y-%m-%d")}.md'
    block = f'## 🩺 健康数据（自动同步 {datetime.now().strftime("%Y-%m-%d %H:%M")}）\n\n'
    block += '| 指标 | 值 |\n|------|-----|\n'
    if 'weight_jin' in rec:
        block += f'| 体重 | {rec["weight_jin"]:g} 斤 |\n'
    if 'body_fat' in rec:
        block += f'| 体脂率 | {rec["body_fat"]:g}% |\n'
    if 'sleep_hr' in rec:
        s = rec['sleep_hr']
        flag = '🚨 严重不足' if s < 5.5 else ('⚠ 不足' if s < 7 else '✅ OK')
        block += f'| 睡眠 | {s} 小时 {flag} |\n'
    if 'resting_hr' in rec:
        block += f'| 静息心率 | {rec["resting_hr"]:g} bpm |\n'
    if 'steps' in rec:
        block += f'| 步数 | {rec["steps"]:,} |\n'
    block += '\n'

    if note_path.exists():
        existing = note_path.read_text(encoding='utf-8')
        existing = re.sub(r'## 🩺 健康数据.*?(?=\n## |\Z)', block.rstrip() + '\n\n',
                          existing, flags=re.DOTALL)
        if '## 🩺 健康数据' not in existing:
            existing += '\n' + block
        note_path.write_text(existing, encoding='utf-8')
    else:
        note_path.write_text(f'# {target.strftime("%Y-%m-%d")}\n\n{block}', encoding='utf-8')
    print(f'✅ Daily Note 更新: {note_path.relative_to(VAULT)}')

def main():
    csv_path = find_csv()
    if not csv_path:
        print(f'❌ iCloud Drive 里没找到 Health Auto Export CSV')
        print(f'   查找了: {ICLOUD_ROOT}/HealthExport/')
        print(f'   以及递归搜索 HealthAutoExport*.csv')
        sys.exit(1)

    age_min = (datetime.now().timestamp() - csv_path.stat().st_mtime) / 60
    print(f'📂 CSV: {csv_path.name} ({age_min:.0f} 分钟前)')

    data = parse_csv(csv_path)
    if not data:
        print('⚠ CSV 解析为空——检查 iPhone 端 Health Auto Export 配置')
        sys.exit(1)

    csv_latest = max(data.keys())
    logged_latest = latest_logged_weight_date()
    weight_days = sum(1 for r in data.values() if 'weight_jin' in r)
    sleep_days = sum(1 for r in data.values() if 'sleep_hr' in r)
    print(f'📊 解析到 {len(data)} 天 (最新 {csv_latest}, 体重: {weight_days}, 睡眠: {sleep_days})')

    if logged_latest and csv_latest < logged_latest:
        print(f'⚠ CSV 最新日期 {csv_latest} 早于现有记录 {logged_latest}，跳过写回，避免旧数据覆盖。')
        sys.exit(0)

    new_weight = update_weight_md(data)
    if new_weight:
        _, weight_value = new_weight
        update_moonlight_md(weight_value)
    update_daily_note(data)
    update_today_md(data)
    print('\n✅ 同步完成')

if __name__ == '__main__':
    main()
