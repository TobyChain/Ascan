"""
ArXiv Daily V3 - P2 完整版
集成多维度评分、定时调度、查询接口
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import get_settings
from src.database.connection import init_database, get_db_session
from src.database.repositories import PaperRepository
from src.core.scoring import MultiDimensionScorer, DEFAULT_DIRECTIONS
from src.core.scheduler import get_scheduler, init_default_schedule
from src.core.query_engine import PaperQueryEngine, TrendAnalyzer
from src.pipeline.core import Pipeline, PipelineContext
from src.pipeline.stages import FetchStage, ParseStage, GenerateReportStage, UploadStage, NotifyStage


def setup_logging():
    """配置日志"""
    settings = get_settings()
    logger.remove()
    
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    logger.add(
        log_dir / "arxiv_v3_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        level="DEBUG",
        encoding="utf-8"
    )


async def run_multi_dimension_pipeline(
    date: str = None,
    subjects: list = None,
    use_llm: bool = True
) -> PipelineContext:
    """
    运行多维度评分流水线
    
    Args:
        date: 目标日期
        subjects: 主题列表
        use_llm: 是否使用 LLM 进行深度分析
    """
    settings = get_settings()
    
    if date is None:
        target_date = datetime.now() - timedelta(days=settings.arxiv_date_offset_days)
        date = target_date.strftime("%Y-%m-%d")
    
    if subjects is None:
        subjects = settings.arxiv_subjects
    
    logger.info(f"🚀 启动多维度评分流水线: {date}, 主题: {subjects}")
    
    context = PipelineContext(date=date, subjects=subjects)
    
    # 阶段 1-2: 获取和解析
    from src.pipeline.core import Stage, Status
    
    fetch_stage = FetchStage()
    parse_stage = ParseStage(max_papers=settings.max_total_papers)
    
    # 获取数据
    context.start_stage(Stage.FETCHING)
    jina_data = fetch_stage.jina_client.fetch_arxiv_list(subjects[0])
    ids = fetch_stage.jina_client.parse_arxiv_ids(jina_data, date)
    context.raw_ids = ids
    context.total_papers = len(ids)
    context.end_stage(Stage.FETCHING, Status.SUCCESS)
    
    # 解析元数据
    context.start_stage(Stage.PARSING)
    arxiv_results = parse_stage.fetch_arxiv_metadata(ids)
    context.end_stage(Stage.PARSING, Status.SUCCESS)
    
    # 阶段 3: 多维度评分
    logger.info("🔍 开始多维度评分...")
    scorer = MultiDimensionScorer(DEFAULT_DIRECTIONS)
    
    papers_for_scoring = []
    for result in arxiv_results:
        papers_for_scoring.append({
            "arxiv_id": result.get_short_id().split('v')[0],
            "title": result.title,
            "abstract": result.summary,
            "authors": [a.name for a in result.authors]
        })
    
    scored_papers = scorer.batch_score(
        papers_for_scoring,
        progress_callback=lambda c, t: logger.info(f"评分进度: {c}/{t}")
    )
    
    # 保存到数据库
    db = get_db_session()
    repo = PaperRepository(db)
    
    # 初始化LLM客户端（用于生成摘要）
    from src.tools.call_llm import LLMClient
    llm_client = LLMClient()
    
    for i, score in enumerate(scored_papers):
        # 创建或更新论文记录
        paper_data = next(
            (p for p in papers_for_scoring if p["arxiv_id"] == score.arxiv_id),
            None
        )
        if paper_data:
            from src.models.schemas import ArxivPaper, PaperAnalysis
            
            paper = ArxivPaper(
                arxiv_id=score.arxiv_id,
                title=score.title,
                authors=paper_data["authors"],
                abstract=paper_data["abstract"],
                abs_url=f"https://arxiv.org/abs/{score.arxiv_id}",
                pdf_url=f"https://arxiv.org/pdf/{score.arxiv_id}.pdf",
                published=date
            )
            
            # 生成真正的中文摘要（使用LLM）
            try:
                logger.info(f"[{i+1}/{len(scored_papers)}] 生成中文摘要: {score.title[:60]}...")
                
                # 调用LLM生成摘要
                analysis = llm_client.analyze_paper(
                    paper_data["title"],
                    paper_data["abstract"]
                )
                
                # 存储评分结果到 keywords 字段（扩展存储）
                keywords_list = [d.value for d in score.primary_directions] + score.dimension_scores[0].matched_keywords[:3]
                # 确保至少有2个关键词
                if len(keywords_list) < 2:
                    keywords_list.extend(["AI", "arXiv"][:2-len(keywords_list)])
                
                paper.analysis = PaperAnalysis(
                    trans_abs=analysis.trans_abs,  # 使用LLM生成的真实摘要
                    compressed=analysis.compressed,  # 使用LLM生成的压缩版
                    keywords=keywords_list,
                    sub_topic=score.primary_directions[0].value if score.primary_directions else "未知",
                    recommendation=score.recommendation_level
                )
                
            except Exception as e:
                logger.error(f"生成摘要失败 {score.arxiv_id}: {e}")
                # 使用评分结果作为兜底
                keywords_list = [d.value for d in score.primary_directions] + score.dimension_scores[0].matched_keywords[:3]
                if len(keywords_list) < 2:
                    keywords_list.extend(["AI", "arXiv"][:2-len(keywords_list)])
                
                paper.analysis = PaperAnalysis(
                    trans_abs=f"[多维度评分] 综合得分: {score.overall_score}",
                    compressed=f"主要方向: {', '.join(d.value for d in score.primary_directions)}",
                    keywords=keywords_list,
                    sub_topic=score.primary_directions[0].value if score.primary_directions else "未知",
                    recommendation=score.recommendation_level
                )
            
            repo.create_or_update(paper)
    
    logger.success(f"✅ 评分完成，已保存 {len(scored_papers)} 篇论文")
    
    # 阶段 4+: 生成报告和推送
    generate_stage = GenerateReportStage()
    await generate_stage.execute(context)
    
    if settings.enable_feishu_push:
        upload_stage = UploadStage()
        notify_stage = NotifyStage()
        await upload_stage.execute(context)
        await notify_stage.execute(context)
    
    return context


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ArXiv AI Agent V3 - P2 完整版")
    parser.add_argument("--date", "-d", help="目标日期 (YYYY-MM-DD)")
    parser.add_argument("--subjects", "-s", help="主题列表，逗号分隔")
    parser.add_argument("--init-db", action="store_true", help="初始化数据库")
    parser.add_argument("--scheduler", action="store_true", help="启动定时调度器")
    parser.add_argument("--query", "-q", help="查询关键词")
    parser.add_argument("--hot", action="store_true", help="显示热点论文")
    parser.add_argument("--weekly", action="store_true", help="生成周报")
    parser.add_argument("--direction", help="查看特定研究方向")
    
    args = parser.parse_args()
    
    setup_logging()
    
    if args.init_db:
        logger.info("🗄️ 初始化数据库...")
        init_database()
        logger.success("数据库初始化完成")
        return
    
    if args.scheduler:
        logger.info("⏰ 启动定时调度器...")
        scheduler = init_default_schedule()
        scheduler.start()
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            scheduler.stop()
        return
    
    if args.query:
        query_engine = PaperQueryEngine()
        from src.core.query_engine import SearchCriteria
        
        criteria = SearchCriteria(keywords=args.query.split(","))
        results = query_engine.search(criteria, limit=20)
        
        print(f"\n🔍 搜索 '{args.query}' 的结果:\n")
        for p in results:
            print(f"  [{p['recommendation']}] {p['title'][:80]}")
            print(f"     方向: {', '.join(p.get('keywords', [])[:3])}")
        return
    
    if args.hot:
        query_engine = PaperQueryEngine()
        results = query_engine.get_hot_papers(days=7, limit=20)
        
        print(f"\n🔥 最近 7 天热点论文:\n")
        for p in results:
            print(f"  [{p['recommendation']}] {p['title'][:80]}")
        return
    
    if args.weekly:
        analyzer = TrendAnalyzer()
        report = analyzer.generate_weekly_report()
        
        print(f"\n📅 周报: {report['period']}\n")
        print(f"总论文数: {report['total_papers']}\n")
        print("热门方向:")
        for d in report['hot_directions']:
            print(f"  - {d['name']}: {d['count']} 篇")
        return
    
    if args.direction:
        query_engine = PaperQueryEngine()
        from src.core.scoring import ResearchDirection
        
        direction = ResearchDirection(args.direction)
        results = query_engine.get_by_direction(direction, limit=20)
        
        print(f"\n📊 {direction.name} 方向论文:\n")
        for p in results:
            print(f"  [{p['recommendation']}] {p['title'][:80]}")
        return
    
    # 默认：运行一次抓取
    subjects = args.subjects.split(",") if args.subjects else None
    result = await run_multi_dimension_pipeline(
        date=args.date,
        subjects=subjects
    )
    
    if result.error_message:
        logger.error(f"执行失败: {result.error_message}")
        sys.exit(1)
    else:
        logger.success("执行完成")


if __name__ == "__main__":
    asyncio.run(main())
