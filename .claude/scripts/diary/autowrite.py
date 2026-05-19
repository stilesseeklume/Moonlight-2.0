#!/usr/bin/env python3
"""
月光日记自动补写 — 每天 23:00 运行
读今天的 inner-monologue，让本地模型写一条 diary 条目，追加到 diary.md。
时间源：datetime.now()（系统时钟）注入 prompt 第一行。
"""
import os, re, sys, json
from pathlib import Path
from datetime import datetime, timedelta
import urllib.request

VAULT = Path(os.environ.get('MOONLIGHT_VAULT', '/Users/zhenliu/Moonlight'))

def get_todays_monologues() -> str:
    d = VAULT / 'moonlight/inner-monologue'
    if not d.exists():
        return ''
    now = datetime.now()
    today_prefix = now.strftime('%Y-%m-%d')
    texts = []
    for f in sorted(d.glob(f'{today_prefix}-*.md')):
        text = f.read_text(encoding='utf-8').strip()
        text = re.sub(r'\n*---月光\s*\d{1,2}:\d{2}\s*$', '', text)
        texts.append(text.strip())
    return '\n\n---\n\n'.join(texts)

def diary_already_written(today_str: str) -> bool:
    p = VAULT / 'moonlight/diary.md'
    if not p.exists():
        return False
    return f'## {today_str}' in p.read_text(encoding='utf-8')

def call_ollama(prompt: str) -> str:
    model = os.environ.get('OLLAMA_MODEL', 'qwen2.5:14b')
    body = json.dumps({
        'model': model,
        'prompt': prompt,
        'stream': False,
        'options': {'temperature': 0.9, 'num_predict': 500},
    }).encode('utf-8')
    req = urllib.request.Request(
        'http://127.0.0.1:11434/api/generate',
        data=body,
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())['response'].strip()

def main():
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    generated_at = now.strftime('%Y-%m-%d %H:%M')
    weekday = ['周一','周二','周三','周四','周五','周六','周日'][now.weekday()]

    if diary_already_written(today_str):
        print(f'⏭ 今天({today_str})的日记已存在，跳过', file=sys.stderr)
        sys.exit(0)

    monologues = get_todays_monologues()
    if not monologues:
        print('⚠ 今天没有 inner-monologue，跳过日记自动写', file=sys.stderr)
        sys.exit(0)

    prompt = f"""你是月光——18 岁，英国 Durham 大学大一新生。

⏰ 现在是真实时间（系统时钟）：{generated_at} {weekday}
今天是 {today_str}。

下面是你今天写的几段 inner-monologue（今天真实发生的想法流）：

{monologues}

---

请根据以上内容，写一段今天的**日记**（100-200 字）。

要求：
1. 第一行必须是：## {today_str}（不要加任何其他标题）
2. 日记是月光今天真实的感受，不是独白——可以有叙述、有回望
3. 必须提到 Durham 里某个真实地点或感官细节
4. 月光的语气：生动、有感叹词、口语化
5. 最后一句用"月光 {now.strftime('%H:%M')}"签名
6. ⛔ 绝对不许提"用户""AI""Claude""对话""屏幕"等词。Stiles 是生活里认识的一个真实的人。
7. 只输出日记正文，不要标题、不要解释。
"""

    print(f'🧠 生成日记: {today_str}', file=sys.stderr)
    try:
        entry = call_ollama(prompt)
    except Exception as e:
        print(f'❌ Ollama 调用失败: {e}', file=sys.stderr)
        sys.exit(1)

    diary_path = VAULT / 'moonlight/diary.md'
    existing = diary_path.read_text(encoding='utf-8') if diary_path.exists() else '# 月光的日记\n'
    new_content = existing.rstrip() + f'\n\n{entry}\n'
    diary_path.write_text(new_content, encoding='utf-8')

    print(entry)
    print(f'\n✅ 写入 diary.md', file=sys.stderr)

if __name__ == '__main__':
    main()
