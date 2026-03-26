"""migrate_reports_to_docx.py

一次性迁移脚本：
1) 将已存在的 HTML 报告批量转为 Markdown 文件
2) 将 Markdown 内容写入飞书 Docx 文档（create docx -> convert -> insert blocks）

也支持：直接把处理后的 JSON（论文列表）渲染成 Markdown 并上传。

用法示例：
    # 迁移历史 HTML：生成 md 并上传
    python migrate_reports_to_docx.py html --database-dir ./database --out-md-dir ./database_md \
        --folder-token your_folder_token_here

    # 基于某一天 JSON 生成 Markdown 并上传
    python migrate_reports_to_docx.py json --json-file ./database/2025-12-20.json --date 2025-12-20 \
        --out-md ./database_md/2025-12-20.md --folder-token your_folder_token_here

环境变量：
    FEISHU_APP_ID / FEISHU_APP_SECRET 必填
    （可选）FEISHU_DOCX_FOLDER_TOKEN 可作为默认 docx folder token
    （可选）FEISHU_DOCX_DOCUMENT_ID 若写入已有文档，可设置此值跳过创建
    FEISHU_WEBHOOK_URL / FEISHU_SECRET 用于发送飞书卡片（可选；不配则不发送）
    （可选）FEISHU_DOCX_BASE_URL 用于拼接 docx 文档链接
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from loguru import logger
from markdownify import markdownify as md

from tools.call_feishu_card import FeishuNotifier
from tools.upload_md_feishu import FeishuDriveUploadError, upload_file
from tools.report2md import papers_to_markdown

# 加载环境变量
load_dotenv()


def html_to_markdown(html_text: str) -> str:
    # markdownify 会做较通用的 HTML->MD 转换。
    # 为了让 docx.convert 更稳定：使用 ATX 标题，尽量输出“干净”的 Markdown。
    markdown_text = md(html_text, heading_style="ATX")
    return markdown_text.strip() + "\n"


def _build_docx_url(document_id: str) -> str:
    base = (
        (os.getenv("FEISHU_DOCX_BASE_URL") or "https://ai.feishu.cn/docx")
        .strip()
        .rstrip("/")
    )
    return f"{base}/{document_id}"


def _maybe_send_card(*, date: str, paper_count: int, docx_url: str) -> None:
    # 若未配置 webhook，则静默跳过
    if not (os.getenv("FEISHU_WEBHOOK_URL") or "").strip():
        return
    notifier = FeishuNotifier()
    notifier.send_daily_report(date=date, paper_count=paper_count, file_url=docx_url)


def upload_markdown_file(*, md_path: Path, parent_node: Optional[str]) -> Optional[str]:
    try:
        return upload_file(
            file_path=str(md_path),
            file_name=md_path.name,
            parent_node=parent_node,
        )
    except FeishuDriveUploadError as e:
        logger.exception(f"写入 Docx 失败: {md_path.name}: {e}")
        return None


def cmd_html(args: argparse.Namespace) -> int:
    db_dir = Path(args.database_dir)
    out_dir = Path(args.out_md_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    html_files = sorted(db_dir.glob("*.html"))
    if not html_files:
        logger.warning(f"未找到 html 文件: {db_dir}")
        return 0

    folder_token = args.folder_token

    for i, html_path in enumerate(html_files, start=1):
        logger.info(f"[{i}/{len(html_files)}] 迁移: {html_path.name}")
        html_text = html_path.read_text(encoding="utf-8", errors="ignore")
        markdown_text = html_to_markdown(html_text)

        md_path = out_dir / (html_path.stem + ".md")
        md_path.write_text(markdown_text, encoding="utf-8")

        document_id = upload_markdown_file(md_path=md_path, parent_node=folder_token)
        if document_id:
            docx_url = _build_docx_url(document_id)
            logger.success(f"写入成功 document_id={document_id} url={docx_url}")
            _maybe_send_card(date=html_path.stem, paper_count=0, docx_url=docx_url)

    return 0


def cmd_json(args: argparse.Namespace) -> int:
    json_file = Path(args.json_file)
    if not json_file.exists():
        raise FileNotFoundError(json_file)

    papers: List[Dict[str, Any]] = json.loads(json_file.read_text(encoding="utf-8"))
    markdown_text = papers_to_markdown(args.date, papers)

    if args.out_md:
        Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_md).write_text(markdown_text, encoding="utf-8")

    md_path: Optional[Path] = None
    if args.out_md:
        md_path = Path(args.out_md)
    else:
        md_path = Path.cwd() / f"{args.date}.md"
        md_path.write_text(markdown_text, encoding="utf-8")

    document_id = upload_markdown_file(md_path=md_path, parent_node=args.folder_token)
    if document_id:
        docx_url = _build_docx_url(document_id)
        logger.success(f"写入成功 document_id={document_id} url={docx_url}")
        _maybe_send_card(date=args.date, paper_count=len(papers), docx_url=docx_url)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)

    p_html = sub.add_parser("html", help="migrate database/*.html -> md + docx")
    p_html.add_argument("--database-dir", required=True)
    p_html.add_argument("--out-md-dir", required=True)
    p_html.add_argument("--folder-token", default=None)
    p_html.add_argument("--title-prefix", default="ArXiv Report - ")
    p_html.set_defaults(func=cmd_html)

    p_json = sub.add_parser("json", help="json -> md + docx")
    p_json.add_argument("--json-file", required=True)
    p_json.add_argument("--date", required=True, help="YYYY-MM-DD")
    p_json.add_argument("--out-md", default=None)
    p_json.add_argument("--folder-token", default=None)
    p_json.add_argument("--title", default=None)
    p_json.set_defaults(func=cmd_json)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
