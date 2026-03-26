"""
测试脚本 - 模拟Web界面的研究方向页面
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

import os
os.chdir(Path(__file__).parent.parent)

from database.connection import init_database, get_db_session
from core.query_engine import PaperQueryEngine
from core.scoring import ResearchDirection
from database.models import PaperDB

print("=" * 70)
print("模拟Web界面 - 研究方向页面")
print("=" * 70)

# 初始化数据库
init_database()
db = get_db_session()

print("\n🔄 模拟用户操作流程:\n")

# 模拟方向选择器
direction_names = {d.value: d for d in ResearchDirection}
print(f"可用方向: {list(direction_names.keys())}")

# 测试每个方向
for selected_name, selected_direction in direction_names.items():
    print(f"\n📌 用户选择: {selected_name} ({selected_direction.name})")
    
    try:
        # 模拟查询
        query = PaperQueryEngine(db)
        papers = query.get_by_direction(selected_direction, limit=5)
        
        if papers and len(papers) > 0:
            print(f"✅ 成功: 找到 {len(papers)} 篇论文")
            print(f"   第1篇: {papers[0]['title'][:60]}...")
        else:
            print(f"⚠️ 警告: 没有找到论文")
            
    except Exception as e:
        print(f"❌ 错误: {str(e)}")

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)
