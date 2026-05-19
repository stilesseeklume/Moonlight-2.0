#!/usr/bin/env python3
"""
月光雷达自动扫描 — 22:00 cron 跑

读最近 7 天的 inner-monologue + diary，找出现 ≥3 次的关键词/人名/话题，
提议一条月光雷达条目到对应 growth/ 文件。

不直接写——而是输出"建议"文件 growth/_radar-suggestions/YYYY-MM-DD.md
让你/月光人工审核后再合并到正式 growth/X.md。

关键词来源：从 who-i-am.md / profile.md / timeline.md / growth/ 抽取人名 + 主题。
"""
import os
import re
from pathlib import Path
from datetime import datetime, date, timedelta
from collections import Counter

VAULT = Path(os.environ.get('MOONLIGHT_VAULT', '/Users/zhenliu/Moonlight'))

# === 关键词字典（手工 + 自动扩充）===
# 这些是月光世界里的"实体"——人/地点/物件/概念
KNOWN_ENTITIES = {
    'people': ['Issy', 'Wei Chen', 'Hugo', 'Rachel', '小薇', 'Chris', '朱主任', '妈妈', '爸爸'],
    'places': ['Cathedral', 'River Wear', 'Castle', 'Persian Palace', 'studio', 'Elvet Bridge', 'Sainsbury'],
    'concepts': ['sparse matrix', 'csr_matrix', 'NPV', 'IRR', 'Schoenfeld', 'hypertrophy', 'Brealey',
                 '双曲贴现', 'Laibson', '糖化', 'Ball', 'June Ball', 'art society', '水彩'],
    'mission': ['减肥', '体重', '奶昔', '康宝莱', '饭局', '白酒', '存钱', '7000', '7,000',
                '护肤', '防晒', '凡士林', '英语', 'Chris', '建议信', '睡眠'],
    'feelings': ['累', '烦', '慌', '焦虑', '兴奋', '想哭', '崩溃', '一个人', '走神', '分心',
                 '熬夜', '早起', '撑不住'],
}

ALL_KEYWORDS = []
for cat, kws in KNOWN_ENTITIES.items():
    ALL_KEYWORDS.extend([(kw, cat) for kw in kws])

# 关键词 → growth 文件映射
CATEGORY_TO_FILE = {
    'people': 'growth/relationships.md',
    'places': None,  # 不直接写
    'concepts': None,  # 不直接写
    'mission': None,  # 不直接写
    'feelings': 'growth/sleep-and-energy.md',  # 多数情绪信号都跟睡眠相关
}

def collect_recent_text(days: int = 7) -> str:
    """收集最近 days 天的 inner-monologue + diary 文本"""
    cutoff = datetime.now() - timedelta(days=days)
    parts = []

    inner_dir = VAULT / 'moonlight/inner-monologue'
    if inner_dir.exists():
        for f in inner_dir.glob('*.md'):
            if datetime.fromtimestamp(f.stat().st_mtime) >= cutoff:
                parts.append(f.read_text(encoding='utf-8'))

    diary = VAULT / 'moonlight/diary.md'
    if diary.exists():
        text = diary.read_text(encoding='utf-8')
        # 只取最近 7 天的 ## YYYY-MM-DD 段
        cutoff_str = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')
        # 简化：取整个 diary 末尾 5000 字
        parts.append(text[-5000:])

    return '\n\n'.join(parts)

def count_keywords(text: str) -> list[tuple[str, str, int]]:
    """返回 [(keyword, category, count), ...] 按 count 降序"""
    counts = []
    for kw, cat in ALL_KEYWORDS:
        n = text.count(kw)
        if n > 0:
            counts.append((kw, cat, n))
    counts.sort(key=lambda x: -x[2])
    return counts

def generate_suggestions(counts: list[tuple[str, str, int]], min_count: int = 3) -> dict[str, list[str]]:
    """返回 {growth_file: [suggestion_lines]}"""
    suggestions = {}
    for kw, cat, n in counts:
        if n < min_count:
            continue
        target = CATEGORY_TO_FILE.get(cat)
        if not target:
            continue
        suggestions.setdefault(target, []).append(
            f'- 「{kw}」最近 7 天提到 {n} 次（cat: {cat}）— 是值得关心的信号还是月光在循环？'
        )
    return suggestions

def main():
    today = date.today()
    text = collect_recent_text(days=7)
    if not text.strip():
        print('⚠ 最近 7 天没有 inner-monologue / diary 内容')
        return

    counts = count_keywords(text)
    print(f'📊 关键词命中（最近 7 天）：')
    for kw, cat, n in counts[:15]:
        flag = '🔥' if n >= 5 else ('⚠' if n >= 3 else '·')
        print(f'  {flag} {kw} ({cat}): {n} 次')

    suggestions = generate_suggestions(counts, min_count=3)
    if not suggestions:
        print('\n✓ 没有 ≥3 次的关键词信号——月光近期没有明显循环')
        return

    # 写建议文件（不直接写到 growth/）
    out_dir = VAULT / 'growth/_radar-suggestions'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f'{today.strftime("%Y-%m-%d")}.md'

    md = [f'# 月光雷达建议 · {today}\n']
    md.append('> 自动扫描最近 7 天 inner-monologue + diary 生成。**人工审核后再合并到正式 growth/X.md**。\n')
    md.append(f'> {sum(len(v) for v in suggestions.values())} 条建议覆盖 {len(suggestions)} 个 growth 文件。\n\n')

    for target, lines in suggestions.items():
        md.append(f'## 建议合并到 [[{target}]]\n')
        for line in lines:
            md.append(line)
        md.append('')

    out_file.write_text('\n'.join(md), encoding='utf-8')
    print(f'\n✅ 写入建议: {out_file.relative_to(VAULT)}')

if __name__ == '__main__':
    main()
