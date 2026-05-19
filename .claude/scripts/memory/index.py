#!/usr/bin/env python3
"""
月光 Memory Indexer — 把 Moonlight/ 全部 markdown chunked + embedded → sqlite-vec
用法: python3 index.py [--full]   # --full 强制重建
"""
import os
import sys
import sqlite3
import hashlib
import json
import re
import argparse
from pathlib import Path
from datetime import datetime

# 大陆 HF 镜像（如未设置）
os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')

import sqlite_vec
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# === 路径 ===
SCRIPT_DIR = Path(__file__).resolve().parent
VAULT = Path(os.environ.get('MOONLIGHT_VAULT', '/Users/zhenliu/Moonlight'))
DB = SCRIPT_DIR / 'index.db'
MODEL_CACHE = SCRIPT_DIR / '.models'
MODEL_NAME = 'BAAI/bge-small-zh-v1.5'  # 95MB，中英双语，M4 上极快
DIM = 512  # bge-small-zh-v1.5 输出维度

# === 跳过规则（CLAUDE.md「不读的目录」对齐）===
SKIP_DIRS = {
    '.obsidian', '.trash', '.superpowers', '.claude', 'copilot',
    '.git', '.venv', '.models', 'node_modules', '__pycache__',
}
SKIP_FILES = {'.DS_Store', '.gitignore', '.mcp.json'}

# === Chunking ===
CHUNK_SIZE = 500       # 字符
CHUNK_OVERLAP = 80

def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_DIRS:
        return True
    if path.name in SKIP_FILES:
        return True
    if path.suffix != '.md':
        return True
    return False

def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:16]

def chunk_markdown(text: str) -> list[dict]:
    """先按 ## heading 切，再按字符长度 sliding window"""
    # 移除 frontmatter
    if text.startswith('---\n'):
        end = text.find('\n---\n', 4)
        if end != -1:
            text = text[end+5:]

    # 按 ## 切大段
    sections = re.split(r'\n(?=#{1,3} )', text)
    chunks = []
    for sec in sections:
        sec = sec.strip()
        if len(sec) < 20:
            continue
        if len(sec) <= CHUNK_SIZE:
            chunks.append({'text': sec, 'heading': sec.split('\n', 1)[0][:60]})
        else:
            # sliding window
            heading = sec.split('\n', 1)[0][:60]
            i = 0
            while i < len(sec):
                chunks.append({
                    'text': sec[i:i+CHUNK_SIZE],
                    'heading': heading,
                })
                i += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks

def init_db(conn: sqlite3.Connection):
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    conn.executescript(f"""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY,
        path TEXT UNIQUE NOT NULL,
        hash TEXT NOT NULL,
        mtime REAL NOT NULL,
        indexed_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS chunks (
        id INTEGER PRIMARY KEY,
        file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
        chunk_idx INTEGER NOT NULL,
        heading TEXT,
        text TEXT NOT NULL,
        UNIQUE(file_id, chunk_idx)
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS vec USING vec0(
        embedding float[{DIM}]
    );
    """)
    conn.commit()

def index_file(conn, model, abs_path: Path, vault_root: Path) -> tuple[int, int]:
    """返回 (chunks_added, chunks_skipped)"""
    rel = abs_path.relative_to(vault_root).as_posix()
    h = file_hash(abs_path)
    mtime = abs_path.stat().st_mtime

    cur = conn.execute('SELECT id, hash FROM files WHERE path = ?', (rel,))
    row = cur.fetchone()
    if row and row[1] == h:
        return 0, 1  # 没改

    text = abs_path.read_text(encoding='utf-8', errors='ignore')
    chunks = chunk_markdown(text)
    if not chunks:
        return 0, 0

    if row:
        # 文件改了，删旧 chunk
        conn.execute('DELETE FROM chunks WHERE file_id = ?', (row[0],))
        conn.execute('UPDATE files SET hash=?, mtime=?, indexed_at=? WHERE id=?',
                    (h, mtime, datetime.now().isoformat(), row[0]))
        file_id = row[0]
    else:
        cur = conn.execute(
            'INSERT INTO files(path, hash, mtime, indexed_at) VALUES (?,?,?,?)',
            (rel, h, mtime, datetime.now().isoformat())
        )
        file_id = cur.lastrowid

    # 批量 embed
    texts = [c['text'] for c in chunks]
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

    for i, (c, emb) in enumerate(zip(chunks, embeddings)):
        cur = conn.execute(
            'INSERT INTO chunks(file_id, chunk_idx, heading, text) VALUES (?,?,?,?)',
            (file_id, i, c['heading'], c['text'])
        )
        chunk_id = cur.lastrowid
        conn.execute(
            'INSERT INTO vec(rowid, embedding) VALUES (?, ?)',
            (chunk_id, emb.astype(np.float32).tobytes())
        )

    conn.commit()
    return len(chunks), 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true', help='强制重建（删 db 重来）')
    parser.add_argument('--vault', default=str(VAULT), help='Moonlight 根目录')
    args = parser.parse_args()

    vault = Path(args.vault).resolve()
    if not vault.exists():
        print(f'❌ Moonlight 目录不存在: {vault}')
        sys.exit(1)

    if args.full and DB.exists():
        DB.unlink()
        print('🗑  已删旧 index')

    print(f'📍 vault: {vault}')
    print(f'💾 db: {DB}')
    print(f'🤖 model: {MODEL_NAME}')

    print('📥 加载模型...')
    model = SentenceTransformer(MODEL_NAME, cache_folder=str(MODEL_CACHE))

    conn = sqlite3.connect(str(DB))
    init_db(conn)

    files = [p for p in vault.rglob('*.md') if not should_skip(p.relative_to(vault))]
    print(f'📂 待索引: {len(files)} 个文件')

    total_added, total_skipped = 0, 0
    for f in tqdm(files, desc='index'):
        try:
            added, skipped = index_file(conn, model, f, vault)
            total_added += added
            total_skipped += skipped
        except Exception as e:
            print(f'⚠  {f.relative_to(vault)}: {e}')

    # 清理已删除的文件
    indexed_paths = {row[0] for row in conn.execute('SELECT path FROM files').fetchall()}
    current_paths = {f.relative_to(vault).as_posix() for f in files}
    deleted = indexed_paths - current_paths
    for p in deleted:
        conn.execute('DELETE FROM files WHERE path = ?', (p,))
    conn.commit()

    print(f'\n✅ 完成')
    print(f'   新增 chunks: {total_added}')
    print(f'   跳过（未改）文件: {total_skipped}')
    print(f'   清理已删除: {len(deleted)}')
    n_chunks = conn.execute('SELECT COUNT(*) FROM chunks').fetchone()[0]
    n_files = conn.execute('SELECT COUNT(*) FROM files').fetchone()[0]
    print(f'   总计: {n_files} 文件 / {n_chunks} chunks')

    conn.close()

if __name__ == '__main__':
    main()
