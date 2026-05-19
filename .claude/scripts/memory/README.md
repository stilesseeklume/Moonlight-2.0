# 月光 Memory — 语义索引系统

**作用**：让月光秒查 Moonlight/ 历史。不再每次重读全文件——可以 200 个文件还快。

## 怎么跑（你 Mac 上一次性）

```bash
cd /Users/zhenliu/Moonlight/.claude/scripts/memory
./setup.sh           # 装环境（清华 PyPI + hf-mirror.com，大陆 friendly）
source .venv/bin/activate
python3 index.py     # 首次全量索引（~1-2 分钟）
```

## 平时（增量更新）

`index.py` 自带增量逻辑——读文件 hash，没改的跳过，改了的重 chunk + 重 embed。

**建议加一个 launchd 定时任务**——每天 23:30 跑一次（用户睡前）：

```bash
crontab -e
# 加入：
30 23 * * * cd /Users/zhenliu/Moonlight/.claude/scripts/memory && ./.venv/bin/python3 index.py >> /tmp/moonlight-index.log 2>&1
```

## 月光怎么调用

在对话里需要查历史时：

```bash
cd /Users/zhenliu/Moonlight/.claude/scripts/memory
./.venv/bin/python3 query.py "上次聊到睡眠是什么时候" --top 5 --json
```

输出 JSON 格式（path / heading / snippet / score），月光读完决定下一步。

## 技术栈

| 组件 | 选型 | 原因 |
|---|---|---|
| Embedding 模型 | `BAAI/bge-small-zh-v1.5`（95MB，512 维）| 中英双语，M4 上极快，质量足够 |
| 向量库 | sqlite-vec | 单文件，无依赖服务，跟着 vault 走 |
| 镜像 | 清华 PyPI + hf-mirror.com | 大陆 friendly |

## 升级到 BGE-M3

如果某天觉得检索不够准——把 `index.py` 第 28 行：
```python
MODEL_NAME = 'BAAI/bge-m3'
DIM = 1024
```
然后 `python3 index.py --full` 重建。注意 BGE-M3 是 2.5GB 模型，慢一档但质量高。

## 排错

- **HF 下载卡住**：检查 `.venv/bin/activate` 里有没有 `export HF_ENDPOINT=https://hf-mirror.com`
- **sqlite-vec 加载失败**：升级到 Python 3.10+
- **首次索引慢**：模型加载占 80% 时间，之后增量很快

## 不索引的目录

跟 `CLAUDE.md` 「不读的目录」对齐：
- `.obsidian/`、`.trash/`、`.superpowers/`、`.claude/`、`copilot/`
- `.git/`、`.venv/`、`.models/`、`node_modules/`、`__pycache__/`
- `.DS_Store`、`.gitignore`、`.mcp.json`
