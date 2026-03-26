"""
定时任务调度系统
支持每天多次抓取（凌晨 + 中午）
"""

import asyncio
import signal
import sys
from datetime import datetime, timedelta
from typing import List, Callable, Optional
from dataclasses import dataclass
from loguru import logger

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, JobExecutionEvent


@dataclass
class FetchJobConfig:
    """抓取任务配置"""
    name: str
    subjects: List[str]                    # 抓取的 ArXiv 主题
    schedule: str                          # cron 表达式
    enabled: bool = True
    max_papers: int = 250
    description: str = ""


# 默认调度配置
DEFAULT_SCHEDULE = [
    FetchJobConfig(
        name="morning_fetch",
        subjects=["cs.AI"],
        schedule="0 8 * * *",              # 每天 8:00
        max_papers=250,
        description="早间抓取 - 获取凌晨更新的论文"
    ),
    FetchJobConfig(
        name="noon_fetch",
        subjects=["cs.AI"],
        schedule="0 14 * * *",             # 每天 14:00
        max_papers=250,
        description="午间抓取 - 获取上午更新的论文"
    ),
    FetchJobConfig(
        name="evening_fetch",
        subjects=["cs.AI", "cs.LG", "cs.CL"],
        schedule="0 20 * * *",             # 每天 20:00
        max_papers=300,
        description="晚间抓取 - 全量更新"
    ),
]


class ArxivScheduler:
    """ArXiv 定时任务调度器"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.jobs: dict = {}
        self.job_configs: List[FetchJobConfig] = []
        self._running = False
        self._callbacks: List[Callable] = []
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理 - 优雅关闭"""
        logger.info(f"收到信号 {signum}，正在关闭调度器...")
        self.stop()
        sys.exit(0)
    
    def add_callback(self, callback: Callable):
        """添加任务完成回调"""
        self._callbacks.append(callback)
    
    def _notify_callbacks(self, job_name: str, success: bool, result: dict):
        """通知回调"""
        for callback in self._callbacks:
            try:
                callback(job_name, success, result)
            except Exception as e:
                logger.error(f"回调执行失败: {e}")
    
    def _job_listener(self, event: JobExecutionEvent):
        """任务执行监听器"""
        job_id = event.job_id
        
        if event.exception:
            logger.error(f"任务 {job_id} 执行失败: {event.exception}")
            self._notify_callbacks(job_id, False, {"error": str(event.exception)})
        else:
            logger.success(f"任务 {job_id} 执行成功")
            self._notify_callbacks(job_id, True, event.retval or {})
    
    async def _fetch_task(self, config: FetchJobConfig) -> dict:
        """实际的抓取任务"""
        # from arxiv_daily_v2 import run_daily_pipeline  # broken import, removed
        
        logger.info(f"开始执行抓取任务: {config.name}")
        start_time = datetime.now()
        
        try:
            # 确定日期（如果是早上抓，可能抓昨天的）
            if "morning" in config.name:
                target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                target_date = datetime.now().strftime("%Y-%m-%d")
            
            # 运行流水线
            # NOTE: run_daily_pipeline was from the removed arxiv_daily_v2 module.
            # This needs to be replaced with the new pipeline from src.pipeline.
            raise NotImplementedError("_fetch_task: run_daily_pipeline is no longer available; update this method to use src.pipeline")
            result = None  # unreachable, kept for type checker
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                "job_name": config.name,
                "success": result.error_message is None,
                "date": target_date,
                "subjects": config.subjects,
                "total_papers": result.total_papers,
                "processed": result.processed_count,
                "duration": duration,
                "error": result.error_message
            }
            
        except Exception as e:
            logger.exception(f"抓取任务 {config.name} 异常: {e}")
            return {
                "job_name": config.name,
                "success": False,
                "error": str(e),
                "duration": (datetime.now() - start_time).total_seconds()
            }
    
    def add_job(self, config: FetchJobConfig):
        """添加定时任务"""
        if not config.enabled:
            logger.info(f"任务 {config.name} 已禁用，跳过")
            return
        
        # 解析 cron 表达式
        # 格式: minute hour day month day_of_week
        parts = config.schedule.split()
        if len(parts) != 5:
            logger.error(f"无效 cron 表达式: {config.schedule}")
            return
        
        trigger = CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4]
        )
        
        # 添加任务
        job = self.scheduler.add_job(
            func=self._fetch_task,
            trigger=trigger,
            args=[config],
            id=config.name,
            name=config.description or config.name,
            replace_existing=True,
            misfire_grace_time=3600  # 错过执行时间后 1 小时内仍可执行
        )
        
        self.jobs[config.name] = job
        self.job_configs.append(config)
        
        logger.info(f"已添加定时任务: {config.name} ({config.schedule})")
    
    def remove_job(self, job_name: str):
        """移除任务"""
        if job_name in self.jobs:
            self.scheduler.remove_job(job_name)
            del self.jobs[job_name]
            self.job_configs = [c for c in self.job_configs if c.name != job_name]
            logger.info(f"已移除任务: {job_name}")
    
    def list_jobs(self) -> List[dict]:
        """列出所有任务"""
        jobs_info = []
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time
            jobs_info.append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run.isoformat() if next_run else None,
                "trigger": str(job.trigger)
            })
        return jobs_info
    
    def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("调度器已在运行")
            return
        
        # 添加事件监听
        self.scheduler.add_listener(
            self._job_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )
        
        self.scheduler.start()
        self._running = True
        
        logger.success("定时任务调度器已启动")
        
        # 打印任务列表
        jobs = self.list_jobs()
        if jobs:
            logger.info(f"已配置 {len(jobs)} 个定时任务:")
            for job in jobs:
                logger.info(f"  - {job['name']}: {job['next_run']}")
    
    def stop(self):
        """停止调度器"""
        if not self._running:
            return
        
        self.scheduler.shutdown(wait=True)
        self._running = False
        logger.success("定时任务调度器已停止")
    
    async def run_now(self, job_name: Optional[str] = None) -> dict:
        """
        立即执行任务
        
        Args:
            job_name: 任务名称，None 则执行第一个任务
            
        Returns:
            执行结果
        """
        if job_name:
            config = next((c for c in self.job_configs if c.name == job_name), None)
            if not config:
                return {"error": f"任务 {job_name} 不存在"}
        else:
            config = self.job_configs[0] if self.job_configs else None
            if not config:
                return {"error": "没有配置任何任务"}
        
        logger.info(f"手动触发任务: {config.name}")
        return await self._fetch_task(config)
    
    def get_stats(self) -> dict:
        """获取调度器统计"""
        return {
            "running": self._running,
            "total_jobs": len(self.jobs),
            "jobs": self.list_jobs()
        }


