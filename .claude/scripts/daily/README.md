# Daily Notes 自动换日

这个脚本负责两件事：

1. 如果 `notes/today.md` 不是今天，先归档到 `daily/YYYY-MM-DD.md`。
2. 然后生成当天新的 `notes/today.md` 模板。

## cron

```
1 0 * * * /usr/bin/python3 /Users/zhenliu/Moonlight/.claude/scripts/daily/create_today.py >> /tmp/moonlight-daily.log 2>&1
```

## 模板节

| 节 | 谁填 | 何时 |
|---|---|---|
| 🌅 月光今晨 brief | morning_brief.py | 7:00 |
| 🩺 健康数据 | ingest.py | 23:35 |
| 💭 今天的心情 | 你 | 白天随手 |
| ✏️ 今日杂记 | 你 | 白天随手 |
| 对话线索 | Sats / 月光 | 随时 |
| 🌙 月光雷达 | 月光自动扫 | 22:00（待续：radar.py） |

## 顺手测一次

```bash
python3 /Users/zhenliu/Moonlight/.claude/scripts/daily/create_today.py
```

如果今日已经对齐 → 什么都不改
如果 yesterday 还挂在 `notes/today.md` → 先归档，再生成新的当天模板
