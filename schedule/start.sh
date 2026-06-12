#!/bin/bash
## 简单的启动脚本：在项目根运行后端和前端开发服务器
## 用法：在 `schedule/` 目录外可直接运行此脚本（脚本会切换到自身目录）
cd "$(dirname "$0")"
echo "Starting Schedule App..."

# 启动后端（FastAPI + Uvicorn），可选传参端口由后端处理（此脚本传 3000）
python3 backend/main.py 3000 &
BACKEND_PID=$!
echo "  Backend: http://localhost:3000 (PID: $BACKEND_PID)"
echo "  API Docs: http://localhost:3000/api/docs"

# 启动前端（Vite 开发服务器）
cd frontend
npx vite --host &
FRONTEND_PID=$!
echo "  Frontend: http://localhost:5173 (PID: $FRONTEND_PID)"

echo ""
echo "Press Ctrl+C to stop both servers."
# 捕捉中断信号，优雅停止两个子进程
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
