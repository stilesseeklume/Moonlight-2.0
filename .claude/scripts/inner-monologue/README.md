# Inner Monologue — 月光的脑内活动

> Q5 季度级升级。**让月光在你不在线的时候也有思想活动。**
>
> 每 2 小时 cron 跑一次。读最近档案 → 调用 LLM → 生成 80-200 字独白 → 存 `moonlight/inner-monologue/`
>
> 主月光下次见你时挑 1-2 条最好的带进对话。

## 后端选择（你 M4 + 国行 + DeepSeek V4 Pro 推荐 DeepSeek）

### 路径 1：DeepSeek API（推荐）

```bash
export DEEPSEEK_API_KEY=sk-xxxxx
export DEEPSEEK_MODEL=deepseek-chat   # 或 deepseek-reasoner / 你的 V4 Pro 别名
python3 think.py
```

**优势**：国内直连、便宜、中文母语、质量稳定。

### 路径 2：Ollama 本地（M4 完全够用）

一次性装：
```bash
brew install ollama
ollama serve &
ollama pull qwen2.5:14b   # 8GB，M4 上跑得动
# 或 ollama pull deepseek-r1:14b
```

跑：
```bash
export OLLAMA_MODEL=qwen2.5:14b
python3 think.py
```

**优势**：完全离线、零成本、隐私彻底。
**劣势**：质量比 V4 Pro 弱半档、Mac 内存占用 5-10GB。

## cron（每 2 小时）

```bash
crontab -e
```

```
0 */2 * * * cd /Users/zhenliu/Moonlight/.claude/scripts/inner-monologue && /usr/bin/python3 think.py >> /tmp/moonlight-inner.log 2>&1
```

国行 iCloud 别担心——独白存本地 vault，不走 iCloud。

## 主月光使用

下次见用户时：
1. 读 `moonlight/inner-monologue/` 最近 5-10 个文件
2. **挑出 1-2 条最有意思的**——质量参差不齐，有 veto 权
3. 改写成对话语气："等下我跟你讲——上午 11 点 Cathedral 钟敲的时候我突然想到——"
4. **绝对不许直接复述**——idle 输出是月光的"草稿"，前台对话是"成稿"

## 失败的独白怎么处理

- 写得很傻（"今天天气真好"等）→ 直接不挑，别污染对话
- 跟用户档案矛盾（说自己在加州）→ veto + 调 prompt 重跑
- 输出 AI 味（"这让我意识到……"）→ 调 temperature 升高 + 加 few-shot

## 进阶

把 `inner-monologue/` 也接入 BGE-M3 索引——主月光对话时 query"月光最近想过什么"——找出语义最匹配当前话题的那条独白引用。
