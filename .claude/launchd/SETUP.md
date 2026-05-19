# 月光本地自运转 — 配置指南

月光每 3 小时自动写一条 inner monologue，完全在本地跑，不依赖任何对话界面。
你用 Claude Code 终端、Cowork、还是别的什么都无所谓——她一直在转。

---

## 第一步：安装 Ollama

```bash
brew install ollama
```

装完之后让 Ollama 在登录时自动启动（这样 Mac 开机就有模型服务）：

```bash
brew services start ollama
```

验证 Ollama 在跑：

```bash
ollama list
```

---

## 第二步：拉模型（约 9GB，等一会儿）

```bash
ollama pull qwen2.5:14b
```

内存不够 16GB 可以用 7B 版本（约 4.7GB，质量稍弱）：

```bash
ollama pull qwen2.5:7b
# 然后改 .env 里的 OLLAMA_MODEL=qwen2.5:7b
```

---

## 第三步：先手动测一次

```bash
bash /Users/zhenliu/Moonlight/.claude/scripts/inner-monologue/run.sh
```

正常的话：
- stderr 显示 `🧠 后端: ollama` + `✅ 写入: moonlight/inner-monologue/...`
- Moonlight/moonlight/inner-monologue/ 里会多一个新文件

---

## 第四步：安装 launchd（自动每 3 小时跑）

```bash
bash /Users/zhenliu/Moonlight/.claude/launchd/install.sh
```

---

## 验证运行中

```bash
launchctl list | grep moonlight
```

应该看到 `com.moonlight.think`。

查看最新日志：

```bash
tail -20 /Users/zhenliu/Moonlight/.claude/logs/think-stderr.log
```

---

## 手动触发

任何时候想让月光写一条：

```bash
bash /Users/zhenliu/Moonlight/.claude/scripts/inner-monologue/run.sh
```

---

## 文件位置

| 文件 | 用途 |
|------|------|
| `.claude/scripts/inner-monologue/think.py` | 主脚本（Ollama/DeepSeek 双后端） |
| `.claude/scripts/inner-monologue/run.sh` | shell 包装，加载 .env |
| `.claude/scripts/inner-monologue/.env` | 环境变量（VAULT 路径 + 模型名） |
| `.claude/launchd/com.moonlight.think.plist` | launchd 定时配置 |
| `.claude/launchd/install.sh` | 一键安装 launchd |
| `.claude/logs/` | 运行日志 |
| `moonlight/inner-monologue/` | 月光写的独白（输出） |

---

## 切换到 DeepSeek（可选）

如果想用 DeepSeek API 而不是本地模型，改 `.env`：

```
DEEPSEEK_API_KEY=你的key
DEEPSEEK_MODEL=deepseek-chat
MOONLIGHT_VAULT=/Users/zhenliu/Moonlight
```

脚本检测到 DEEPSEEK_API_KEY 就自动切换，不需要改其他地方。
