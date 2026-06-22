"""
多维度相关性评分系统
聚焦于电商 AI 应用的六个核心方向：
  1. DIGITAL_WORKER     — 数字员工 / 虚拟人
  2. PRODUCT_RECOMMEND  — 商品推荐 / 电商推荐
  3. PRODUCT_INSPECTION — 商品巡检 / 合规检测
  4. ECOM_SERVICE       — 电商客服 / 对话系统
  5. AGENTIC_FRAMEWORK  — 智能体框架 / 工具调用 / MCP
  6. INTENT_UNDERSTAND  — 意图理解 / 用户行为
"""

RECOMMENDATION_ORDER = {
    "极度推荐": 5, "很推荐": 4, "推荐": 3, "一般推荐": 2, "不推荐": 1,
}

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import re
from loguru import logger


class ResearchDirection(str, Enum):
    """研究方向枚举（聚焦电商 AI 应用）"""
    DIGITAL_WORKER     = "digital_worker"     # 数字员工 / 虚拟人
    PRODUCT_RECOMMEND  = "product_recommend"  # 商品推荐 / 电商推荐
    PRODUCT_INSPECTION = "product_inspection" # 商品巡检 / 合规检测
    ECOM_SERVICE       = "ecom_service"       # 电商客服 / 对话系统
    AGENTIC_FRAMEWORK  = "agentic_framework"  # 智能体框架 / 工具调用 / MCP
    INTENT_UNDERSTAND  = "intent_understand"  # 意图理解 / 用户行为


@dataclass
class DirectionConfig:
    """研究方向配置"""
    name: str
    keywords: List[str]           # 核心关键词（高权重）
    secondary_keywords: List[str] # 次要关键词（低权重）
    top_authors: List[str]
    weight: float = 1.0
    description: str = ""


