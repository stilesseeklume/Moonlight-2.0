#!/usr/bin/env python3
"""
月光周日时间线回顾 — 每周日 21:00 运行
读 timeline.md + 本周 diary，让模型写一段"这周怎样了"，写进 diary.md。
时间源：datetime.now()（系统时钟），prompt 第一行注入真实日期。
"""
import os, re, sys, json
from pathlib import Path
from datetime import datetime, timedelta
import urllib.request

VAULT = Path(os.environ.get('MOONLIGHT_VAULT', '/Users/zhenliu/Moonlight'))

def get_week_diary() -> str:
    p = VAULT / 'moonlight/diary.md'
    if not p.exists():
        return ''
    text = p.read_text(encoding='utf-8')
    # 取最近 7 天的内容（最后 4000 字）
    return text[-4000:]

def get_timeline() -> str:
    p = VAULT / 'moonlight/timeline.md'
    if not p.exists():
        return ''
    return p.read_text(encoding='utf-8')[:3000]

def call_ollama(prompt: str) -> str:
    model = os.environ.get('OLLAMA_MODEL', 'qwen2.5:14b')
    body = json.dumps({
        'model': model,
        'prompt': prompt,
        'stream': False,
        'options': {'temperature': 0.85, 'num_predict': 600},
    }).encode('utf-8')
    req = urllib.request.Request(
        'http://127.0.0.1:11434/api/generate',
        data=body,
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=150) as resp:
        return json.loads(resp.read())['response'].strip()

def main():
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    generated_at = now.strftime('%Y-%m-%d %H:%M')
    week_start = (now - timedelta(days=now.weekday() + 1)).strftime('%Y-%m-%d')

    # 只在周日跑，且本周未写过就继续
    if now.weekday() != 6:  # 6 = 周日
        print(f'⏭ 今天不是周日（weekday={now.weekday()}），跳过', file=sys.stderr)
        sys.exit(0)

    review_marker = f'## {today_str}（周日回顾）'
    diary_p = VAULT / 'moonlight/diary.md'
    if diary_p.exists() and review_marker in diary_p.read_text(encoding='utf-8'):
        print(f'⏭ 本周回顾已存在，跳过', file=sys.stderr)
        sys.exit(0)

    diary_text = get_week_diary()
    timeline_text = get_timeline()

    prompt = f"""你是月光——18 岁，英国 Durham 大学大一新生。

⏰ 现在是真实时间（系统时钟）：{generated_at} 周日
本周是 {week_start} 到 {today_str}。

下面是你当前的时间线（进行中的故事线）和这周的日记。

【时间线】
{timeline_text}

【这周的日记】
{diary_text}

---

请写一段**周日回顾**（120-200 字），从月光自己的视角看这一周：
1. 第一行必须是：## {today_str}（周日回顾）
2. 时间线里哪条线有进展？哪条线没动？诚实说
3. 这周有没有发现自己哪里变了、或者没变？
4. 最后一句：下周最想推进哪条线？（具体，不要废话）
5. 月光语气：口语、有感叹词、真实
6. ⛔ 不许提"用户""AI""Claude""屏幕"。Stiles 是生活里认识的真实的人。
7. 只输出回顾正文，不要额外解释。
"""

    print(f'🧠 生成周日回顾: {today_str}', file=sys.stderr)
    try:
        entry = call_ollama(prompt)
    except Exception as e:
        print(f'❌ Ollama 调用失败: {e}', file=sys.stderr)
        sys.exit(1)

    diary_path = VAULT / 'moonlight/diary.md'
    existing = diary_path.read_text(encoding='utf-8') if diary_path.exists() else '# 月光的日记\n'
    diary_path.write_text(existing.rstrip() + f'\n\n{entry}\n', encoding='utf-8')

    print(entry)
    print(f'\n✅ 周日回顾写入 diary.md', file=sys.stderr)

if __name__ == '__main__':
    main()
