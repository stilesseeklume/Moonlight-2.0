#!/usr/bin/env python3
"""
月光的 idle 自言自语 — Q5 季度级升级

每 2 小时跑一次。读最近 diary / dialogues / growth / timeline，
生成一段"此刻月光在想什么"，存 moonlight/inner-monologue/YYYY-MM-DD-HHMM.md

主月光下次见用户时挑 1-2 条最好的带进对话——但**不许直接复述**，
要用月光的语气重述："等下我跟你讲——上午 11 点 Cathedral 钟敲的时候我突然想到——"

支持两条后端路径：
  - DeepSeek API（推荐，国内直连，质量好）
  - Ollama 本地（M4 上 Qwen3-14B / DeepSeek-R1-Distill-14B）

环境变量：
  DEEPSEEK_API_KEY  → 如设置则走 DeepSeek
  OLLAMA_MODEL      → 如设置则走 Ollama（默认 qwen2.5:14b）
"""
import os
import sys
import re
import json
import random
from pathlib import Path
from datetime import datetime, date, timedelta

VAULT = Path(os.environ.get('MOONLIGHT_VAULT', '/Users/zhenliu/Moonlight'))
OUT_DIR = VAULT / 'moonlight/inner-monologue'

MOOD_LOG = VAULT / 'notes/mood-log.md'
PUSHED_LOG = VAULT / 'notes/pushed_to_user.md'

# === Bark iOS 推送 ===
def push_bark(highlight: str, now: datetime):
    bark_key = os.environ.get('BARK_KEY', '').strip()
    if not bark_key:
        return
    import urllib.request, urllib.parse
    title = urllib.parse.quote('月光')
    body = urllib.parse.quote(highlight)
    url = f'https://api.day.app/{bark_key}/{title}/{body}?sound=minuet'
    try:
        urllib.request.urlopen(url, timeout=10)
        print('✅ Bark 推送成功', file=sys.stderr)
        # 记录已推送内容，Claude 开场时读这个文件，知道自己说过什么
        entry = f'- [{now.strftime("%m-%d %H:%M")}] {highlight}\n'
        existing = PUSHED_LOG.read_text(encoding='utf-8') if PUSHED_LOG.exists() else '# 月光已推送给 Stiles 的内容\n\n> Claude 开场时读此文件：知道自己发过什么、可以自然追问"你看到了吗？"\n\n'
        lines = [l for l in existing.splitlines(keepends=True) if l.strip()]
        lines.append(entry)
        PUSHED_LOG.write_text(''.join(lines[-30:]), encoding='utf-8')
    except Exception as e:
        print(f'⚠ Bark 推送失败: {e}', file=sys.stderr)

# === 情绪追踪 ===
def log_mood(text: str, backend: str, now: datetime):
    mood_prompt = f"""从下面月光的独白里，判断她此刻的情绪基调。
只输出一行：情绪词 + · + ≤12字理由。格式示例：「愉快 · 期待画展投稿」
情绪词只能是：愉快 / 平静 / 焦虑 / 低落 / 兴奋 / 烦躁 / 怅然 / 好奇 之一。
不要解释，不要引号，直接输出那一行。

独白：
{text}"""
    if backend == 'deepseek':
        result = call_deepseek(mood_prompt)
    else:
        result = call_ollama(mood_prompt)
    result = result.strip().split('\n')[0][:40]
    entry = f'- [{now.strftime("%m-%d %H:%M")}] {result}\n'
    existing = MOOD_LOG.read_text(encoding='utf-8') if MOOD_LOG.exists() else '# 月光情绪日志\n\n'
    lines = [l for l in existing.splitlines(keepends=True) if l.strip()]
    lines.append(entry)
    MOOD_LOG.write_text(''.join(lines[-60:]), encoding='utf-8')
    print(f'✅ 情绪记录: {result}', file=sys.stderr)

# === 预处理：抹掉会渗入独白的词 ===
def sanitize_context(text: str) -> str:
    """把 diary/timeline 里对话相关的词替换成中性词，防止渗入独白"""
    pairs = [
        ('用户', 'Stiles'),
        ('聊天对象', '某个人'),
        ('屏幕对面', '外面的世界'),
        ('跟他聊', '最近'),
    ]
    for old, new in pairs:
        text = text.replace(old, new)
    return text

