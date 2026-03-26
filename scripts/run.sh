#!/usr/bin/env bash
# ArXiv AI Agent 启动脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# 确保日志目录存在
mkdir -p logs

# 使用 uv 运行 Python 脚本
# 如果是从 schedule.py 调用，它已经是在后台运行的，这里可以不用 nohup，
# 但保留 nohup 可以确保即使 schedule.py 崩溃，抓取任务也能完成。
nohup uv run python main.py "$@" > "./logs/arxiv_ai_agent_$(date +%Y%m%d).log" 2>&1 &
