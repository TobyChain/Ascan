"""修复飞书HTML渲染问题"""

import re
from database.connection import get_db_session
from database.models import PaperDB
from tools.report2md import papers_to_markdown

def clean_html_tags(text: str) -> str:
    """移除HTML标签"""
    if not text:
        return text
    
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 移除HTML实体
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    
    # 移除多余的空格和换行
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def fix_feishu_html():
    """修复飞书HTML渲染问题"""
    session = get_db_session()
    
    # 获取今天的文献
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    papers = session.query(PaperDB).filter(PaperDB.published == today).all()
    
    # 转换为字典列表，并清理HTML标签
    paper_list = []
    for p in papers:
        paper_list.append({
            'arxiv_id': p.arxiv_id,
            'title': clean_html_tags(p.title),
            'authors': [clean_html_tags(a) for a in p.authors],
            'abs_url': p.abs_url,
            'pdf_url': p.pdf_url,
            'sub_topic': p.sub_topic,
            'recommendation': p.recommendation,
            'keywords': p.keywords,
            'trans_abs': clean_html_tags(p.trans_abs),
            'compressed': clean_html_tags(p.compressed)
        })
    
    # 生成Markdown
    markdown = papers_to_markdown(today, paper_list)
    
    # 保存到文件
    with open('output/2026-02-03_fixed.md', 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    print(f'修复完成！共 {len(paper_list)} 篇论文')
    print(f'文件已保存: output/2026-02-03_fixed.md')
    
    # 检查是否有HTML标签残留
    html_pattern = re.compile(r'<[^>]+>')
    for p in paper_list:
        if html_pattern.search(p['title']):
            print(f"警告: {p['arxiv_id']} 标题仍有HTML标签")
        if html_pattern.search(p['trans_abs']):
            print(f"警告: {p['arxiv_id']} 摘要仍有HTML标签")
    
    session.close()

if __name__ == "__main__":
    fix_feishu_html()
