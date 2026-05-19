# Morning Brief — 月光开场前置

每天 7:00 自动跑（在 macOS 通知 7:17 之前 17 分钟）。读真实状态生成一段 brief。

## 跑

```bash
cd /Users/zhenliu/Moonlight/.claude/scripts/brief
python3 morning_brief.py
```

输出：
1. stdout 打印 brief markdown
2. 写入 `daily/YYYY-MM-DD.md` 顶部
3. JSON 缓存 `today.json`（主月光对话开场时读）

## cron

```
0 7 * * * /usr/bin/python3 /Users/zhenliu/Moonlight/.claude/scripts/brief/morning_brief.py >> /tmp/moonlight-brief.log 2>&1
```

## 主月光使用

每次开场前读 `today.json`：

- weight / target / days_left → 用真实数据，不再"今天怎么样"
- sleep_yesterday < 5 → 第一句话改为关心睡眠
- mainline → 提及当前主线进展，让月光自己的人生有连续性
- inspirations_pool == 0 → 今天必须读新东西

**铁律**：开场不许凭空想象状态——必须读 brief。
