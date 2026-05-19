# Health 数据自动接入 — 设置步骤

> 终态：你称体重 → 月光自动看到 → 自动写进 missions/weight-loss.md + Daily Note。**你零打字。**

## 全链路

```
小米体脂秤
  ↓ (蓝牙)
小米运动健康 app
  ↓ (HealthKit 同步)
iPhone Apple Health
  ↓ (Health Auto Export)
iCloud Drive: HealthExport/HealthAutoExport-YYYY-MM-DD.csv
  ↓ (国行 iCloud → 云上贵州 → 你 Mac)
~/Library/Mobile Documents/com~apple~CloudDocs/HealthExport/
  ↓ (cron 23:30)
ingest.py
  ↓
missions/weight-loss.md + daily/2026-MM-DD.md
```

## 第一步：iPhone 端

### 1. 确认小米 → Apple Health 已通

打开「小米运动健康」app → 我的 → 隐私设置 → Apple 健康 → **打开「写入 Apple 健康」**：
- ✅ 体重
- ✅ 体脂率（可选）
- ✅ 肌肉量（可选）

### 2. 装 Health Auto Export

App Store 搜「**Health Auto Export – JSON+CSV**」（开发者：Lybron Sobers）。免费档够用——CSV 导出到 iCloud Drive 每日 1 次。

打开 app 配置：

**Automations** → **新建一个 Automation**：
- Name: `Moonlight Daily`
- Type: **CSV**
- Schedule: **Daily**, 时间设 23:00
- Aggregation: **Daily Average**（同一天多次称重取均值）
- Date Range: **Last 7 days**（保险，方便补漏）
- Metrics（选这几个，其他不要）：
  - ✅ Body Mass
  - ✅ Sleep Analysis
  - ✅ Step Count
  - （可选：Heart Rate Variability、Resting Heart Rate）
- Destination: **iCloud Drive**
  - Folder: `HealthExport`（首次会自动创建）
- File Format: **CSV**

确认 → 启动 Automation → **手动 Run Once** 验证一下生成了 CSV。

### 3. 检查 CSV 已到 Mac

```bash
ls -la "$HOME/Library/Mobile Documents/com~apple~CloudDocs/HealthExport/"
```

国行 iCloud 同步走云上贵州，**第一次可能慢 30-60 分钟**。之后每天延迟 5-30 分钟。看到 `HealthAutoExport-2026-05-XX.csv` 就 OK。

## 第二步：Mac 端跑 ingest.py

### 手动跑一次（验证）

```bash
cd /Users/zhenliu/Moonlight/.claude/scripts/health
python3 ingest.py
```

期望输出：
```
📂 最新 CSV: HealthAutoExport-2026-05-06.csv (15 分钟前)
📊 解析到 7 天数据，最新 2026-05-06
✅ missions/weight-loss.md 更新
   今日体重: 184.5 斤
✅ Daily Note 更新: daily/2026-05-06.md
✅ 同步完成
```

### 加 cron 定时跑

```bash
crontab -e
```
加入：
```
35 23 * * * cd /Users/zhenliu/Moonlight/.claude/scripts/health && /usr/bin/python3 ingest.py >> /tmp/moonlight-health.log 2>&1
```

每天 23:35（Health Auto Export 23:00 导出之后留 35 分钟同步缓冲）自动跑。

## 排错

| 症状 | 原因 | 修法 |
|---|---|---|
| `Health Export 目录不存在` | iCloud 还没同步好 / 路径错 | `ls ~/Library/Mobile\ Documents/com~apple~CloudDocs/` 看看叫什么 |
| `CSV 解析为空` | Health Auto Export 没勾 metrics | 回 app 检查 metrics 勾选 |
| 体重一直是旧值 | 小米 → Apple Health 没同步 | 打开小米运动健康，下拉刷新 |
| 国行 iCloud 同步太慢 | 云上贵州延迟 | 接受 30 分钟延迟，或改用海外 iCloud |

## 升级路径

- 把 ingest 接入 `.claude/scripts/memory/index.py` 之后跑——新数据立刻进语义索引
- 加 sleep 阈值告警：连续 3 天 < 5h → 触发 macOS 通知催睡觉
- 加体重周环比：每周日跑一次，写一段「这周比上周 ±X 斤」到 Daily Note