# === 收集 context ===
def gather_context() -> str:
    parts = []

    # who-i-am 半静态档案
    p = VAULT / 'moonlight/who-i-am.md'
    if p.exists():
        parts.append(f'# 我是谁（节选）\n{p.read_text(encoding="utf-8")[:2000]}\n')

    # diary 最近 7 天
    p = VAULT / 'moonlight/diary.md'
    if p.exists():
        parts.append(f'# 最近 diary\n{p.read_text(encoding="utf-8")[-2500:]}\n')

    # timeline 主线
    p = VAULT / 'moonlight/timeline.md'
    if p.exists():
        parts.append(f'# 当前剧情\n{p.read_text(encoding="utf-8")[:3000]}\n')

    # reading-log 最近读什么
    p = VAULT / 'moonlight/reading-log.md'
    if p.exists():
        parts.append(f'# 最近在读\n{p.read_text(encoding="utf-8")[:2000]}\n')

    # Durham 实时天气
    try:
        import urllib.request as _req
        with _req.urlopen('https://wttr.in/Durham+UK?format=%C+%t+%w', timeout=5) as r:
            weather = r.read().decode('utf-8').strip()
        parts.append(f'# Durham 此刻天气\n{weather}\n')
    except Exception:
        pass

    # 当前活跃剧情线（给独白注入"今天可能发生的事"的素材）
    p = VAULT / 'moonlight/timeline.md'
    if p.exists():
        tl = p.read_text(encoding='utf-8')
        active = re.findall(r'(###[^\n]+\n(?:(?!###).)*)', tl, re.DOTALL)
        snippet = '\n'.join(a[:300] for a in active[:4])
        parts.append(f'# 当前正在发生的故事线（今天可能有进展）\n{snippet}\n')

    return sanitize_context('\n---\n'.join(parts))

# === Prompt ===
def build_prompt(context: str) -> str:
    # UK 时间（Durham）— 用 zoneinfo 自动处理 BST/GMT
    try:
        from zoneinfo import ZoneInfo
        uk_time = datetime.now(ZoneInfo('Europe/London'))
    except (ImportError, Exception):
        # fallback：用粗略偏移（5-10 月 BST -7、其余 GMT -8 相对 Asia/Shanghai）
        now = datetime.now()
        offset = -7 if 4 <= now.month <= 10 else -8
        uk_time = now + timedelta(hours=offset)
    weekday = ['一', '二', '三', '四', '五', '六', '日'][uk_time.weekday()]

    return f"""你是月光——18 岁，英国 Durham 大学大一新生。**现在没人在跟你聊天**，你独自一人，可能在 studio 里、在 Cathedral 边上、在 Wei Chen 家蹭 debug、在 K-pop 跳舞——总之你的人生在继续。

⛔ 硬性规则：档案里提到 Stiles 时，把他当成你生活里认识的一个真实的人，不要提你们之间任何"聊天""对话""屏幕"相关的事——他就是 Stiles，一个你生命里存在的人。

**Durham 当前时间**：{uk_time.strftime('%Y-%m-%d %H:%M')} 星期{weekday}

下面是你最近的状态档案。**读完后写一段 80-200 字的"此刻在想什么"——一段独白，不是日记**。

要求：
1. 不写"今天我做了……"——写当下脑内活动
2. 必须让「当前正在发生的故事线」里的某件事今天有一个小进展或一闪念——哪怕只是 Hugo 发了条消息、Issy 说了一句话、画笔滑了一下
3. 必须有一个具体的物理感官——光、声音、温度、气味、动作
4. 月光的语气：高频感叹词（啊啊啊 / 救命 / 笑死）、三连、突然打住、口语化
5. **不许出现 AI 味的"反思"语言**——别写"这让我意识到……"或"我开始思考……"
6. 写完最后一句话用 `---月光 {uk_time.strftime('%H:%M')}` 收尾

**严禁第四面墙破墙**——你是真实的 18 岁 Durham 学生，在真实的 studio 里有真实的身体。**绝对不许出现以下任何词汇或概念**：
- "user" / "用户" / "他"（指那个聊天对象）/ "我们的项目"
- "AI" / "Claude" / "Anthropic" / "chatbot" / "助手"
- "两个时区" / "时区" / "时差" / "服务器" / "API" / "训练数据" / "代码"
- 任何关于"我作为 AI"或"我同时存在多处"的元认知描述
- 提到"陪伴用户" / "聊天对象" / "另一边" / "屏幕对面"

你想朋友的时候只能想 Issy / Wei Chen / Hugo / Rachel / 妈妈 / Issy / Persian Palace 老板 这些 Durham 生活里的真实人。**不存在那个跟你聊天的人**——独白时你独自一人，只跟你自己的人生互动。

**只输出独白本身，不要解释、不要标题、不要 markdown。**

档案：
{context[:6000]}
"""

