#!/usr/bin/env python3
"""
简化版 ArXiv 爬虫 - 快速抓取今天的论文
"""

import sys
import re
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import arxiv
from loguru import logger

from src.database.connection import init_database, get_db_session
from src.database.repositories import PaperRepository
from src.database.models import PaperDB
from src.core.scoring import MultiDimensionScorer, DEFAULT_DIRECTIONS


def extract_affiliations(result) -> list:
    """从 arxiv 结果中提取作者机构"""
    affiliations = []
    try:
        # arxiv 库的作者对象可能有 affiliation 属性
        for author in result.authors:
            if hasattr(author, 'affiliation') and author.affiliation:
                affiliations.append(author.affiliation)
    except:
        pass
    return affiliations[:3]  # 只取前三个


def get_arxiv_image_url(arxiv_id: str) -> str:
    """获取 ArXiv 论文的主图 URL"""
    # ArXiv 摘要页面的图片通常在 arxiv.org/abs/{id} 页面中
    # 这里返回一个可能的图片 URL 格式
    return f"https://arxiv.org/ps_cache/{arxiv_id[0]}/{arxiv_id[:4]}/arxiv.{arxiv_id}.ps.gz"


def fetch_today_papers(subjects: list = None, max_papers: int = None):
    """抓取今天的 ArXiv 论文"""
    
    if subjects is None:
        subjects = ["cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.RO"]
    
    # 获取今天的日期
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    logger.info(f"📅 抓取日期: {yesterday.strftime('%Y-%m-%d')}")
    logger.info(f"📚 主题: {', '.join(subjects)}")
    
    # 使用 arxiv 库搜索
    client = arxiv.Client()
    
    all_results = []
    date_query = yesterday.strftime("%Y%m%d")
    
    for subject in subjects:
        # 构建查询 - 使用 submittedDate 获取昨天提交的论文
        query = f"cat:{subject} AND submittedDate:[{date_query}0000 TO {date_query}2359]"
        
        logger.info(f"🔍 查询 {subject}: {query}")
        
        search = arxiv.Search(
            query=query,
            max_results=max_papers or 200,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        
        results = list(client.results(search))
        logger.info(f"   ✅ {subject}: 找到 {len(results)} 篇论文")
        all_results.extend(results)
    
    # 去重（按 arxiv_id）
    seen_ids = set()
    unique_results = []
    for result in all_results:
        arxiv_id = result.get_short_id().split('v')[0]
        if arxiv_id not in seen_ids:
            seen_ids.add(arxiv_id)
            unique_results.append(result)
    
    logger.info(f"✅ 总计找到 {len(unique_results)} 篇不重复论文")
    
    return unique_results


import re
import requests
from bs4 import BeautifulSoup

def extract_institutions_from_arxiv_page(arxiv_id: str) -> list:
    """
    从ArXiv摘要页面HTML获取机构信息
    注意：ArXiv标准页面通常不包含机构信息，除非作者在作者名中明确写入
    """
    try:
        abs_url = f"https://arxiv.org/abs/{arxiv_id}"
        response = requests.get(abs_url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        institutions = []
        
        # 方法1: 查找meta标签中的机构信息
        for meta in soup.find_all('meta', {'name': 'citation_author_institution'}):
            inst = meta.get('content', '').strip()
            if inst and len(inst) > 2 and inst not in institutions:
                institutions.append(inst)
        
        # 方法2: 从作者div中解析（如果作者名中包含机构信息）
        if not institutions:
            author_div = soup.find('div', class_='authors')
            if author_div:
                # 获取作者列表
                authors_text = author_div.get_text()
                # 提取括号中的内容（可能包含机构）
                matches = re.findall(r'\(([^)]+)\)', authors_text)
                for match in matches:
                    inst = match.strip()
                    # 检查是否是机构（包含关键词）
                    if any(keyword in inst.lower() for keyword in ['university', 'institute', 'college', 'school', 'center', 'lab', 'department']):
                        if len(inst) > 3 and inst not in institutions:
                            institutions.append(inst)
        
        return institutions[:3]  # 只返回前三个
        
    except Exception as e:
        return []


def extract_institutions_from_source(arxiv_id: str) -> list:
    """
    备用方法：从ArXiv源文件获取机构信息（较慢但更准确）
    只在页面方法失败时使用
    """
    return []  # 暂时不使用，因为太慢


def extract_institutions_from_authors(authors: list) -> list:
    """从作者名中提取机构信息（启发式方法，作为备用）"""
    institutions = []
    for author in authors[:3]:  # 只处理前三个作者
        # 尝试从作者名中提取机构（通常在括号中）
        if '(' in author and ')' in author:
            start = author.find('(')
            end = author.find(')')
            if start != -1 and end != -1:
                inst = author[start+1:end].strip()
                if inst and inst not in institutions:
                    institutions.append(inst)
    return institutions


def score_papers(results, use_source_institutions: bool = True):
    """对论文进行多维度评分"""
    scorer = MultiDimensionScorer(DEFAULT_DIRECTIONS)
    
    papers_data = []
    institutions_found = 0
    institutions_missing = 0
    
    for i, result in enumerate(results):
        arxiv_id = result.get_short_id().split('v')[0]
        authors_list = [a.name for a in result.authors]
        
        # 提取机构信息
        institutions = []
        if use_source_institutions:
            # 主要使用启发式方法（从作者名中提取）
            institutions = extract_institutions_from_authors(authors_list)
            
            # 如果启发式方法失败，尝试从ArXiv页面获取
            if not institutions:
                institutions = extract_institutions_from_arxiv_page(arxiv_id)
            
            if institutions:
                institutions_found += 1
            else:
                institutions_missing += 1
        else:
            # 使用启发式方法
            institutions = extract_institutions_from_authors(authors_list)
            if institutions:
                institutions_found += 1
            else:
                institutions_missing += 1
        
        paper_data = {
            'arxiv_id': arxiv_id,
            'title': result.title,
            'authors': authors_list,
            'affiliations': institutions,
            'primary_image_url': None,
            'abstract': result.summary,
            'abs_url': f"http://arxiv.org/abs/{arxiv_id}",
            'pdf_url': f"http://arxiv.org/pdf/{arxiv_id}",
            'published': result.published.strftime('%Y-%m-%d'),
            'doi': result.doi,
        }
        
        # 多维度评分
        score = scorer.score_paper(
            arxiv_id=arxiv_id,
            title=result.title,
            abstract=result.summary,
            authors=authors_list
        )
        
        paper_data['score'] = score
        papers_data.append(paper_data)
        
        # 每10篇显示一次进度
        if (i + 1) % 10 == 0:
            logger.info(f"   已处理 {i + 1}/{len(results)} 篇论文")
    
    # 计算缺失率
    total = institutions_found + institutions_missing
    missing_rate = institutions_missing / total if total > 0 else 1.0
    
    logger.info(f"📊 机构信息统计:")
    logger.info(f"   成功获取: {institutions_found} 篇")
    logger.info(f"   缺失: {institutions_missing} 篇")
    logger.info(f"   缺失率: {missing_rate * 100:.1f}%")
    
    # 如果缺失率大于20%，清空所有机构信息
    if missing_rate > 0.20:
        logger.warning(f"⚠️ 机构信息缺失率 {missing_rate * 100:.1f}% > 20%，将不显示机构栏")
        for paper in papers_data:
            paper['affiliations'] = []
    else:
        logger.success(f"✅ 机构信息缺失率 {missing_rate * 100:.1f}% <= 20%，将显示机构栏")
    
    return papers_data


def save_to_database(papers_data):
    """保存论文到数据库"""
    db = get_db_session()
    repo = PaperRepository(db)
    
    imported = 0
    skipped = 0
    
    for paper in papers_data:
        # 检查是否已存在
        existing = repo.get_by_arxiv_id(paper['arxiv_id'])
        if existing:
            skipped += 1
            continue
        
        # 创建新记录
        paper_db = PaperDB(
            arxiv_id=paper['arxiv_id'],
            title=paper['title'],
            authors=paper['authors'],
            affiliations=paper.get('affiliations', []),
            primary_image_url=paper.get('primary_image_url'),
            abstract=paper['abstract'],
            abs_url=paper['abs_url'],
            pdf_url=paper['pdf_url'],
            doi=paper.get('doi'),
            doi_url=None,
            published=paper['published'],
            bibtex=None,
            trans_abs='',  # 没有翻译
            compressed='',  # 没有压缩版
            keywords=[],  # 评分器会填充
            sub_topic=paper['score'].primary_directions[0].value if paper['score'].primary_directions else '未知',
            recommendation=paper['score'].recommendation_level,
            status='completed',
            processed_at=datetime.now()
        )
        
        db.add(paper_db)
        imported += 1
    
    db.commit()
    return imported, skipped


def main():
    """主函数"""
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    # 初始化数据库
    init_database()
    logger.success("✅ 数据库初始化完成")
    
    # 抓取论文 - 限制数量以便测试机构信息获取
    subjects = ["cs.AI", "cs.LG"]
    results = fetch_today_papers(subjects=subjects, max_papers=50)
    
    if not results:
        logger.warning("⚠️ 没有找到今天的论文")
        return
    
    # 评分
    logger.info("🔍 开始多维度评分...")
    papers_data = score_papers(results)
    
    # 统计推荐等级
    rec_counts = {}
    for p in papers_data:
        rec = p['score'].recommendation_level
        rec_counts[rec] = rec_counts.get(rec, 0) + 1
    
    logger.info("📊 推荐等级分布:")
    for rec, count in sorted(rec_counts.items(), key=lambda x: -x[1]):
        logger.info(f"   {rec}: {count} 篇")
    
    # 显示高分论文
    high_score = [p for p in papers_data if p['score'].recommendation_level in ['极度推荐', '很推荐', '推荐']]
    if high_score:
        logger.info(f"\n🔥 高分论文 ({len(high_score)} 篇):")
        for p in high_score[:10]:
            score = p['score']
            logger.info(f"   [{score.recommendation_level}] {p['title'][:55]}...")
    
    # 保存到数据库
    imported, skipped = save_to_database(papers_data)
    logger.success(f"✅ 导入完成: {imported} 篇新论文, {skipped} 篇已存在")
    
    # 统计
    db = get_db_session()
    total = db.query(PaperDB).count()
    rec_dist = {}
    for p in db.query(PaperDB).all():
        rec = p.recommendation
        rec_dist[rec] = rec_dist.get(rec, 0) + 1
    
    logger.info(f"\n📊 数据库总计: {total} 篇论文")
    logger.info("推荐等级分布:")
    for rec, count in sorted(rec_dist.items(), key=lambda x: -x[1]):
        logger.info(f"   {rec}: {count} 篇")


if __name__ == "__main__":
    main()
