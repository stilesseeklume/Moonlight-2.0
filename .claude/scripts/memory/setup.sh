#!/bin/bash
# 月光 Memory 一次性装环境（Mac 用）
# 大陆 friendly: 用 PyPI 清华镜像 + HuggingFace hf-mirror.com

set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "🌙 月光 memory setup 启动..."
echo "📍 工作目录: $SCRIPT_DIR"
echo

# 检查 Python
if ! command -v python3 &> /dev/null; then
  echo "❌ python3 没装。先装 Python 3.10+：brew install python@3.11"
  exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Python $PY_VERSION"

# 创建 venv（避免污染系统 python）
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
  echo "📦 创建 venv..."
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# pip 国内镜像
echo "📦 装依赖（清华镜像）..."
pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple/ -q
pip install -r "$SCRIPT_DIR/requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple/ -q

# 配置 HF 镜像（永久写入 venv 的 activate）
HF_LINE='export HF_ENDPOINT=https://hf-mirror.com'
if ! grep -q "HF_ENDPOINT" "$VENV_DIR/bin/activate"; then
  echo "" >> "$VENV_DIR/bin/activate"
  echo "$HF_LINE" >> "$VENV_DIR/bin/activate"
fi
export HF_ENDPOINT=https://hf-mirror.com

# 预下载模型（第一次跑 index.py 会自动下，但这里先下能看到进度）
echo "📥 预下载 BGE-small-zh-v1.5（约 95MB）..."
python3 -c "
from sentence_transformers import SentenceTransformer
m = SentenceTransformer('BAAI/bge-small-zh-v1.5', cache_folder='$SCRIPT_DIR/.models')
print('模型加载成功，维度:', m.get_sentence_embedding_dimension())
"

echo
echo "✅ 装完了。下一步："
echo "   cd $SCRIPT_DIR && source .venv/bin/activate && python3 index.py"
echo "   首次 index 大约 1-2 分钟（取决于 Moonlight/ 文件数量）"
