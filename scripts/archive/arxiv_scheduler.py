import schedule
import time
import subprocess
from pathlib import Path

# 获取当前脚本所在目录的绝对路径
SCRIPT_DIR = Path(__file__).parent.absolute()
RUN_SH = SCRIPT_DIR / "run.sh"


def job():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 正在启动 ArXiv 抓取任务...")
    try:
        subprocess.run(["/usr/bin/bash", str(RUN_SH)], cwd=str(SCRIPT_DIR), check=True)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 任务启动指令已发送")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 启动任务失败: {e}")


# 每天 08:00 运行
schedule.every().day.at("08:00").do(job)

print(f"定时任务已启动，将在每天 08:00 执行 {RUN_SH}")
# 启动时立即运行一次测试（可选，如果用户只想定时则注释掉）
# job()

while True:
    schedule.run_pending()
    time.sleep(60)  # 每分钟检查一次
