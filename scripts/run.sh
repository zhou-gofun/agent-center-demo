#!/bin/bash
# Agent Center 启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR" || exit 1

# 检查虚拟环境
if [ ! -d ".venv_new" ]; then
    echo "创建虚拟环境..."
    python3 -m venv .venv_new
    .venv_new/bin/pip install -r requirements.txt
fi

# 启动服务
echo "启动 Agent Center 服务..."
echo "地址: http://localhost:8000"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

.venv_new/bin/python -m src.main
