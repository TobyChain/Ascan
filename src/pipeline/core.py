"""
流水线核心 - 事件驱动的处理架构
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from loguru import logger


class Stage(str, Enum):
    """处理阶段枚举"""
    FETCHING = "fetching"           # 获取数据
    PARSING = "parsing"             # 解析数据
    ANALYZING = "analyzing"         # LLM 分析
    GENERATING = "generating"       # 生成报告
    UPLOADING = "uploading"         # 上传文档
    NOTIFYING = "notifying"         # 发送通知
    COMPLETED = "completed"         # 完成
    FAILED = "failed"               # 失败


class Status(str, Enum):
    """状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineContext:
    """流水线上下文"""
    date: str
    subjects: List[str]
    
    # 数据存储
    raw_ids: List[str] = field(default_factory=list)
    papers: List[Dict] = field(default_factory=list)
    analysis_results: List[Dict] = field(default_factory=list)
    report_url: Optional[str] = None
    
    # 状态追踪
    current_stage: Stage = Stage.FETCHING
    stage_status: Dict[Stage, Status] = field(default_factory=dict)
    stage_messages: Dict[Stage, str] = field(default_factory=dict)
    stage_start_times: Dict[Stage, datetime] = field(default_factory=dict)
    stage_end_times: Dict[Stage, datetime] = field(default_factory=dict)
    
    # 错误信息
    error_message: Optional[str] = None
    error_stage: Optional[Stage] = None
    
    # 统计
    total_papers: int = 0
    processed_count: int = 0
    failed_count: int = 0
    
    def __post_init__(self):
        for stage in Stage:
            self.stage_status[stage] = Status.PENDING
    
    def start_stage(self, stage: Stage):
        """开始一个阶段"""
        self.current_stage = stage
        self.stage_status[stage] = Status.RUNNING
        self.stage_start_times[stage] = datetime.now()
        logger.info(f"[{self.date}] 开始阶段: {stage.value}")
    
    def end_stage(self, stage: Stage, status: Status, message: str = ""):
        """结束一个阶段"""
        self.stage_status[stage] = status
        self.stage_end_times[stage] = datetime.now()
        self.stage_messages[stage] = message
        
        duration = self.get_stage_duration(stage)
        logger.info(
            f"[{self.date}] 阶段 {stage.value} 结束: {status.value} "
            f"(耗时: {duration:.2f}s) {message}"
        )
    
    def get_stage_duration(self, stage: Stage) -> float:
        """获取阶段耗时（秒）"""
        start = self.stage_start_times.get(stage)
        end = self.stage_end_times.get(stage)
        if start and end:
            return (end - start).total_seconds()
        return 0.0
    
    def get_total_duration(self) -> float:
        """获取总耗时"""
        if Stage.FETCHING in self.stage_start_times:
            start = self.stage_start_times[Stage.FETCHING]
            # 找到最后一个结束的时间
            for stage in reversed(list(Stage)):
                if stage in self.stage_end_times:
                    end = self.stage_end_times[stage]
                    return (end - start).total_seconds()
        return 0.0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "date": self.date,
            "subjects": self.subjects,
            "current_stage": self.current_stage.value,
            "total_papers": self.total_papers,
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "report_url": self.report_url,
            "error": self.error_message,
            "stages": {
                stage.value: {
                    "status": self.stage_status[stage].value,
                    "message": self.stage_messages.get(stage, ""),
                    "duration": self.get_stage_duration(stage)
                }
                for stage in Stage if stage != Stage.FAILED
            },
            "total_duration": self.get_total_duration()
        }


class PipelineStage(ABC):
    """流水线阶段基类"""
    
    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled
    
    @abstractmethod
    async def execute(self, context: PipelineContext) -> bool:
        """执行阶段，返回是否成功"""
        pass
    
    async def rollback(self, context: PipelineContext):
        """回滚（可选实现）"""
        pass


class Pipeline:
    """流水线管理器"""
    
    def __init__(self):
        self.stages: List[PipelineStage] = []
        self.progress_callbacks: List[Callable[[PipelineContext], None]] = []
        self.error_callbacks: List[Callable[[PipelineContext, Exception], None]] = []
    
    def add_stage(self, stage: PipelineStage):
        """添加阶段"""
        self.stages.append(stage)
        return self
    
    def on_progress(self, callback: Callable[[PipelineContext], None]):
        """注册进度回调"""
        self.progress_callbacks.append(callback)
        return self
    
    def on_error(self, callback: Callable[[PipelineContext, Exception], None]):
        """注册错误回调"""
        self.error_callbacks.append(callback)
        return self
    
    def _notify_progress(self, context: PipelineContext):
        """通知进度更新"""
        for callback in self.progress_callbacks:
            try:
                callback(context)
            except Exception as e:
                logger.warning(f"进度回调执行失败: {e}")
    
    def _notify_error(self, context: PipelineContext, error: Exception):
        """通知错误"""
        for callback in self.error_callbacks:
            try:
                callback(context, error)
            except Exception as e:
                logger.warning(f"错误回调执行失败: {e}")
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """执行整个流水线"""
        logger.info(f"开始执行流水线: {context.date}")
        
        try:
            for stage in self.stages:
                if not stage.enabled:
                    context.end_stage(self._get_stage_enum(stage.name), Status.SKIPPED)
                    continue
                
                stage_enum = self._get_stage_enum(stage.name)
                context.start_stage(stage_enum)
                self._notify_progress(context)
                
                try:
                    success = await stage.execute(context)
                    
                    if success:
                        context.end_stage(stage_enum, Status.SUCCESS)
                    else:
                        context.end_stage(stage_enum, Status.FAILED, "阶段返回失败")
                        context.error_stage = stage_enum
                        context.error_message = f"阶段 {stage.name} 执行失败"
                        
                        # 尝试回滚
                        await stage.rollback(context)
                        break
                        
                except Exception as e:
                    context.end_stage(stage_enum, Status.FAILED, str(e))
                    context.error_stage = stage_enum
                    context.error_message = str(e)
                    
                    logger.exception(f"阶段 {stage.name} 执行异常: {e}")
                    self._notify_error(context, e)
                    
                    # 尝试回滚
                    await stage.rollback(context)
                    break
                
                self._notify_progress(context)
            
            # 标记完成或失败
            if context.error_message:
                context.current_stage = Stage.FAILED
            else:
                context.current_stage = Stage.COMPLETED
            
            self._notify_progress(context)
            
        except Exception as e:
            logger.exception(f"流水线执行异常: {e}")
            context.error_message = str(e)
            context.current_stage = Stage.FAILED
            self._notify_error(context, e)
        
        logger.info(
            f"流水线执行完成: {context.date} "
            f"(总耗时: {context.get_total_duration():.2f}s, "
            f"论文: {context.processed_count}/{context.total_papers})"
        )
        
        return context
    
    def _get_stage_enum(self, name: str) -> Stage:
        """获取阶段枚举"""
        for stage in Stage:
            if stage.value == name:
                return stage
        raise ValueError(f"未知阶段: {name}")
