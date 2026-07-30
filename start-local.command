#!/bin/bash
# 短视频稿生成器 - 本地一键启动（零依赖版）
# 双击本文件即可：启动本地服务 + 自动打开浏览器
# macOS 自带 Python3，无需安装任何东西
# 关闭此终端窗口会停止服务

cd "$(dirname "$0")"

# 优先使用 Python（macOS 自带），备选 Node.js
USE_PYTHON=true
USE_NODE=false

if command -v python3 &> /dev/null; then
    USE_PYTHON=true
elif command -v node &> /dev/null; then
    USE_NODE=true
else
    osascript -e 'display dialog "未检测到 Python3 或 Node.js。\n\n请安装任一方案：\n1. Python: https://www.python.org/downloads/\n2. Node.js: https://nodejs.org\n\n（macOS 通常已自带 Python3，可终端运行 python3 --version 确认）" buttons {"好"} default button "好"'
    exit 1
fi

echo "========================================="
echo "  短视频稿生成器 - 本地服务启动中..."
echo "  访问地址: http://localhost:3001"
echo "  关闭此窗口即可停止服务"
echo "========================================="
echo ""

# 启动服务
if [ "$USE_PYTHON" = true ]; then
    echo "[启动方式] Python3 (server.py)"
    python3 server.py &
    SERVER_PID=$!
elif [ "$USE_NODE" = true ]; then
    echo "[启动方式] Node.js (server.js)"
    node server.js &
    SERVER_PID=$!
fi

# 等待服务就绪
sleep 2

# 打开浏览器
open http://localhost:3001

# 保持窗口打开
wait $SERVER_PID 2>/dev/null

# 如果进程意外退出，提示用户
echo ""
echo "服务已停止。如需重新启动，请再次双击本文件。"
read -p "按回车键退出..."
