"""
飞书通知工具模块
支持发送多种类型的飞书卡片消息
"""

import os
import time
import hmac
import hashlib
import base64
import requests
from typing import Any, Dict, Optional
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class FeishuNotifier:
    """飞书消息通知器"""

    def __init__(self, webhook_url: Optional[str] = None, secret: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("FEISHU_WEBHOOK_URL")
        self.secret = secret or os.getenv("FEISHU_SECRET")

    def _gen_sign(self, timestamp: str) -> str:
        """生成飞书签名"""
        if not self.secret:
            return ""
        string_to_sign = "{}\n{}".format(timestamp, self.secret)
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")
        return sign

    def send_card(self, card_content: Dict[str, Any]) -> bool:
        """
        发送自定义卡片消息

        Args:
            card_content: 飞书卡片 JSON 内容
        """
        if not self.webhook_url:
            logger.warning("未配置 FEISHU_WEBHOOK_URL，跳过发送")
            return False

        timestamp = str(int(time.time()))

        msg = {
            "msg_type": "interactive",
            "card": card_content,
        }

        if self.secret:
            msg["timestamp"] = timestamp
            msg["sign"] = self._gen_sign(timestamp)

        try:
            response = requests.post(self.webhook_url, json=msg, timeout=10)
            response.raise_for_status()
            result = response.json()
            if result.get("code") == 0:
                logger.success("飞书卡片消息发送成功")
                return True
            else:
                logger.error(f"飞书卡片消息发送失败: {result}")
                return False
        except Exception as e:
            logger.exception(f"发送飞书卡片请求异常: {e}")
            return False

    def send_daily_report(
        self,
        date: str,
        paper_count: int,
        file_url: str,
        title: str = "ArXiv AI Daily Report",
        template: str = "blue",
    ) -> bool:
        """
        发送每日报告卡片（内置模板）
        """
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": template,
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"content": f"**📅 报告日期**\n{date}", "tag": "lark_md"},
                },
                {
                    "tag": "div",
                    "text": {
                        "content": f"**📚 今日论文数量**\n{paper_count} 篇",
                        "tag": "lark_md",
                    },
                },
                {
                    "tag": "div",
                    "text": {
                        "content": "💡 点击下方按钮查看详细的论文翻译与分析报告（Markdown 格式）。",
                        "tag": "lark_md",
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "查看 Markdown 报告",
                            },
                            "type": "primary",
                            "url": file_url,
                        }
                    ],
                },
            ],
        }
        return self.send_card(card)


# 兼容性快捷函数
def send_daily_report(date: str, paper_count: int, file_url: str) -> bool:
    notifier = FeishuNotifier()
    return notifier.send_daily_report(date, paper_count, file_url)


def main():
    """
    主函数：从最新日志中提取 Docx 链接并发送
    """
    import glob
    import re
    from datetime import datetime

    # 定位 logs 目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    log_dir = os.path.join(project_root, "logs")

    if not os.path.exists(log_dir):
        logger.error(f"日志目录不存在: {log_dir}")
        return

    # 获取最新的日志文件
    log_files = glob.glob(os.path.join(log_dir, "*.log"))
    if not log_files:
        logger.error("未找到日志文件")
        return
    
    latest_log = max(log_files, key=os.path.getmtime)
    logger.info(f"读取最新日志文件: {latest_log}")

    docx_url = None
    
    # 读取日志查找链接和论文数量
    paper_count = 0
    try:
        with open(latest_log, "r", encoding="utf-8") as f:
            content = f.read()
            # 搜索：飞书 Docx 写入成功: https://...
            # 使用 findall 取最后一个匹配项，防止有多次写入
            matches = re.findall(r"飞书 Docx 写入成功:\s*(https://[^\s]+)", content)
            if matches:
                docx_url = matches[-1]
            
            # 搜索：共提取到 245 篇文献
            count_matches = re.findall(r"共提取到\s*(\d+)\s*篇文献", content)
            if count_matches:
                paper_count = int(count_matches[-1])
                logger.info(f"找到论文数量: {paper_count}")

    except Exception as e:
        logger.error(f"读取日志文件失败: {e}")
        return

    if docx_url:
        logger.info(f"找到 Docx 链接: {docx_url}")
        # 发送卡片
        # 日期使用当前日期
        today = datetime.now().strftime("%Y-%m-%d")
        
        notifier = FeishuNotifier()
        notifier.send_daily_report(
            date=today,
            paper_count=paper_count,
            file_url=docx_url,
            title="ArXiv AI Daily Report (Resend)"
        )
    else:
        logger.warning("在最新日志中未找到 Docx 链接")


if __name__ == "__main__":
    main()
