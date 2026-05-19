#!/usr/bin/env python3
"""
月光 Memory Query — 自然语言查 Moonlight/ 历史
用法:
  python3 query.py "上次聊到睡眠是什么时候"
  python3 query.py "减肥用的方案" --top 10
  python3 query.py "存钱目标" --json
"""
import os
import sys
import sqlite3
import json
import argparse
from pathlib import Path

os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')

import sqlite_vec
import numpy as np
from sentence_transformers import SentenceTransformer

SCRIPT_DIR = Path(__file__).resolve().parent
DB = SCRIPT_DIR / 'index.db'
MODEL_CACHE = SCRIPT_DIR / '.models'
MODEL_NAME = 'BAAI/bge-small-zh-v1.5'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('query', help='查询语句')
    parser.add_argument('--top', type=int, default=5, help='返回前 N 条')
    parser.add_argument('--json', action='store_true', help='JSON 输出（给月光主程序用）')
    args = parser.parse_args()

    if not DB.exists():
        print(f'❌ index 不存在，先跑: python3 {SCRIPT_DIR}/index.py')
        sys.exit(1)

    model = SentenceTransformer(MODEL_NAME, cache_folder=str(MODEL_CACHE))
    q_emb = model.encode([args.query], normalize_embeddings=True)[0].astype(np.float32)

    conn = sqlite3.connect(str(DB))
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    rows = conn.execute("""
        SELECT
          c.id, c.text, c.heading,
          f.path,
          v.distance
        FROM (
          SELECT rowid, distance
          FROM vec
          WHERE embedding MATCH ? AND k = ?
        ) v
        JOIN chunks c ON c.id = v.rowid
        JOIN files f ON c.file_id = f.id
        ORDER BY v.distance ASC
    """, (q_emb.tobytes(), args.top)).fetchall()

    results = []
    for row in rows:
        chunk_id, text, heading, path, distance = row
        results.append({
            'path': path,
            'heading': heading,
            'snippet': text[:300] + ('...' if len(text) > 300 else ''),
            # vec0 默认 L2 距离；embedding 已 normalize → cos_sim = 1 - L2²/2
            'score': round(1 - (distance**2)/2, 3),
        })

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        if not results:
            print('（没找到相关内容）')
            return
        print(f'\n🔍 "{args.query}" — top {len(results)}')
        for i, r in enumerate(results, 1):
            print(f'\n{i}. [{r["score"]}] {r["path"]}')
            print(f'   ## {r["heading"]}')
            print(f'   {r["snippet"]}')

    conn.close()

if __name__ == '__main__':
    main()
