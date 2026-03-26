"""
多维度相关性评分系统
支持多个研究方向的综合评估
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import re
from loguru import logger


class ResearchDirection(str, Enum):
    """研究方向枚举"""
    MEDICAL_LLM = "medical_llm"      # 医学大模型
    MOE = "moe"                       # 混合专家模型
    LORA = "lora"                     # 低秩适配
    RAG = "rag"                       # 检索增强生成
    AGENT = "agent"                   # 智能体
    MULTIMODAL = "multimodal"         # 多模态
    REASONING = "reasoning"           # 推理能力
    ALIGNMENT = "alignment"           # 对齐技术


@dataclass
class DirectionConfig:
    """研究方向配置"""
    name: str                           # 方向名称
    keywords: List[str]                 # 核心关键词
    secondary_keywords: List[str]       # 次要关键词
    top_authors: List[str]              # 该领域重要作者/机构
    weight: float = 1.0                 # 基础权重
    description: str = ""               # 描述


# 预定义研究方向配置
DEFAULT_DIRECTIONS: Dict[ResearchDirection, DirectionConfig] = {
    ResearchDirection.MEDICAL_LLM: DirectionConfig(
        name="医学大模型",
        keywords=[
            "medical", "medicine", "healthcare", "clinical",
            "diagnosis", "biomedical", "health", "patient",
            "medical llm", "medical large language model"
        ],
        secondary_keywords=[
            "electronic health records", "ehr", "medical imaging",
            "drug discovery", "clinical trial"
        ],
        top_authors=["google health", "deepmind health", "microsoft health"],
        weight=1.5,
        description="医学领域的大模型应用"
    ),
    
    ResearchDirection.MOE: DirectionConfig(
        name="混合专家模型",
        keywords=[
            "mixture of experts", "moe", "sparse mixture",
            "expert routing", "switch transformer", "expert parallelism",
            "activation sparsity", "expert selection"
        ],
        secondary_keywords=[
            "expert capacity", "load balancing", "expert dropout",
            "hierarchical mixture of experts", "hmoe"
        ],
        top_authors=["google", "deepmind", "openai", "mistral"],
        weight=1.3,
        description="MoE 架构与专家路由技术"
    ),
    
    ResearchDirection.LORA: DirectionConfig(
        name="低秩适配",
        keywords=[
            "lora", "low-rank adaptation", "low rank",
            "parameter-efficient", "peft", "qlora", "dora",
            "adalora", "lora-fine-tuning", "lora fine tuning"
        ],
        secondary_keywords=[
            "adapter", "prefix tuning", "prompt tuning",
            "p-tuning", "bitfit", "ia3"
        ],
        top_authors=["microsoft", "huggingface", "stanford"],
        weight=1.3,
        description="参数高效微调技术"
    ),
    
    ResearchDirection.RAG: DirectionConfig(
        name="检索增强生成",
        keywords=[
            "retrieval-augmented", "retrieval augmented", "rag",
            "knowledge retrieval", "document retrieval",
            "vector database", "semantic search", "dense retrieval"
        ],
        secondary_keywords=[
            "hybrid retrieval", "multi-hop retrieval",
            "graphrag", "knowledge graph"
        ],
        top_authors=["meta", "google", "microsoft", "openai"],
        weight=1.2,
        description="检索增强的生成技术"
    ),
    
    ResearchDirection.AGENT: DirectionConfig(
        name="智能体系统",
        keywords=[
            "agent", "multi-agent", "autonomous agent",
            "tool use", "function calling", "agent framework",
            "llm agent", "ai agent", "agentic"
        ],
        secondary_keywords=[
            "agent memory", "agent planning", "agent reasoning",
            "tool learning", "api calling"
        ],
        top_authors=["openai", "anthropic", "google", "meta"],
        weight=1.4,
        description="LLM 智能体与工具使用"
    ),
    
    ResearchDirection.MULTIMODAL: DirectionConfig(
        name="多模态模型",
        keywords=[
            "multimodal", "vision-language", "vlm",
            "image understanding", "video understanding",
            "cross-modal", "multimodal llm"
        ],
        secondary_keywords=[
            "clip", "llava", "gpt-4v", "gemini",
            "audio", "speech recognition"
        ],
        top_authors=["openai", "google", "meta", "microsoft"],
        weight=1.2,
        description="多模态理解与生成"
    ),
    
    ResearchDirection.REASONING: DirectionConfig(
        name="推理能力",
        keywords=[
            "reasoning", "chain of thought", "cot",
            "mathematical reasoning", "logical reasoning",
            "step-by-step", "multistep reasoning"
        ],
        secondary_keywords=[
            "tree of thought", "graph of thought",
            "self-consistency", "verifier"
        ],
        top_authors=["openai", "deepmind", "google"],
        weight=1.3,
        description="大模型推理能力提升"
    ),
    
    ResearchDirection.ALIGNMENT: DirectionConfig(
        name="对齐技术",
        keywords=[
            "alignment", "rlhf", "dpo", "ppo",
            "instruction tuning", "human feedback",
            "constitutional ai", "safety"
        ],
        secondary_keywords=[
            "reward modeling", "preference optimization",
            "sft", "supervised fine-tuning"
        ],
        top_authors=["openai", "anthropic", "deepmind"],
        weight=1.2,
        description="模型对齐与安全性"
    ),
}


@dataclass
class DimensionScore:
    """单一维度得分"""
    direction: ResearchDirection
    score: float                    # 0-100
    matched_keywords: List[str]     # 匹配到的关键词
    confidence: float               # 置信度 0-1
    reason: str                     # 得分原因


@dataclass
class MultiDimensionScore:
    """多维度综合得分"""
    arxiv_id: str
    title: str
    
    # 各维度得分
    dimension_scores: List[DimensionScore] = field(default_factory=list)
    
    # 综合指标
    overall_score: float = 0.0              # 综合得分 0-100
    relevance_score: float = 0.0            # 相关性得分
    novelty_score: float = 0.0              # 新颖性得分
    quality_score: float = 0.0              # 质量得分
    
    # 推荐等级
    recommendation_level: str = "一般推荐"    # 极度推荐/很推荐/推荐/一般推荐/不推荐
    
    # 主要方向（得分最高的 1-3 个）
    primary_directions: List[ResearchDirection] = field(default_factory=list)
    
    # 元信息
    timestamp: str = ""
    version: str = "1.0"
    
    def get_top_directions(self, n: int = 3) -> List[Tuple[ResearchDirection, float]]:
        """获取得分最高的 n 个方向"""
        sorted_scores = sorted(
            self.dimension_scores,
            key=lambda x: x.score,
            reverse=True
        )
        return [(s.direction, s.score) for s in sorted_scores[:n] if s.score > 0]
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "arxiv_id": self.arxiv_id,
            "title": self.title,
            "overall_score": self.overall_score,
            "relevance_score": self.relevance_score,
            "novelty_score": self.novelty_score,
            "quality_score": self.quality_score,
            "recommendation_level": self.recommendation_level,
            "primary_directions": [d.value for d in self.primary_directions],
            "dimension_scores": [
                {
                    "direction": s.direction.value,
                    "score": s.score,
                    "matched_keywords": s.matched_keywords,
                    "confidence": s.confidence,
                    "reason": s.reason
                }
                for s in self.dimension_scores
            ],
            "timestamp": self.timestamp
        }


class MultiDimensionScorer:
    """多维度评分器"""
    
    def __init__(self, directions: Optional[Dict[ResearchDirection, DirectionConfig]] = None):
        self.directions = directions or DEFAULT_DIRECTIONS
        self._compile_patterns()
    
    def _compile_patterns(self):
        """编译正则表达式模式（优化性能）"""
        self.patterns = {}
        for direction, config in self.directions.items():
            # 为每个关键词创建不区分大小写的正则
            patterns = []
            for kw in config.keywords:
                # 处理词边界，避免部分匹配
                if ' ' in kw:
                    pattern = re.compile(re.escape(kw), re.IGNORECASE)
                else:
                    pattern = re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
                patterns.append((kw, pattern))
            self.patterns[direction] = patterns
    
    def score_paper(
        self,
        arxiv_id: str,
        title: str,
        abstract: str,
        authors: Optional[List[str]] = None
    ) -> MultiDimensionScore:
        """
        对论文进行多维度评分
        
        Args:
            arxiv_id: ArXiv ID
            title: 论文标题
            abstract: 论文摘要
            authors: 作者列表
            
        Returns:
            MultiDimensionScore 对象
        """
        from datetime import datetime
        
        text = f"{title} {abstract}".lower()
        dimension_scores = []
        
        # 计算各维度得分
        for direction, config in self.directions.items():
            score, matched_keywords, confidence, reason = self._calculate_direction_score(
                text, direction, config, authors or []
            )
            
            dimension_scores.append(DimensionScore(
                direction=direction,
                score=score,
                matched_keywords=matched_keywords,
                confidence=confidence,
                reason=reason
            ))
        
        # 计算综合得分
        overall_score = self._calculate_overall_score(dimension_scores)
        
        # 确定主要方向（得分>30 的）
        primary_directions = [
            s.direction for s in dimension_scores
            if s.score >= 30
        ]
        primary_directions.sort(
            key=lambda d: next(s.score for s in dimension_scores if s.direction == d),
            reverse=True
        )
        
        # 确定推荐等级
        recommendation = self._determine_recommendation(overall_score, primary_directions)
        
        return MultiDimensionScore(
            arxiv_id=arxiv_id,
            title=title,
            dimension_scores=dimension_scores,
            overall_score=overall_score,
            relevance_score=overall_score,  # 相关性与综合得分一致
            novelty_score=self._estimate_novelty(text, primary_directions),
            quality_score=self._estimate_quality(authors or [], primary_directions),
            recommendation_level=recommendation,
            primary_directions=primary_directions[:3],  # 最多 3 个主要方向
            timestamp=datetime.now().isoformat()
        )
    
    def _calculate_direction_score(
        self,
        text: str,
        direction: ResearchDirection,
        config: DirectionConfig,
        authors: List[str]
    ) -> Tuple[float, List[str], float, str]:
        """
        计算单一维度得分
        
        Returns:
            (score, matched_keywords, confidence, reason)
        """
        score = 0.0
        matched_keywords = []
        
        # 1. 关键词匹配（核心关键词权重更高）
        for keyword, pattern in self.patterns[direction]:
            matches = len(pattern.findall(text))
            if matches > 0:
                matched_keywords.append(keyword)
                # 核心关键词每个 +25 分，最多 75 分（提高分数）
                score += min(matches * 25, 75)
        
        # 2. 次要关键词匹配（每个 +10 分，最多 40 分）
        for kw in config.secondary_keywords:
            if kw.lower() in text:
                score += 10
                if kw not in matched_keywords:
                    matched_keywords.append(kw)
        
        # 3. 作者/机构匹配（+20 分）
        author_match = False
        for author in authors:
            author_lower = author.lower()
            for top_author in config.top_authors:
                if top_author.lower() in author_lower:
                    score += 20
                    author_match = True
                    break
        
        # 4. 应用基础权重
        score *= config.weight
        
        # 5. 归一化到 0-100
        score = min(score, 100)
        
        # 计算置信度（基于匹配数量）
        confidence = min(len(matched_keywords) / 3, 1.0)
        
        # 生成原因
        if matched_keywords:
            reason = f"匹配关键词: {', '.join(matched_keywords[:5])}"
            if author_match:
                reason += "; 来自顶级研究机构"
        else:
            reason = "未匹配到相关关键词"
        
        return score, matched_keywords, confidence, reason
    
    def _calculate_overall_score(self, dimension_scores: List[DimensionScore]) -> float:
        """计算综合得分"""
        if not dimension_scores:
            return 0.0
        
        # 取加权平均，高分维度权重更高
        scores = [s.score for s in dimension_scores]
        weights = [1 + s.score / 100 for s in dimension_scores]  # 高分额外加权
        
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        total_weight = sum(weights)
        
        return round(weighted_sum / total_weight, 2)
    
    def _estimate_novelty(self, text: str, primary_directions: List[ResearchDirection]) -> float:
        """估计新颖性（基于关键词组合）"""
        # 简单的启发式：组合多个方向表示创新性
        base_score = 50.0
        
        # 跨领域组合加分
        if len(primary_directions) >= 2:
            base_score += 20
        if len(primary_directions) >= 3:
            base_score += 10
        
        # 提到新方法/架构加分
        novel_keywords = ['novel', 'new', 'first', 'propose', 'introduce', 'architecture']
        for kw in novel_keywords:
            if kw in text:
                base_score += 5
        
        return min(base_score, 100)
    
    def _estimate_quality(
        self,
        authors: List[str],
        primary_directions: List[ResearchDirection]
    ) -> float:
        """估计质量（基于作者和方向热度）"""
        base_score = 60.0
        
        # 检查是否是知名机构
        top_institutions = [
            'openai', 'google', 'deepmind', 'anthropic', 'meta',
            'microsoft', 'stanford', 'mit', 'berkeley', 'tsinghua'
        ]
        
        for author in authors:
            author_lower = author.lower()
            for inst in top_institutions:
                if inst in author_lower:
                    base_score += 10
                    break
        
        # 热门方向加分
        hot_directions = [ResearchDirection.MOE, ResearchDirection.AGENT, ResearchDirection.REASONING]
        for d in primary_directions:
            if d in hot_directions:
                base_score += 5
        
        return min(base_score, 100)
    
    def _determine_recommendation(
        self,
        overall_score: float,
        primary_directions: List[ResearchDirection]
    ) -> str:
        """确定推荐等级（降低阈值以获取更多推荐）"""
        # 高优先方向（用户特别关注）
        priority_directions = [
            ResearchDirection.MEDICAL_LLM,
            ResearchDirection.MOE,
            ResearchDirection.LORA,
            ResearchDirection.AGENT,
            ResearchDirection.RAG
        ]
        
        has_priority = any(d in priority_directions for d in primary_directions)
        
        # 提升阈值，让推荐更严格
        if overall_score >= 85 and has_priority:
            return "极度推荐"
        elif overall_score >= 75 or (overall_score >= 70 and has_priority):
            return "很推荐"
        elif overall_score >= 60:
            return "推荐"
        elif overall_score >= 40:
            return "一般推荐"
        else:
            return "不推荐"
    
    def batch_score(
        self,
        papers: List[Dict],
        progress_callback=None
    ) -> List[MultiDimensionScore]:
        """批量评分"""
        results = []
        total = len(papers)
        
        for i, paper in enumerate(papers):
            try:
                score = self.score_paper(
                    arxiv_id=paper.get("arxiv_id", ""),
                    title=paper.get("title", ""),
                    abstract=paper.get("abstract", ""),
                    authors=paper.get("authors", [])
                )
                results.append(score)
                
                if progress_callback:
                    progress_callback(i + 1, total)
                    
            except Exception as e:
                logger.error(f"评分失败 {paper.get('arxiv_id')}: {e}")
                # 创建失败标记的得分
                results.append(MultiDimensionScore(
                    arxiv_id=paper.get("arxiv_id", ""),
                    title=paper.get("title", ""),
                    overall_score=0,
                    recommendation_level="不推荐",
                    timestamp=""
                ))
        
        return results
