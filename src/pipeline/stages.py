"""
流水线各阶段的具体实现
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict

import arxiv
from loguru import logger

from src.pipeline.core import PipelineStage, PipelineContext, Stage
from src.tools.call_jina import JinaReaderClient
from src.tools.call_llm import LLMClient
from src.database.connection import get_db_session
from src.database.repositories import PaperRepository
from src.models.schemas import ArxivPaper, PaperAnalysis


class FetchStage(PipelineStage):
    """数据获取阶段"""
    
    def __init__(self):
        super().__init__("fetching")
        self.jina_client = JinaReaderClient()
    
    async def execute(self, context: PipelineContext) -> bool:
        """从 Jina 获取论文 ID"""
        try:
            all_ids = []
            
            for subject in context.subjects:
                logger.info(f"正在获取主题: {subject}")
                
                # 计算目标日期
                target_date = self._get_target_date(context.date)
                target_date_str = target_date.strftime("%a, %d %b %Y")
                
                # 获取数据
                data = self.jina_client.fetch_arxiv_list(
                    subject=subject,
                    skip=0,
                    show=250
                )
                
                if data:
                    ids = self.jina_client.parse_arxiv_ids(data, target_date_str)
                    logger.info(f"主题 {subject} 获取到 {len(ids)} 篇论文")
                    all_ids.extend(ids)
                else:
                    logger.warning(f"主题 {subject} 未获取到数据")
            
            # 去重
            context.raw_ids = list(dict.fromkeys(all_ids))
            context.total_papers = len(context.raw_ids)
            
            logger.success(f"共获取 {len(context.raw_ids)} 篇不重复论文")
            return True
            
        except Exception as e:
            logger.error(f"获取阶段失败: {e}")
            return False
    
    def _get_target_date(self, date_str: str) -> datetime:
        """获取目标日期"""
        return datetime.strptime(date_str, "%Y-%m-%d")


class ParseStage(PipelineStage):
    """数据解析阶段 - 获取论文元数据"""
    
    def __init__(self, max_papers: int = 500):
        super().__init__("parsing")
        self.max_papers = max_papers
    
    async def execute(self, context: PipelineContext) -> bool:
        """使用 arxiv 库获取元数据"""
        try:
            if not context.raw_ids:
                logger.warning("没有论文 ID 需要解析")
                return True
            
            # 限制数量
            ids = context.raw_ids[:self.max_papers]
            context.total_papers = len(ids)
            
            logger.info(f"正在解析 {len(ids)} 篇论文的元数据...")
            
            # 使用 arxiv 库
            client = arxiv.Client()
            search = arxiv.Search(id_list=ids)
            results = list(client.results(search))
            
            papers = []
            for result in results:
                paper = ArxivPaper(
                    arxiv_id=result.get_short_id().split('v')[0],  # 去除版本号
                    title=result.title,
                    authors=[a.name for a in result.authors],
                    abstract=result.summary,
                    summary=result.summary,
                    abs_url=result.entry_id,
                    pdf_url=result.pdf_url,
                    doi=result.doi,
                    doi_url=f"https://doi.org/{result.doi}" if result.doi else None,
                    published=result.published.strftime("%Y-%m-%d"),
                    bibtex=self._generate_bibtex(result)
                )
                papers.append(paper)
            
            context.papers = [p.model_dump() for p in papers]
            
            # 存入数据库
            self._save_to_db(papers, context.date)
            
            logger.success(f"成功解析 {len(papers)} 篇论文")
            return True
            
        except Exception as e:
            logger.exception(f"解析阶段失败: {e}")
            return False
    
    def _generate_bibtex(self, result) -> str:
        """生成 BibTeX"""
        year = result.published.year
        title = result.title
        author_text = " and ".join([a.name for a in result.authors])
        url = result.entry_id
        doi = result.doi
        eprint = result.get_short_id()
        
        doi_line = f"  doi={{{doi}}},\n" if doi else ""
        return (
            f"@article{{{eprint},\n"
            f"  title={{{title}}},\n"
            f"  author={{{author_text}}},\n"
            f"  journal={{arXiv preprint arXiv:{eprint}}},\n"
            f"  year={{{year}}},\n"
            f"  url={{{url}}},\n"
            f"{doi_line}"
            f"}}"
        )
    
    def fetch_arxiv_metadata(self, ids: List[str]) -> List:
        """获取 arXiv 元数据（同步方法）"""
        try:
            if not ids:
                logger.warning("没有论文 ID 需要解析")
                return []
            
            # 限制数量
            ids = ids[:self.max_papers]
            
            logger.info(f"正在解析 {len(ids)} 篇论文的元数据...")
            
            # 使用 arxiv 库
            client = arxiv.Client()
            search = arxiv.Search(id_list=ids)
            results = list(client.results(search))
            
            logger.success(f"成功解析 {len(results)} 篇论文")
            return results
            
        except Exception as e:
            logger.exception(f"解析阶段失败: {e}")
            return []
    
    def _save_to_db(self, papers: List[ArxivPaper], date: str):
        """保存到数据库"""
        try:
            db = get_db_session()
            repo = PaperRepository(db)
            
            for paper in papers:
                repo.create_or_update(paper)
            
            logger.info(f"已保存 {len(papers)} 篇论文到数据库")
        except Exception as e:
            logger.error(f"保存到数据库失败: {e}")


class AnalyzeStage(PipelineStage):
    """LLM 分析阶段"""
    
    def __init__(self, batch_size: int = 10):
        super().__init__("analyzing")
        self.llm_client = LLMClient()
        self.batch_size = batch_size
    
    async def execute(self, context: PipelineContext) -> bool:
        """批量分析论文"""
        try:
            papers_data = context.papers
            if not papers_data:
                logger.warning("没有论文需要分析")
                return True
            
            db = get_db_session()
            repo = PaperRepository(db)
            
            total = len(papers_data)
            processed = 0
            failed = 0
            
            logger.info(f"开始分析 {total} 篇论文...")
            
            for i, paper_data in enumerate(papers_data):
                try:
                    # 检查是否已分析
                    existing = repo.get_by_arxiv_id(paper_data["arxiv_id"])
                    if existing and existing.status == "completed" and existing.trans_abs:
                        logger.info(f"[{i+1}/{total}] 跳过已分析: {paper_data['arxiv_id']}")
                        processed += 1
                        continue
                    
                    logger.info(f"[{i+1}/{total}] 分析: {paper_data['title'][:60]}...")
                    
                    # 调用 LLM
                    analysis = self.llm_client.analyze_paper(
                        paper_data["title"],
                        paper_data["abstract"]
                    )
                    
                    # 更新数据库
                    repo.update_analysis(
                        paper_data["arxiv_id"],
                        analysis,
                        status="completed"
                    )
                    
                    # 更新上下文
                    paper_data["analysis"] = analysis.model_dump()
                    processed += 1
                    
                except Exception as e:
                    logger.error(f"分析论文失败 {paper_data.get('arxiv_id')}: {e}")
                    failed += 1
                    # 更新失败状态
                    if existing:
                        existing.status = "failed"
                        existing.error_message = str(e)
                        db.commit()
                
                # 更新进度
                context.processed_count = processed
                context.failed_count = failed
            
            logger.success(f"分析完成: {processed} 成功, {failed} 失败")
            return True
            
        except Exception as e:
            logger.exception(f"分析阶段失败: {e}")
            return False


class GenerateReportStage(PipelineStage):
    """生成报告阶段"""
    
    def __init__(self, output_dir: str = "./output"):
        super().__init__("generating")
        self.output_dir = output_dir
    
    async def execute(self, context: PipelineContext) -> bool:
        """生成 Markdown 报告"""
        try:
            from src.tools.report2md import papers_to_markdown
            
            db = get_db_session()
            repo = PaperRepository(db)
            
            # 从数据库获取当天的论文
            papers_db = repo.get_by_date(context.date)
            
            if not papers_db:
                logger.warning("没有论文数据可生成报告")
                return True
            
            # 转换为字典列表
            papers = [p.to_dict() for p in papers_db]
            
            # 按推荐程度排序
            recommendation_order = {
                "极度推荐": 5,
                "很推荐": 4,
                "推荐": 3,
                "一般推荐": 2,
                "不推荐": 1,
            }
            papers.sort(
                key=lambda x: recommendation_order.get(x.get("recommendation"), 0),
                reverse=True
            )
            
            # 生成 Markdown
            markdown_text = papers_to_markdown(context.date, papers)
            
            # 保存文件
            import os
            os.makedirs(self.output_dir, exist_ok=True)
            
            md_path = f"{self.output_dir}/{context.date}.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_text)
            
            context.report_path = md_path
            logger.success(f"报告已生成: {md_path}")
            return True
            
        except Exception as e:
            logger.exception(f"生成报告失败: {e}")
            return False


class UploadStage(PipelineStage):
    """上传阶段"""
    
    def __init__(self):
        super().__init__("uploading")
    
    async def execute(self, context: PipelineContext) -> bool:
        """上传到飞书"""
        try:
            from src.tools.upload_md_feishu import upload_file
            from src.config.settings import get_settings
            
            settings = get_settings()
            
            if not settings.enable_feishu_push:
                logger.info("飞书推送已禁用")
                return True
            
            if not hasattr(context, 'report_path'):
                logger.error("报告路径不存在")
                return False
            
            folder_token = settings.feishu_docx_folder_token
            if not folder_token:
                logger.error("未配置飞书文件夹 Token")
                return False
            
            # 上传
            document_id = upload_file(
                file_path=context.report_path,
                file_name=f"{context.date}.md",
                parent_node=folder_token
            )
            
            if document_id:
                # 构建 URL
                base_url = settings.feishu_docx_base_url.rstrip('/')
                context.report_url = f"{base_url}/{document_id}"
                logger.success(f"已上传到飞书: {context.report_url}")
                return True
            else:
                logger.error("上传失败")
                return False
                
        except Exception as e:
            logger.exception(f"上传阶段失败: {e}")
            return False


class NotifyStage(PipelineStage):
    """通知阶段"""
    
    def __init__(self):
        super().__init__("notifying")
    
    async def execute(self, context: PipelineContext) -> bool:
        """发送飞书通知"""
        try:
            from src.tools.call_feishu_card import FeishuNotifier
            from src.config.settings import get_settings
            
            settings = get_settings()
            
            if not settings.enable_feishu_push:
                logger.info("飞书推送已禁用")
                return True
            
            if not context.report_url:
                logger.warning("报告 URL 不存在，跳过通知")
                return True
            
            # 获取统计
            db = get_db_session()
            repo = PaperRepository(db)
            stats = repo.get_statistics(context.date)
            
            notifier = FeishuNotifier()
            success = notifier.send_daily_report(
                date=context.date,
                paper_count=stats.get("total", 0),
                file_url=context.report_url,
                title=f"ArXiv AI Daily Report - {context.date}"
            )
            
            if success:
                logger.success("飞书通知发送成功")
            else:
                logger.error("飞书通知发送失败")
            
            return success
            
        except Exception as e:
            logger.exception(f"通知阶段失败: {e}")
            return False
