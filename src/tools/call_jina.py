"""
Jina Reader API 调用工具 - 改进版
添加了重试机制、更好的错误处理和类型验证
"""

import os
import re
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

import requests
from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential, 
    retry_if_exception_type,
    before_sleep_log
)
from loguru import logger

from src.config.settings import get_settings


class JinaAPIError(Exception):
    """Jina API 自定义异常"""
    pass


class JinaRateLimitError(JinaAPIError):
    """请求频率限制异常"""
    pass


class JinaReaderClient:
    """改进版 Jina Reader API 客户端"""
    
    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.jina_api_key
        self.base_url = "https://r.jina.ai"
        self.timeout = settings.jina_timeout
        self.max_retries = settings.jina_max_retries
        
        # 请求统计
        self.request_count = 0
        self.error_count = 0
        self.last_request_time: Optional[datetime] = None
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "arXiv-AI-Agent/2.0"
        }
    
    @retry(
        retry=retry_if_exception_type((
            requests.RequestException,
            requests.Timeout,
            JinaAPIError
        )),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, "warning"),
        reraise=True
    )
    def _make_request(self, url: str) -> Dict[str, Any]:
        """执行 HTTP 请求（带重试）"""
        self.request_count += 1
        self.last_request_time = datetime.now()
        
        try:
            response = requests.post(
                url, 
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            # 处理特定状态码
            if response.status_code == 429:
                raise JinaRateLimitError("Jina API 请求频率限制")
            if response.status_code == 401:
                raise JinaAPIError("Jina API 认证失败，请检查 API Key")
            if response.status_code >= 500:
                raise JinaAPIError(f"Jina API 服务器错误: {response.status_code}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.Timeout:
            logger.warning(f"Jina API 请求超时 (attempt {self.request_count})")
            raise
        except requests.RequestException as e:
            logger.warning(f"Jina API 请求失败: {e}")
            raise
    
    def fetch_arxiv_list(
        self, 
        subject: str = "cs.AI", 
        skip: int = 0, 
        show: int = 250
    ) -> Optional[Dict[str, Any]]:
        """
        获取 ArXiv 指定主题的最新论文列表
        
        Args:
            subject: ArXiv 主题代码
            skip: 跳过的论文数量
            show: 显示的论文数量
            
        Returns:
            Jina Reader 返回的 JSON 数据
        """
        # 验证主题代码格式
        if not re.match(r'^[a-z]+\.[A-Z]+$', subject):
            logger.error(f"无效的 ArXiv 主题代码: {subject}")
            return None
        
        url = f"{self.base_url}/https://arxiv.org/list/{subject}/recent?skip={skip}&show={show}"
        logger.info(f"正在请求 Jina Reader API: subject={subject}, skip={skip}, show={show}")
        
        try:
            data = self._make_request(url)
            logger.success(f"成功获取 {subject} 的论文列表")
            return data
        except JinaRateLimitError:
            logger.error("Jina API 触发频率限制，请稍后再试")
            return None
        except Exception as e:
            self.error_count += 1
            logger.error(f"获取论文列表失败: {e}")
            return None
    
    def fetch_url(self, target_url: str) -> Optional[Dict[str, Any]]:
        """
        使用 Jina Reader 获取任意 URL 的内容
        
        Args:
            target_url: 目标 URL
            
        Returns:
            Jina Reader 返回的 JSON 数据
        """
        url = f"{self.base_url}/{target_url}"
        logger.info(f"正在获取 URL: {target_url}")
        
        try:
            return self._make_request(url)
        except Exception as e:
            self.error_count += 1
            logger.error(f"获取 URL 失败: {e}")
            return None
    
    def parse_arxiv_ids(
        self, 
        jina_response: Dict[str, Any], 
        target_date: str
    ) -> List[str]:
        """
        从 Jina Reader 响应中提取指定日期的 ArXiv ID
        
        Args:
            jina_response: Jina Reader 返回的 JSON 数据
            target_date: 目标日期字符串，格式如 "Wed, 17 Dec 2025"
            
        Returns:
            ArXiv ID 列表
        """
        if not jina_response or not isinstance(jina_response, dict):
            logger.error("无效的 Jina 响应数据")
            return []
        
        content = jina_response.get("data", {}).get("content", "")
        if not content:
            logger.error("Jina 响应中未找到 content 内容")
            return []
        
        logger.info(f"正在解析日期: {target_date}")
        
        # 尝试匹配指定日期
        ids = self._extract_ids_by_date(content, target_date)
        
        if not ids:
            logger.warning(f"未找到日期 {target_date} 的内容，尝试回退到最近日期...")
            ids = self._extract_ids_fallback(content)
        
        # 验证 ID 格式
        valid_ids = self._validate_ids(ids)
        
        logger.success(f"共提取到 {len(valid_ids)} 篇有效文献")
        return valid_ids
    
    def _extract_ids_by_date(self, content: str, target_date: str) -> List[str]:
        """按指定日期提取 ID"""
        pattern = rf"### {re.escape(target_date)}(.*?)(?=### |$)"
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            return []
        
        return self._extract_arxiv_ids_from_text(match.group(1))
    
    def _extract_ids_fallback(self, content: str) -> List[str]:
        """回退：提取第一个可用日期的内容"""
        # 寻找第一个日期块
        pattern = r"### \w+, \d+ \w+ \d{4}(.*?)(?=### |$)"
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            logger.error("未找到任何日期内容")
            return []
        
        logger.info("已回退到最近的可用日期内容")
        return self._extract_arxiv_ids_from_text(match.group(1))
    
    def _extract_arxiv_ids_from_text(self, text: str) -> List[str]:
        """从文本中提取 ArXiv ID"""
        # 匹配格式: arxiv.org/abs/2512.13510
        id_pattern = r"arxiv\.org/abs/(\d{4}\.\d{4,5}(?:v\d+)?)"
        ids = re.findall(id_pattern, text, re.IGNORECASE)
        
        # 去重并保持顺序
        seen = set()
        unique_ids = []
        for id_ in ids:
            base_id = id_.split('v')[0]  # 去除版本号
            if base_id not in seen:
                seen.add(base_id)
                unique_ids.append(base_id)
        
        return unique_ids
    
    def _validate_ids(self, ids: List[str]) -> List[str]:
        """验证 ArXiv ID 格式"""
        valid_ids = []
        pattern = re.compile(r'^\d{4}\.\d{4,5}$')
        
        for id_ in ids:
            if pattern.match(id_):
                valid_ids.append(id_)
            else:
                logger.warning(f"过滤掉无效的 ArXiv ID: {id_}")
        
        return valid_ids
    
    def get_stats(self) -> Dict[str, Any]:
        """获取请求统计信息"""
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "success_rate": (
                (self.request_count - self.error_count) / self.request_count * 100
                if self.request_count > 0 else 0
            ),
            "last_request": self.last_request_time.isoformat() if self.last_request_time else None
        }


# ==================== 快捷函数 ====================

_default_client: Optional[JinaReaderClient] = None


def get_client() -> JinaReaderClient:
    """获取默认客户端实例（单例）"""
    global _default_client
    if _default_client is None:
        _default_client = JinaReaderClient()
    return _default_client


def fetch_arxiv_papers(
    target_date: str, 
    subject: str = "cs.AI", 
    max_papers: int = 250
) -> List[str]:
    """
    快捷函数：获取指定日期和主题的 ArXiv 论文 ID 列表
    
    Args:
        target_date: 目标日期字符串
        subject: ArXiv 主题代码
        max_papers: 最多获取的论文数量
        
    Returns:
        ArXiv ID 列表
    """
    client = get_client()
    data = client.fetch_arxiv_list(subject=subject, skip=0, show=max_papers)
    
    if data:
        return client.parse_arxiv_ids(data, target_date)
    return []