# 全局调度器实例
_scheduler: Optional[ArxivScheduler] = None


def get_scheduler() -> ArxivScheduler:
    """获取调度器实例（单例）"""
    global _scheduler
    if _scheduler is None:
        _scheduler = ArxivScheduler()
    return _scheduler


def init_default_schedule():
    """初始化默认调度"""
    scheduler = get_scheduler()
    
    for config in DEFAULT_SCHEDULE:
        scheduler.add_job(config)
    
    return scheduler


# ==================== CLI 接口 ====================

async def main():
    """主函数 - 用于直接运行调度器"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ArXiv 定时任务调度器")
    parser.add_argument(
        "--run-now", "-r",
        help="立即执行指定任务",
        metavar="JOB_NAME"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="列出所有任务"
    )
    parser.add_argument(
        "--start",
        action="store_true",
        help="启动调度器"
    )
    
    args = parser.parse_args()
    
    scheduler = init_default_schedule()
    
    if args.list:
        jobs = scheduler.list_jobs()
        print("\n📋 定时任务列表:")
        for job in jobs:
            print(f"  [{job['id']}] {job['name']}")
            print(f"       下次执行: {job['next_run']}")
        return
    
    if args.run_now:
        result = await scheduler.run_now(args.run_now)
        print(f"\n执行结果: {result}")
        return
    
    if args.start or True:  # 默认启动
        scheduler.start()
        
        # 保持运行
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
