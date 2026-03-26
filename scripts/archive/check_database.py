"""检查数据库状态"""

from database.connection import get_db_session
from database.models import PaperDB

def check_database():
    """检查数据库状态"""
    session = get_db_session()
    
    # 统计总数
    total = session.query(PaperDB).count()
    print(f"当前数据库文献数量: {total}\n")
    
    # 统计推荐等级
    recommendations = session.query(
        PaperDB.recommendation,
        PaperDB.recommendation,
        PaperDB.recommendation
    ).all()
    
    from collections import Counter
    counter = Counter([r[0] for r in recommendations])
    
    print("按推荐等级统计:")
    for level, count in sorted(counter.items(), key=lambda x: x[1], reverse=True):
        print(f"  {level}: {count} 篇")
    
    # 统计日期分布
    from datetime import datetime, timedelta
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    today_count = session.query(PaperDB).filter(PaperDB.published == today).count()
    yesterday_count = session.query(PaperDB).filter(PaperDB.published == yesterday).count()
    
    print(f"\n最近2天的文献分布:")
    print(f"  {today}: {today_count} 篇")
    print(f"  {yesterday}: {yesterday_count} 篇")
    
    session.close()

if __name__ == "__main__":
    check_database()
