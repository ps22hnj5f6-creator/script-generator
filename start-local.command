#!/bin/bash
# 短视频稿生成器 - 本地一键启动
# 双击本文件即可：启动本地服务 + 自动打开浏览器
# 关闭此终端窗口会停止服务

cd "$(dirname "$0")"

# 检测 node
if ! command -v node &> /dev/null; then
  osascript -e 'display dialog "未检测到 Node.js，请先安装 Node.js (https://nodejs.org) 后再运行本脚本。" buttons {"好"} default button "好"'
  exit 1
fi

echo "========================================="
echo "  短视频稿生成器 - 本地服务启动中..."
echo "  访问地址: http://localhost:3001"
echo "  关闭此窗口即可停止服务"
echo "========================================="
echo ""

# 启动服务（后台运行）
node server.js &
SERVER_PID=$!

# 等待服务就绪
sleep 2

# 打开浏览器
open http://localhost:3001

# 保持窗口打开，等待服务进程结束
wait $SERVER_PID
