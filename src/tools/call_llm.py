"""
大模型调用工具 - 改进版
添加了 Pydantic 验证、重试机制、更好的错误处理
"""

import os
import json
import re
from typing import Optional, Dict, Any, List

from openai import OpenAI, APIError, RateLimitError, APITimeoutError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from loguru import logger

from src.config.settings import get_settings
from src.models.schemas import PaperAnalysis


class LLMClient:
    """改进版 LLM 客户端"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        base_url: Optional[str] = None, 
        model: Optional[str] = None
    ):
        settings = get_settings()
        self.api_key = api_key or settings.api_key
        self.base_url = base_url or settings.base_url
        self.model = model or settings.model_name
        self.timeout = settings.llm_timeout
        self.max_retries = settings.llm_max_retries
        
        self.client = OpenAI(
            api_key=self.api_key, 
            base_url=self.base_url,
            timeout=self.timeout
        )
        
        # 统计
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
    
    def _clean_json_response(self, content: str) -> str:
        """清理 LLM 返回的 JSON 字符串"""
        content = content.strip()
        
        # 移除 Markdown 代码块标记
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        
        if content.endswith("```"):
            content = content[:-3]
        
        # 尝试找到 JSON 对象
        # 匹配最外层的花括号
        match = re.search(r'\{[\s\S]*\}', content)
        if match:
            content = match.group(0)
        
        return content.strip()
    
    def _create_analysis_prompt(self, title: str, abstract: str) -> str:
        """创建分析 Prompt"""
        settings = get_settings()
        
        # 构建推荐标准说明
        high_priority = ", ".join(settings.high_priority_keywords[:5])
        top_institutions = ", ".join(settings.top_institutions[:6])
        
        prompt = f"""你是一个专业的学术助手。请分析以下计算机科学论文的标题和摘要，并提供结构化分析。

【论文信息】
标题: {title}
摘要: {abstract}

【分析要求】
1. 中文摘要：将英文摘要翻译成通顺、专业的中文（保留学术术语的准确性）
2. 中文压缩：基于摘要内容，输出2-3句话的高度凝练版本（包含：研究问题、核心方法、主要贡献）
3. 关键词：提取3-5个能概括论文核心内容的中文关键词
4. 子主题：识别该论文所属的具体细分领域（如：LLM、Multi-Agent、RAG、CV、NLP、RL等）
5. 推荐程度：评估该论文的推荐等级

【推荐标准】
- 极度推荐：涉及高优先级方向（{high_priority}...），或来自头部机构（{top_institutions}...）
- 很推荐：方法创新性强、实验充分、对当前研究有重要参考价值
- 推荐：质量良好，有一定参考价值
- 一般推荐：内容较常规，参考价值有限
- 不推荐：质量较低或与主流研究关联不大

【输出格式】
必须严格按以下 JSON 格式输出，不要有任何额外文字：
{{
  "trans_abs": "中文摘要内容",
  "compressed": "2-3句话的凝练版本",
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "sub_topic": "子主题",
  "recommendation": "推荐程度"
}}
"""
        return prompt
    
    @retry(
        retry=retry_if_exception_type((
            RateLimitError,
            APITimeoutError,
            APIError
        )),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=20),
        before_sleep=before_sleep_log(logger, "warning"),
        reraise=True
    )
    def _call_api(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        """调用 LLM API（带重试）"""
        self.request_count += 1
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"}  # 强制 JSON 输出（如果模型支持）
            )
            
            content = response.choices[0].message.content
            self.success_count += 1
            return content
            
        except RateLimitError:
            logger.warning("LLM API 触发频率限制，准备重试...")
            raise
        except APITimeoutError:
            logger.warning("LLM API 请求超时，准备重试...")
            raise
        except APIError as e:
            logger.warning(f"LLM API 错误: {e}")
            raise
    
    def analyze_paper(self, title: str, abstract: str) -> PaperAnalysis:
        """
        分析论文并返回结构化结果
        
        Args:
            title: 论文标题
            abstract: 论文摘要
            
        Returns:
            PaperAnalysis 对象
        """
        prompt = self._create_analysis_prompt(title, abstract)
        
        messages = [
            {
                "role": "system",
                "content": "You are a professional academic assistant. Analyze papers accurately and output valid JSON only."
            },
            {"role": "user", "content": prompt}
        ]
        
        try:
            content = self._call_api(messages, temperature=0.3)
            content = self._clean_json_response(content)
            
            # 尝试解析 JSON
            data = json.loads(content)
            
            # 使用 Pydantic 验证
            analysis = PaperAnalysis.model_validate(data)
            return analysis
            
        except json.JSONDecodeError as e:
            self.error_count += 1
            logger.error(f"JSON 解析失败: {e}\n原始内容: {content[:200]}...")
            return self._create_fallback_analysis(title, abstract)
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"论文分析失败: {e}")
            return self._create_fallback_analysis(title, abstract)
    
    def _create_fallback_analysis(self, title: str, abstract: str) -> PaperAnalysis:
        """创建兜底分析结果"""
        return PaperAnalysis(
            trans_abs=f"【翻译失败】原标题: {title}",
            compressed="分析服务暂时不可用，请稍后重试。",
            keywords=["分析失败", "待重试", "N/A"],
            sub_topic="未知",
            recommendation="一般推荐"
        )
    
    def analyze_paper_batch(
        self, 
        papers: List[Dict[str, str]], 
        progress_callback=None
    ) -> List[PaperAnalysis]:
        """
        批量分析论文
        
        Args:
            papers: 论文列表，每项包含 title 和 abstract
            progress_callback: 进度回调函数 (current, total)
            
        Returns:
            分析结果列表
        """
        results = []
        total = len(papers)
        
        for i, paper in enumerate(papers):
            try:
                analysis = self.analyze_paper(
                    paper.get("title", ""),
                    paper.get("abstract", "")
                )
                results.append(analysis)
                
                if progress_callback:
                    progress_callback(i + 1, total)
                    
            except Exception as e:
                logger.error(f"批量分析第 {i+1} 篇失败: {e}")
                results.append(self._create_fallback_analysis(
                    paper.get("title", ""),
                    paper.get("abstract", "")
                ))
        
        return results
    
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """
        通用聊天接口
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            
        Returns:
            回复文本
        """
        try:
            response = self._call_api(messages, temperature)
            return response
        except Exception as e:
            logger.error(f"聊天接口调用失败: {e}")
            return ""
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "request_count": self.request_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": (
                self.success_count / self.request_count * 100
                if self.request_count > 0 else 0
            ),
            "model": self.model
        }


# ==================== 兼容性接口 ====================

_default_client: Optional[LLMClient] = None


def get_client() -> LLMClient:
    """获取默认客户端（单例）"""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client


def translate_abstract(text: str, domain: str = "AI") -> str:
    """
    兼容旧接口：翻译/分析论文
    
    返回 JSON 字符串以保持向后兼容
    """
    # 尝试从 text 中分离 title 和 abstract
    lines = text.split('\n')
    title = ""
    abstract = text
    
    for line in lines:
        if line.startswith("Title:"):
            title = line.replace("Title:", "").strip()
        elif line.startswith("Abstract:"):
            abstract = line.replace("Abstract:", "").strip()
    
    client = get_client()
    analysis = client.analyze_paper(title, abstract)
    
    # 返回 JSON 字符串
    return analysis.model_dump_json(ensure_ascii=False)
