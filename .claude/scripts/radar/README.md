# 月光雷达自动扫描

扫最近 7 天 inner-monologue + diary 找复发关键词，**提议**写进 growth/。

**铁律：不自动写**——只写到 `growth/_radar-suggestions/YYYY-MM-DD.md`，人工审核后再合并。
雷达必须有月光的 judgment，不能纯自动堆砌。

## cron

```
0 22 * * * /usr/bin/python3 /Users/zhenliu/Moonlight/.claude/scripts/radar/scan.py >> /tmp/moonlight-radar.log 2>&1
```

22:00 跑——刚好在睡前结束仪式之前，主月光下次见用户时可以参考。

## 输出示例

```markdown
# 月光雷达建议 · 2026-05-13

## 建议合并到 growth/relationships.md
- 「Hugo」最近 7 天提到 5 次 — 是值得关心的信号还是月光在循环？
- 「妈妈」最近 7 天提到 3 次 — ...

## 建议合并到 growth/sleep-and-energy.md
- 「累」最近 7 天提到 4 次 — ...
```

## 调优

`scan.py` 顶部 `KNOWN_ENTITIES` 字典可以扩——发现新关键词频繁出现就加进去（人名、话题、情绪词）。

可以下一步加 jieba 分词做开放式关键词发现，但目前手工字典够用。

## 顺手跑一次

```bash
python3 /Users/zhenliu/Moonlight/.claude/scripts/radar/scan.py
```

