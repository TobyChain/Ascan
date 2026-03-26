"""tap2upload.py

最小化：把本地 Markdown 文件写入飞书 Docx 云文档。

核心流程（由 feishu_drive_upload 内部完成）：
1) 创建 Docx 文档（或写入已有 document_id）
2) 将 Markdown convert 为 blocks
3) 批量写入 blocks 到文档

用法示例：
    uv run tap2upload.py

环境变量：
    FEISHU_APP_ID / FEISHU_APP_SECRET
    FEISHU_DOCX_FOLDER_TOKEN
    （可选）FEISHU_DOCX_DOCUMENT_ID
    （可选）FEISHU_DOCX_BASE_URL（默认 https://ai.feishu.cn/docx）
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from tools.upload_md_feishu import FeishuDriveUploadError, upload_file


# 加载环境变量
load_dotenv()

# ================= 配置区域 =================
REPORT_DATE = "2025-12-16"
MD_FILE_PATH = f"./database_md/{REPORT_DATE}.md"
# ===========================================


def _build_docx_url(document_id: str) -> str:
    base = (
        (os.getenv("FEISHU_DOCX_BASE_URL") or "https://ai.feishu.cn/docx")
        .strip()
        .rstrip("/")
    )
    return f"{base}/{document_id}"


def upload_md_to_docx(md_file: Path, date: str) -> None:
    if not md_file.exists():
        raise FileNotFoundError(md_file)
    logger.info(f"准备上传 Markdown 文件: {md_file}")
    folder_token = (os.getenv("FEISHU_DOCX_FOLDER_TOKEN") or "").strip()
    if not folder_token:
        raise FeishuDriveUploadError("缺少 FEISHU_DOCX_FOLDER_TOKEN 环境变量")

    os.environ["FEISHU_DOCX_CONTENT_TYPE"] = "markdown"

    try:
        document_id = upload_file(
            file_path=str(md_file), file_name=md_file.name, parent_node=folder_token
        )
        docx_url = _build_docx_url(document_id)
        logger.success(f"写入成功 document_id={document_id} url={docx_url}")
    except FeishuDriveUploadError as e:
        logger.exception(f"写入 Docx 失败: {e}")


def main():
    # 使用代码顶部配置的参数
    md_file = Path(MD_FILE_PATH)
    date = REPORT_DATE

    logger.info(f"开始执行上传任务: 日期={date}, 文件={md_file}")
    upload_md_to_docx(md_file, date)


if __name__ == "__main__":
    main()