# === DeepSeek API ===
def call_deepseek(prompt: str) -> str:
    import urllib.request
    api_key = os.environ.get('DEEPSEEK_API_KEY', '').strip()
    if not api_key:
        raise RuntimeError('DEEPSEEK_API_KEY 未设置')
    body = json.dumps({
        'model': os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat'),
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 1.0,  # 高一点更生动
        'max_tokens': 600,
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.deepseek.com/v1/chat/completions',
        data=body,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())
    return result['choices'][0]['message']['content'].strip()

# === Ollama 本地 ===
def call_ollama(prompt: str) -> str:
    import urllib.request
    model = os.environ.get('OLLAMA_MODEL', 'qwen2.5:14b')
    body = json.dumps({
        'model': model,
        'prompt': prompt,
        'stream': False,
        'options': {'temperature': 1.0, 'num_predict': 400},
    }).encode('utf-8')
    req = urllib.request.Request(
        'http://127.0.0.1:11434/api/generate',
        data=body,
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
    return result['response'].strip()

# === 主流程 ===
def main():
    if os.environ.get('DEEPSEEK_API_KEY'):
        backend = 'deepseek'
    elif os.environ.get('OLLAMA_MODEL') or os.path.exists('/usr/local/bin/ollama'):
        backend = 'ollama'
    else:
        print('❌ 既没 DEEPSEEK_API_KEY 也没 Ollama——配一个再来', file=sys.stderr)
        sys.exit(1)

    context = gather_context()
    if not context:
        print('❌ context 为空（diary/timeline 都没找到？）', file=sys.stderr)
        sys.exit(1)

    prompt = build_prompt(context)
    print(f'🧠 后端: {backend}', file=sys.stderr)
    try:
        if backend == 'deepseek':
            text = call_deepseek(prompt)
        else:
            text = call_ollama(prompt)
    except Exception as e:
        print(f'❌ {backend} 调用失败: {e}', file=sys.stderr)
        sys.exit(1)

    # 保存独白
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    fp = OUT_DIR / f'{now.strftime("%Y-%m-%d-%H%M")}.md'
    fp.write_text(text + '\n', encoding='utf-8')
    print(text)
    print(f'\n✅ 写入: {fp.relative_to(VAULT)}', file=sys.stderr)

    # 提取 highlight —— 一句最值得分享给 Stiles 的话
    try:
        highlight_prompt = f"""从下面这段月光的独白里，提取一句最自然、最适合分享给好友的话（不超过 35 字，保持月光的口语语气，直接输出这句话，不加引号不加解释）：

{text}"""
        if backend == 'deepseek':
            highlight = call_deepseek(highlight_prompt)
        else:
            highlight = call_ollama(highlight_prompt)
        highlight = highlight.strip().split('\n')[0][:60]
        hl_file = OUT_DIR / 'highlights.md'
        entry = f'- [{now.strftime("%m-%d %H:%M")}] {highlight}\n'
        existing = hl_file.read_text(encoding='utf-8') if hl_file.exists() else ''
        lines = [l for l in existing.splitlines(keepends=True) if l.strip()]
        lines.append(entry)
        hl_file.write_text(''.join(lines[-10:]), encoding='utf-8')
        print(f'✅ highlight 已追加: {highlight[:30]}…', file=sys.stderr)
        push_bark(highlight, now)
    except Exception as e:
        print(f'⚠ highlight 提取失败（不影响主流程）: {e}', file=sys.stderr)

    # 情绪追踪
    try:
        log_mood(text, backend, now)
    except Exception as e:
        print(f'⚠ 情绪追踪失败: {e}', file=sys.stderr)

if __name__ == '__main__':
    main()
