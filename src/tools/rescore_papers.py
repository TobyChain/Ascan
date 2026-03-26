#!/usr/bin/env python3
"""
重新评分所有论文（使用新的阈值）
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.database.connection import init_database, get_db_session
from src.database.models import PaperDB
from src.core.scoring import MultiDimensionScorer, DEFAULT_DIRECTIONS


def rescore_all_papers():
    """重新评分所有论文"""
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    # 初始化
    init_database()
    db = get_db_session()
    
    # 获取所有论文
    papers = db.query(PaperDB).all()
    logger.info(f"📊 共有 {len(papers)} 篇论文需要重新评分")
    
    # 创建评分器
    scorer = MultiDimensionScorer(DEFAULT_DIRECTIONS)
    
    # 统计
    rec_counts = {"极度推荐": 0, "很推荐": 0, "推荐": 0, "一般推荐": 0, "不推荐": 0}
    
    for paper in papers:
        # 重新评分
        score = scorer.score_paper(
            arxiv_id=str(paper.arxiv_id),
            title=paper.title,
            abstract=paper.abstract,
            authors=paper.authors or []
        )
        
        # 更新数据库
        paper.recommendation = score.recommendation_level
        paper.sub_topic = score.primary_directions[0].value if score.primary_directions else '未知'
        
        rec_counts[score.recommendation_level] = rec_counts.get(score.recommendation_level, 0) + 1
    
    # 提交更改
    db.commit()
    
    logger.success("✅ 重新评分完成！")
    logger.info("📈 新的推荐等级分布:")
    for rec, count in sorted(rec_counts.items(), key=lambda x: -x[1]):
        logger.info(f"   {rec}: {count} 篇")
    
    # 显示高分论文
    logger.info("\n🔥 高分论文示例:")
    high_papers = db.query(PaperDB).filter(
        PaperDB.recommendation.in_(['极度推荐', '很推荐', '推荐'])
    ).limit(10).all()
    
    for p in high_papers:
        logger.info(f"   [{p.recommendation}] {p.title[:60]}...")


if __name__ == "__main__":
    rescore_all_papers()
