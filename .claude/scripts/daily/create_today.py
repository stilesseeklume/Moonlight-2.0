#!/usr/bin/env python3
"""
Today 自动换日器。

职责：
- 如果 `notes/today.md` 还是昨天，先归档到 `daily/YYYY-MM-DD.md`。
- 然后重建当天的 `notes/today.md` 模板。
- 如果今天已经是今天，什么都不做。

幂等：
- 可重复运行，不会重复归档当天文件。
- 归档时保留旧 `notes/today.md` 的正文，只把标题换成 `# 今日上下文 · YYYY-MM-DD`。
"""
import os
import re
from pathlib import Path
from datetime import date

DEFAULT_VAULT = Path(__file__).resolve().parents[3]
VAULT = Path(os.environ.get('MOONLIGHT_VAULT', DEFAULT_VAULT))
TODAY_FILE = VAULT / 'notes/today.md'
DAILY_DIR = VAULT / 'daily'

TODAY_TEMPLATE = """# {date}

## 🌅 月光今晨 brief
*（今天先确认系统还能不能持续迭代，别急着长功能。）*

## 🩺 健康数据（自动同步）
*（health ingest 跑完后会更新这里。）*

## 💭 今天的心情
*（白天随手写一句就行。）*

## ✏️ 今日杂记
*（开放区：任何不属于上面的内容。）*

## 对话线索
*（Sats / 月光补充的当日线索。）*

## 🌙 月光雷达
*（月光晚上自动写观察到的当日 pattern。）*

"""

ARCHIVE_NOTE = "> 从 `notes/today.md` 归档。"
DATE_RE = re.compile(r'^#\s*(?:今日上下文\s*·\s*)?(\d{4}-\d{2}-\d{2})(?:\s*.*)?$')


def parse_note_date(text: str) -> date | None:
    first = text.splitlines()[0].strip() if text.strip() else ''
    m = DATE_RE.match(first)
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(1))
    except ValueError:
        return None


def build_archive(text: str, note_date: date) -> str:
    lines = text.rstrip('\n').splitlines()
    if not lines:
        return f'# 今日上下文 · {note_date.isoformat()}\n\n{ARCHIVE_NOTE}\n'

    lines[0] = f'# 今日上下文 · {note_date.isoformat()}'
    if len(lines) == 1:
        lines.append('')
    if len(lines) < 3 or lines[1].strip() != ARCHIVE_NOTE:
        lines.insert(1, '')
        lines.insert(2, ARCHIVE_NOTE)
    return '\n'.join(lines).rstrip() + '\n'


def write_archive(path: Path, archive: str) -> None:
    if not path.exists():
        path.write_text(archive, encoding='utf-8')
        return

    existing = path.read_text(encoding='utf-8')
    if archive.strip() in existing:
        return

    merged = (
        existing.rstrip()
        + '\n\n---\n\n'
        + '<!-- auto-archived from notes/today.md -->\n\n'
        + archive.strip()
        + '\n'
    )
    path.write_text(merged, encoding='utf-8')


def write_today_template(today: date) -> None:
    TODAY_FILE.parent.mkdir(parents=True, exist_ok=True)
    TODAY_FILE.write_text(TODAY_TEMPLATE.format(date=today.strftime('%Y-%m-%d')), encoding='utf-8')


def main():
    today = date.today()
    DAILY_DIR.mkdir(parents=True, exist_ok=True)

    if TODAY_FILE.exists():
        text = TODAY_FILE.read_text(encoding='utf-8')
        note_date = parse_note_date(text)
        if note_date == today:
            print(f'✓ today 已是当日: {TODAY_FILE.relative_to(VAULT)}')
            return

        if note_date is None:
            note_date = date.fromtimestamp(TODAY_FILE.stat().st_mtime)

        archive_path = DAILY_DIR / f'{note_date.strftime("%Y-%m-%d")}.md'
        write_archive(archive_path, build_archive(text, note_date))
        print(f'✅ 归档: {archive_path.relative_to(VAULT)}')

    write_today_template(today)
    print(f'✅ 创建: {TODAY_FILE.relative_to(VAULT)}')

    if TODAY_FILE.exists():
        return

    # 理论上不会走到这里，保留给未来调试
    print(f'⚠ 未能写入: {TODAY_FILE.relative_to(VAULT)}')

if __name__ == '__main__':
    main()
