# ArXiv AI Agent

一个基于 AI 的 ArXiv 论文每日速递工具。每天自动帮你抓取最新论文、翻译成中文、打上标签、评估推荐度，最后生成一份漂亮的日报推送到飞书。

做研究的朋友都知道，ArXiv 每天更新的论文太多了，根本看不过来。这个工具就是用来解决这个痛点的——让 AI 帮你做第一轮筛选，你只需要看它觉得值得推荐的就行。

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live-success)](https://tobychain.github.io/arXiv-ai-Agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## 功能特性

- **自动抓取**：每日自动获取 ArXiv 最新论文（支持多个分类）
- **智能翻译**：使用 DeepSeek 等大模型翻译摘要为中文
- **智能分析**：自动提取关键词、识别子主题、评估推荐程度
- **生成日报**：输出结构化 Markdown 文档，方便阅读和归档
- **飞书集成**：上传到云空间 + 群机器人推送，手机电脑都能看

## 项目结构

```
arXiv-ai-Agent/
├── main.py                    # 主程序入口
├── arxiv_subjects.py          # ArXiv 分类配置
├── requirements.txt           # Python 依赖
├── .env.example               # 环境变量示例
├── .env                       # 环境变量（需手动创建）
├── CHANGELOG.md               # 版本变更记录
│
├── src/                       # 源代码
│   ├── config/                # 配置管理
│   ├── models/                # 数据模型
│   ├── core/                  # 核心业务逻辑（评分、调度、查询）
│   ├── pipeline/              # 数据处理流水线
│   ├── tools/                 # 外部服务调用（LLM、Jina、飞书）
│   ├── database/              # 数据层（ORM 模型、仓储）
│   └── utils/                 # 通用工具
│
├── web/                       # Streamlit Web 界面
│   └── app.py
│
├── scripts/                   # 可执行脚本
│   ├── run.sh                 # 启动脚本
│   └── dev/                   # 开发工具脚本
│
├── docs/                      # 文档
│   ├── guides/                # 使用指南
│   └── archive/               # 历史文档归档
│
├── output/                    # 生成的 Markdown 日报
├── database/                  # 数据库文件
│   └── arxiv_papers.db
└── logs/                      # 日志文件
```

## 快速开始

### 1. 环境配置

首先，复制 `.env.example` 文件为 `.env`，然后根据实际情况填写相关配置：

```bash
cp .env.example .env
```

主要配置项包括：

- **LLM API**: `API_KEY`, `BASE_URL`, `MODEL_NAME`
  - 支持 OpenAI 格式接口（比如 DeepSeek、通义千问、智谱等）
  - DeepSeek 价格便宜，推荐使用：https://platform.deepseek.com/

- **Jina Reader**: `JINA_API_KEY`
  - Jina Reader 是个非常好用的网页解析工具，可以把任何 URL 转成 LLM 友好的 Markdown
  - 获取 API Key：https://jina.ai/reader
  - 免费额度足够日常使用

- **飞书机器人**: `FEISHU_WEBHOOK_URL`, `FEISHU_SECRET`
  - 在飞书群里添加自定义机器人，获取 Webhook 地址
  - 配置文档：https://www.feishu.cn/hc/zh-CN/articles/807992406756-webhook-%E8%A7%A6%E5%8F%91%E5%99%A8

- **飞书开放平台**: `FEISHU_APP_ID`, `FEISHU_APP_SECRET`
  - 用于上传文件到飞书云空间
  - 创建企业自建应用：https://open.feishu.cn/
  - 需要开通「云文档」权限

- **飞书云文档**: `FEISHU_DRIVE_PARENT_NODE`, `FEISHU_DRIVE_BASE_URL`
  - 指定上传文件的目标文件夹（可选）
  - 导入指南：https://open.feishu.cn/document/server-docs/docs/drive-v1/import_task/import-user-guide

### 2. 安装依赖

本项目使用 `uv` 进行 Python 包管理。依赖已在项目根目录的 `pyproject.toml` 中配置。如果你还没装 uv，强烈推荐试试，比 pip 快很多：

```bash
# 如果没有安装 uv，先安装
curl -LsSf https://astral.sh/uv/install.sh | sh

# uv 会自动使用 pyproject.toml 中的依赖
```

### 3. 运行任务

配置完成后，可以先手动运行一次测试：

```bash
# 使用 uv 执行每日论文抓取和处理
uv run python main.py

# 或使用提供的快捷脚本
bash scripts/run.sh
```

第一次运行可能会比较慢（取决于当天的论文数量），耐心等待即可。运行完成后，你应该能在飞书群里收到推送消息。

## 核心模块说明

项目采用模块化设计，各个功能独立封装，方便二次开发和定制。

### src/tools/call_llm.py - LLM 调用

负责调用大模型 API 进行论文分析。这是整个项目的核心，它会：
- 翻译英文摘要为中文
- 生成 2-3 句话的精简版本
- 提取关键词和识别子领域
- 根据你设定的标准评估推荐程度

**自定义推荐标准的话，重点改这个文件**（详见下文）。

### src/tools/call_jina.py - 网页解析

使用 Jina Reader API 抓取 ArXiv 列表页面。Jina Reader 可以把任何网页转成干净的 Markdown，非常适合给 LLM 做输入。

### src/tools/call_feishu_card.py - 飞书推送

负责将日报以交互式卡片的形式推送到飞书群。卡片格式美观，带按钮链接，可以直接跳转到云文档查看完整日报。

### arxiv_subjects.py - 主题配置

定义要抓取的 ArXiv 分类。默认是 cs.AI（人工智能），你可以根据自己的研究方向添加其他分类，比如：
- cs.LG - 机器学习
- cs.CV - 计算机视觉
- cs.CL - 计算语言学（NLP）
- cs.RO - 机器人
- stat.ML - 统计机器学习

## 定时任务设置

手动测试没问题后，就可以设置定时任务了。使用 cron 让脚本每天自动运行：

```bash
# 编辑 crontab
crontab -e

# 添加以下内容（每天早上 9:00 执行）
0 9 * * * cd /path/to/arxiv-ai-agent && uv run python main.py >> /path/to/arxiv-ai-agent/logs/cron.log 2>&1
```

**注意事项**：
- 把 `/path/to/arxiv-ai-agent` 替换成你的实际路径
- ArXiv 通常在北京时间凌晨更新，建议设置在早上 8-10 点执行
- 日志会输出到 `logs/cron.log`，方便排查问题
- 确保服务器/电脑在设定时间是开机状态

## 日志系统

项目使用 `loguru` 进行日志管理，所有日志会自动输出到控制台并按级别着色：

- `logger.info()` - 一般信息（蓝色）
- `logger.success()` - 成功信息（绿色）
- `logger.warning()` - 警告信息（黄色）
- `logger.error()` - 错误信息（红色）
- `logger.exception()` - 异常信息（红色，包含堆栈）

日志输出示例：
```
2025-12-17 10:30:45 | INFO     | 正在请求 Jina Reader API: https://r.jina.ai/...
2025-12-17 10:30:46 | SUCCESS  | 共提取到 154 篇文献。
2025-12-17 10:30:50 | INFO     | [1/10] 处理: Context-Picker...
2025-12-17 10:31:00 | SUCCESS  | JSON 数据已保存: database/2025-12-17.json
```

## 自定义推荐标准

这个项目最有意思的地方在于，你可以根据自己的研究方向定制推荐标准。比如我目前的设置是：

- 关注大模型（LLM）相关的工作
- 特别关注医学 LLM 的进展
- 优先推荐来自头部厂商（Google、Meta、OpenAI 等）的研究

**如果你想修改推荐标准**，只需要编辑 `src/tools/call_llm.py` 文件中的 `translate_abstract` 方法，找到第 40-41 行的 prompt：

```python
f"5. 推荐程度：作为一名大模型算法工程师,请给出推荐程度（极度推荐、很推荐、推荐、一般推荐、不推荐）。\n"
f"   - 特别注意：如果涉及医学LLM（Medical LLM）的进展，或来自头部互联网厂商（如Google, Meta, OpenAI, DeepMind, 百度, 腾讯, 阿里, 字节等）的研究，请标记为"极度推荐"。\n\n"
```

你可以根据自己的需求修改这段文字，比如：
- 如果你做计算机视觉，可以改成「特别关注 CV 领域的 SOTA 模型」
- 如果你做强化学习，可以改成「优先推荐 RL 和多智能体系统相关工作」
- 如果你在做具身智能，可以改成「重点关注机器人和具身智能的突破」

修改后，LLM 就会按照你的标准来评估论文了。这也是为什么我把 LLM 的调用单独抽出来的原因——方便大家按需定制。

## 飞书消息推送

每次运行完成后，会自动向飞书群推送一张交互式卡片，包含：
- 报告日期
- 论文数量统计
- 云文档链接（点击即可查看完整日报）

卡片样式美观，手机和电脑端都能很好地展示。点击卡片上的按钮就能直接跳转到飞书云文档查看详细内容

## 常见问题

### 为什么用飞书不用企业微信？

主要是飞书的云空间 API 比较好用，可以直接上传 Markdown 文件并生成在线文档。企业微信也可以，但需要额外的转换步骤。

### 能不能支持其他论文源？

理论上可以，只要网站有列表页，Jina Reader 都能解析。但 ArXiv 的格式比较统一，其他来源可能需要调整解析逻辑。

### 每天会抓取多少篇论文？

这取决于 ArXiv 当天的更新量，通常 cs.AI 类别每天会有 100-300 篇新论文。脚本默认抓取最多 250 篇，可以在 `arxiv_daily.py` 中修改这个参数。

### LLM API 费用大概多少？

以 GPT-5-mini 为例，如果每天处理 200 篇，月成本大约 4-5 元。如果觉得贵，可以只翻译「极度推荐」和「很推荐」的论文。

## 写在最后

这个项目是我自己用来追论文的工具，开源出来希望能帮到同样需要每天看 ArXiv 的朋友。代码写得比较随意，如果有 bug 或者建议，欢迎提 issue 或 PR。

另外，如果你觉得这个项目有用，可以给个 Star，这对我是最大的鼓励。

## License

MIT