# ──────────────────────────────────────────────────────────────────────────────
# 四个核心方向配置
# 设计原则：
#   - 核心关键词必须精准，宁缺毋滥
#   - 聚焦电商 AI 应用场景
#   - weight 越高 → 该方向对最终排名的影响越大
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_DIRECTIONS: Dict[ResearchDirection, DirectionConfig] = {

    # ── 1. 数字员工 / 虚拟人 ──────────────────────────────────────────────────
    ResearchDirection.DIGITAL_WORKER: DirectionConfig(
        name="数字员工",
        keywords=[
            "digital twin", "digital avatar", "virtual human",
            "digital human", "virtual avatar", "avatar generation",
            "talking head", "face reenactment", "face cloning",
            "face generation", "face swap", "face synthesis",
            "video generation", "portrait animation",
            "lip sync", "speech-driven animation",
            "3d avatar", "3d face reconstruction",
            "neural radiance", "nerf", "gaussian splatting",
            "motion capture", "body animation",
        ],
        secondary_keywords=[
            "deepfake", "face editing", "style transfer",
            "image-to-video", "text-to-video",
            "virtual try-on", "virtual fitting",
            "live streaming", "virtual anchor",
            "expression transfer", "gesture generation",
            "voice cloning", "tts", "speech synthesis",
        ],
        top_authors=[
            "google", "meta", "microsoft", "nvidia",
            "bytedance", "tencent", "baidu",
            "adobe", "stanford", "cmu",
        ],
        weight=1.8,
        description="数字员工、虚拟人生成、面部动画、3D 重建等技术"
    ),

    # ── 2. 商品推荐 / 电商推荐 ────────────────────────────────────────────────
    ResearchDirection.PRODUCT_RECOMMEND: DirectionConfig(
        name="商品推荐",
        keywords=[
            "product recommendation", "item recommendation",
            "e-commerce recommendation", "ecommerce recommendation",
            "recommendation system", "recommender system",
            "collaborative filtering", "content-based filtering",
            "sequential recommendation", "next-item prediction",
            "click-through rate", "ctr prediction",
            "conversion rate", "purchase prediction",
            "personalized recommendation", "hybrid recommendation",
            "llm recommendation", "llm for recommendation",
            "conversational recommendation",
        ],
        secondary_keywords=[
            "ranking model", "learning to rank",
            "cold start", "exploration exploitation",
            "knowledge graph recommendation",
            "session-based recommendation",
            "user modeling", "user preference",
            "user behavior", "behavioral recommendation",
            "cross-domain recommendation", "multi-task learning",
            "graph neural network", "attention mechanism",
        ],
        top_authors=[
            "amazon", "google", "meta",
            "microsoft", "tencent", "bytedance",
            "jd", "netflix", "pinterest",
        ],
        weight=1.7,
        description="商品推荐算法、电商推荐系统、排序模型、用户行为建模"
    ),

    # ── 3. 商品巡检 / 合规检测 ────────────────────────────────────────────────
    ResearchDirection.PRODUCT_INSPECTION: DirectionConfig(
        name="商品巡检",
        keywords=[
            "product inspection", "product compliance",
            "compliance detection", "violation detection",
            "content moderation", "content safety",
            "counterfeit detection", "fake product",
            "image classification", "product quality",
            "defect detection", "anomaly detection",
            "text classification", "harmful content",
            "risk detection", "fraud detection",
            "brand protection", "trademark detection",
            "multimodal classification", "image-text matching",
        ],
        secondary_keywords=[
            "object detection", "visual inspection",
            "ocr", "text recognition",
            "fine-grained classification", "attribute recognition",
            "product categorization", "product tagging",
            "safety filter", "nsfw detection",
            "policy compliance", "regulatory",
            "llm moderation", "llm safety",
        ],
        top_authors=[
            "google", "meta", "microsoft",
            "openai", "anthropic", "bytedance", "tencent",
            "amazon", "baidu",
        ],
        weight=1.6,
        description="商品合规巡检、违规检测、内容安全、图文多模态审核"
    ),

    # ── 4. 电商客服 / 对话系统 ────────────────────────────────────────────────
    ResearchDirection.ECOM_SERVICE: DirectionConfig(
        name="电商客服",
        keywords=[
            "customer service", "customer support",
            "e-commerce chatbot", "ecommerce chatbot",
            "dialogue system", "conversational ai",
            "task-oriented dialogue", "goal-oriented dialogue",
            "after-sales service", "service automation",
            "question answering", "faq",
            "intent recognition", "intent classification",
            "slot filling", "dialogue state tracking",
            "retrieval augmented generation", "rag",
            "knowledge-grounded dialogue",
        ],
        secondary_keywords=[
            "chatbot", "virtual assistant",
            "sentiment analysis", "emotion detection",
            "response generation", "reply suggestion",
            "multi-turn dialogue", "context understanding",
            "llm agent", "ai agent",
            "tool use", "function calling",
            "customer satisfaction", "service quality",
        ],
        top_authors=[
            "google", "meta", "microsoft",
            "amazon", "openai", "anthropic",
            "baidu", "tencent", "jd",
        ],
        weight=1.5,
        description="电商客服对话系统、意图识别、FAQ 问答、售后自动化"
    ),

    # ── 5. 智能体框架 / 工具调用 / MCP ────────────────────────────────────────
    ResearchDirection.AGENTIC_FRAMEWORK: DirectionConfig(
        name="智能体框架",
        keywords=[
            "agentic workflow", "agentic ai",
            "multi-agent system", "multi-agent framework",
            "autonomous agent", "llm agent", "ai agent",
            "agent framework", "agent architecture",
            "agent-based", "agent based system",
            "tool use", "tool calling", "function calling",
            "mcp", "model context protocol",
            "skills library", "tool library",
            "api calling", "tool integration",
            "orchestration framework", "agent orchestration",
            "multi-agent orchestration",
            "self-reflection", "self-refine",
        ],
        secondary_keywords=[
            "agentic", "multi-agent", "orchestrator",
            "sub-agent", "agent collaboration",
            "tool selection", "tool routing",
            "code agent", "software agent",
            "browser use", "web agent", "gui agent", "computer use",
            "task planning", "task decomposition",
            "workflow", "pipeline orchestration",
            "reward model", "environment interaction",
        ],
        top_authors=[
            "openai", "anthropic", "google", "deepmind",
            "microsoft", "meta", "langchain", "stanford",
        ],
        weight=1.4,
        description="智能体系统架构、工具调用、MCP协议、多智能体编排"
    ),

    # ── 6. 意图理解 / 用户行为 ────────────────────────────────────────────────
    ResearchDirection.INTENT_UNDERSTAND: DirectionConfig(
        name="意图理解",
        keywords=[
            "intent recognition", "intent understanding",
            "user intent", "intent classification",
            "intent prediction", "intent inference",
            "intent detection", "query understanding",
            "user modeling", "user preference",
            "user behavior", "behavioral analysis",
            "personalization", "user profiling",
            "context understanding", "query intent",
        ],
        secondary_keywords=[
            "natural language understanding", "nlu",
            "semantic parsing", "slot filling",
            "dialogue state tracking", "search intent",
            "click behavior", "session analysis",
            "attention pattern", "engagement prediction",
            "cold start", "preference learning",
        ],
        top_authors=[
            "google", "meta", "microsoft",
            "amazon", "baidu", "tencent", "bytedance",
        ],
        weight=1.3,
        description="用户意图理解、行为分析、个性化建模"
    ),
}


