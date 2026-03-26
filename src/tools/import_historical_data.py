#!/usr/bin/env python3
"""
导入历史 Markdown 数据到 SQLite 数据库
"""

import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import init_database, get_db_session
from src.database.repositories import PaperRepository
from src.database.models import PaperDB


def parse_markdown_file(file_path: Path) -> List[Dict]:
    """解析 Markdown 文件，提取论文信息"""
    content = file_path.read_text(encoding='utf-8')
    
    papers = []
    
    # 按 "## " 分割每个论文条目
    sections = re.split(r'\n## \d+\.\s*', content)
    
    for section in sections[1:]:  # 跳过第一个空内容
        paper = parse_paper_section(section)
        if paper:
            papers.append(paper)
    
    return papers


def parse_paper_section(section: str) -> Optional[Dict]:
    """解析单个论文段落"""
    lines = section.strip().split('\n')
    if not lines:
        return None
    
    # 第一行是标题
    title = lines[0].strip()
    
    paper = {
        'title': title,
        'authors': [],
        'sub_topic': '未知',
        'recommendation': '一般推荐',
        'keywords': [],
        'abs_url': '',
        'pdf_url': '',
        'trans_abs': '',
        'arxiv_id': '',
        'published': ''
    }
    
    in_abstract = False
    abstract_lines = []
    
    for line in lines[1:]:
        line = line.strip()
        
        # 解析作者
        if line.startswith('- 作者：') or line.startswith('- Authors: '):
            authors_str = line.replace('- 作者：', '').replace('- Authors: ', '')
            paper['authors'] = [a.strip() for a in authors_str.split(',')]
        
        # 解析子主题
        elif line.startswith('- 子主题：') or line.startswith('- Sub-topic: '):
            paper['sub_topic'] = line.replace('- 子主题：', '').replace('- Sub-topic: ', '').strip()
        
        # 解析推荐等级
        elif line.startswith('- 推荐：') or line.startswith('- Recommendation: '):
            rec = line.replace('- 推荐：', '').replace('- Recommendation: ', '').strip()
            paper['recommendation'] = rec
        
        # 解析关键词
        elif line.startswith('- 关键词：') or line.startswith('- Keywords: '):
            kw_str = line.replace('- 关键词：', '').replace('- Keywords: ', '')
            paper['keywords'] = [k.strip() for k in kw_str.split(',')]
        
        # 解析 Abstract URL
        elif line.startswith('- Abstract：') or line.startswith('- Abstract: '):
            url = line.replace('- Abstract：', '').replace('- Abstract: ', '').strip()
            paper['abs_url'] = url
            # 从 URL 提取 arxiv_id
            match = re.search(r'/(\d{4}\.\d{4,5})', url)
            if match:
                paper['arxiv_id'] = match.group(1)
        
        # 解析 PDF URL
        elif line.startswith('- PDF：') or line.startswith('- PDF: '):
            paper['pdf_url'] = line.replace('- PDF：', '').replace('- PDF: ', '').strip()
        
        # 中文摘要标记
        elif line == '**中文摘要**' or line == '**Translated Abstract**':
            in_abstract = True
            continue
        
        # 收集摘要内容
        elif in_abstract and line and not line.startswith('---'):
            abstract_lines.append(line)
        
        # 遇到分隔符结束摘要收集
        elif line.startswith('---') and in_abstract:
            in_abstract = False
    
    paper['trans_abs'] = '\n'.join(abstract_lines).strip()
    
    return paper if paper['arxiv_id'] else None


def import_to_database(papers: List[Dict], date_str: str):
    """导入论文到数据库"""
    db = get_db_session()
    repo = PaperRepository(db)
    
    imported = 0
    skipped = 0
    
    for paper_data in papers:
        # 检查是否已存在
        existing = repo.get_by_arxiv_id(paper_data['arxiv_id'])
        if existing:
            skipped += 1
            continue
        
        # 创建新记录
        paper_db = PaperDB(
            arxiv_id=paper_data['arxiv_id'],
            title=paper_data['title'],
            authors=paper_data['authors'],
            abstract='',  # 历史数据没有英文摘要
            abs_url=paper_data['abs_url'],
            pdf_url=paper_data['pdf_url'],
            doi=None,
            doi_url=None,
            published=date_str,
            bibtex=None,
            trans_abs=paper_data['trans_abs'],
            compressed='',  # 没有压缩版
            keywords=paper_data['keywords'],
            sub_topic=paper_data['sub_topic'],
            recommendation=paper_data['recommendation'],
            status='completed',
            processed_at=datetime.now()
        )
        
        db.add(paper_db)
        imported += 1
    
    db.commit()
    return imported, skipped


def main():
    """主函数"""
    # 初始化数据库
    init_database()
    print("✅ 数据库初始化完成")
    
    # 查找所有 Markdown 文件
    db_dir = Path(__file__).parent.parent / 'database'
    md_files = sorted(db_dir.glob('*.md'))
    
    total_imported = 0
    total_skipped = 0
    
    for md_file in md_files:
        # 从文件名提取日期
        date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', md_file.name)
        if not date_match:
            continue
        
        date_str = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
        print(f"\n📄 处理: {md_file.name} (日期: {date_str})")
        
        # 解析文件
        papers = parse_markdown_file(md_file)
        print(f"   解析到 {len(papers)} 篇论文")
        
        # 导入数据库
        imported, skipped = import_to_database(papers, date_str)
        total_imported += imported
        total_skipped += skipped
        
        print(f"   ✅ 导入: {imported} | ⏭️ 跳过: {skipped}")
    
    print(f"\n{'='*50}")
    print(f"📊 导入完成!")
    print(f"   总计导入: {total_imported} 篇")
    print(f"   总计跳过: {total_skipped} 篇 (已存在)")


if __name__ == '__main__':
    main()