# ──────────────────────────────────────────────────────────────────────────────
# 数据类
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class DimensionScore:
    direction: ResearchDirection
    score: float
    matched_keywords: List[str]
    confidence: float
    reason: str


@dataclass
class MultiDimensionScore:
    arxiv_id: str
    title: str
    dimension_scores: List[DimensionScore] = field(default_factory=list)
    overall_score: float = 0.0
    relevance_score: float = 0.0
    novelty_score: float = 0.0
    quality_score: float = 0.0
    recommendation_level: str = "不推荐"
    primary_directions: List[ResearchDirection] = field(default_factory=list)
    timestamp: str = ""
    version: str = "2.0"

    def get_top_directions(self, n: int = 3) -> List[Tuple[ResearchDirection, float]]:
        sorted_scores = sorted(self.dimension_scores, key=lambda x: x.score, reverse=True)
        return [(s.direction, s.score) for s in sorted_scores[:n] if s.score > 0]

    def to_dict(self) -> dict:
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
                    "reason": s.reason,
                }
                for s in self.dimension_scores
            ],
            "timestamp": self.timestamp,
        }


# ──────────────────────────────────────────────────────────────────────────────
# 评分器
# ──────────────────────────────────────────────────────────────────────────────

class MultiDimensionScorer:
    """
    多维度评分器
    评分逻辑：
      - 每个方向独立打分（0-100）
      - overall_score = 各方向加权均值（高分方向额外加权）
      - 推荐门槛提高：overall_score >= 45 才会进入"推荐"及以上
      - 严格过滤：overall_score < 30 标记为"不推荐"，由 main.py 直接丢弃
    """

    # 最低入选分数线（低于此分不写入报告）
    MIN_REPORT_SCORE = 30.0
    # 每日报告最多保留篇数
    MAX_REPORT_PAPERS = 15

    def __init__(self, directions: Optional[Dict[ResearchDirection, DirectionConfig]] = None):
        self.directions = directions or DEFAULT_DIRECTIONS
        self._compile_patterns()

    def _compile_patterns(self):
        self.patterns: Dict[ResearchDirection, List[Tuple[str, re.Pattern]]] = {}
        for direction, config in self.directions.items():
            patterns = []
            for kw in config.keywords:
                if ' ' in kw:
                    pat = re.compile(re.escape(kw), re.IGNORECASE)
                else:
                    pat = re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
                patterns.append((kw, pat))
            self.patterns[direction] = patterns

    def score_paper(
        self,
        arxiv_id: str,
        title: str,
        abstract: str,
        authors: Optional[List[str]] = None,
    ) -> MultiDimensionScore:
        from datetime import datetime

        text = f"{title} {abstract}".lower()
        dimension_scores = []

        for direction, config in self.directions.items():
            score, matched, confidence, reason = self._score_direction(
                text, direction, config, authors or []
            )
            dimension_scores.append(DimensionScore(
                direction=direction,
                score=score,
                matched_keywords=matched,
                confidence=confidence,
                reason=reason,
            ))

        overall = self._overall(dimension_scores)

        primary = [
            s.direction for s in dimension_scores if s.score >= 35
        ]
        primary.sort(
            key=lambda d: next(s.score for s in dimension_scores if s.direction == d),
            reverse=True,
        )

        recommendation = self._recommend(overall, primary)

        return MultiDimensionScore(
            arxiv_id=arxiv_id,
            title=title,
            dimension_scores=dimension_scores,
            overall_score=overall,
            relevance_score=overall,
            novelty_score=self._novelty(text, primary),
            quality_score=self._quality(authors or [], primary),
            recommendation_level=recommendation,
            primary_directions=primary[:3],
            timestamp=datetime.now().isoformat(),
        )

    def _score_direction(
        self,
        text: str,
        direction: ResearchDirection,
        config: DirectionConfig,
        authors: List[str],
    ) -> Tuple[float, List[str], float, str]:
        score = 0.0
        matched = []

        # 核心关键词：每次命中 +30，同一词多次出现不额外加分
        for kw, pat in self.patterns[direction]:
            if pat.search(text):
                matched.append(kw)
                score += 30

        # 次要关键词：每个 +8
        for kw in config.secondary_keywords:
            if kw.lower() in text:
                score += 8
                if kw not in matched:
                    matched.append(kw)

        # 机构匹配：+15
        for author in authors:
            al = author.lower()
            for inst in config.top_authors:
                if inst.lower() in al:
                    score += 15
                    break

        # 乘以方向权重
        score *= config.weight

        # 归一化
        score = min(score, 100.0)

        confidence = min(len(matched) / 3.0, 1.0)
        if matched:
            reason = f"匹配关键词: {', '.join(matched[:5])}"
        else:
            reason = "未匹配到相关关键词"

        return score, matched, confidence, reason

    def _overall(self, dim_scores: List[DimensionScore]) -> float:
        """加权均值，高分维度额外加权"""
        if not dim_scores:
            return 0.0
        scores = [s.score for s in dim_scores]
        weights = [1 + s.score / 100 for s in dim_scores]
        return round(sum(s * w for s, w in zip(scores, weights)) / sum(weights), 2)

    def _novelty(self, text: str, primary: List[ResearchDirection]) -> float:
        base = 50.0
        if len(primary) >= 2:
            base += 20
        novel_kws = ['novel', 'new', 'first', 'propose', 'introduce']
        for kw in novel_kws:
            if kw in text:
                base += 5
        return min(base, 100.0)

    def _quality(self, authors: List[str], primary: List[ResearchDirection]) -> float:
        base = 55.0
        top = ['openai', 'google', 'deepmind', 'anthropic', 'meta',
               'microsoft', 'stanford', 'mit', 'berkeley', 'tsinghua',
               'xiaomi', 'huawei', 'apple', 'samsung']
        for author in authors:
            al = author.lower()
            for inst in top:
                if inst in al:
                    base += 10
                    break
        return min(base, 100.0)

    def _recommend(self, score: float, primary: List[ResearchDirection]) -> str:
        """
        推荐门槛（已校准到4方向评分体系）：
          极度推荐 >= 65  且命中核心方向（数字员工/商品推荐/商品巡检/智能体框架）
          很推荐   >= 50  或命中核心方向 >= 45
          推荐     >= 38
          一般推荐 >= 30
          不推荐   <  30  （main.py 据此过滤）
        """
        core = {
            ResearchDirection.DIGITAL_WORKER,
            ResearchDirection.PRODUCT_RECOMMEND,
            ResearchDirection.PRODUCT_INSPECTION,
            ResearchDirection.AGENTIC_FRAMEWORK,
        }
        has_core = any(d in core for d in primary)

        if score >= 65 and has_core:
            return "极度推荐"
        elif score >= 50 or (score >= 45 and has_core):
            return "很推荐"
        elif score >= 38:
            return "推荐"
        elif score >= 30:
            return "一般推荐"
        else:
            return "不推荐"

    def batch_score(
        self,
        papers: List[Dict],
        progress_callback=None,
    ) -> List[MultiDimensionScore]:
        results = []
        total = len(papers)
        for i, paper in enumerate(papers):
            try:
                s = self.score_paper(
                    arxiv_id=paper.get("arxiv_id", ""),
                    title=paper.get("title", ""),
                    abstract=paper.get("abstract", ""),
                    authors=paper.get("authors", []),
                )
                results.append(s)
                if progress_callback:
                    progress_callback(i + 1, total)
            except Exception as e:
                logger.error(f"评分失败 {paper.get('arxiv_id')}: {e}")
                results.append(MultiDimensionScore(
                    arxiv_id=paper.get("arxiv_id", ""),
                    title=paper.get("title", ""),
                    overall_score=0,
                    recommendation_level="不推荐",
                ))
        return results
