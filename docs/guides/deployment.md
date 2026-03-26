# Web 界面部署与共享访问指南

## 🚀 快速启动

### 1. 安装 Streamlit
```bash
pip install streamlit plotly pandas
```

### 2. 启动 Web 服务
```bash
cd /Users/guanbingtao/arXiv-ai-Agent
streamlit run web/app.py
```

启动后你会看到：
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

---

## 🌐 让外部访问的 3 种方案

### 方案一：ngrok 内网穿透（⭐推荐，5分钟搞定）

**适用场景**：临时分享给同事/朋友，不需要服务器

**步骤**：

1. 安装 ngrok
```bash
# macOS
brew install ngrok

# 或使用官网脚本
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok
```

2. 注册 ngrok 账号并获取 authtoken
   - 访问 https://ngrok.com
   - 注册账号，获取 authtoken

3. 配置并启动
```bash
# 配置 token（只需一次）
ngrok config add-authtoken YOUR_AUTHTOKEN

# 启动内网穿透（在另一个终端窗口）
ngrok http 8501
```

4. 分享链接
```
Forwarding  https://xxxx.ngrok-free.app -> http://localhost:8501
```
把这个 https 链接发给任何人都能访问！

**优点**：免费、快速、无需服务器  
**缺点**：每次重启 URL 会变、有流量限制

---

### 方案二：部署到服务器（长期稳定）

**适用场景**：长期提供服务，有固定域名

#### 方法 A：使用 Docker（推荐）

1. 创建 Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
copy requirements.txt .
RUN pip install -r requirements.txt

# 复制代码
copy . .

# 暴露端口
EXPOSE 8501

# 启动命令
CMD ["streamlit", "run", "web/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

2. 构建并运行
```bash
# 构建镜像
docker build -t arxiv-web .

# 运行容器
docker run -d -p 8501:8501 --name arxiv-web arxiv-web
```

3. 使用 Nginx 反向代理（可选）
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

#### 方法 B：直接部署（如阿里云/腾讯云）

```bash
# 1. 购买云服务器（最低配即可，约 50元/月）
# 2. SSH 连接到服务器
ssh root@your-server-ip

# 3. 安装 Python 和依赖
apt update && apt install -y python3-pip
pip3 install -r requirements.txt

# 4. 上传代码（用 scp 或 git）
git clone https://github.com/your-repo/arXiv-ai-Agent.git
cd arXiv-ai-Agent

# 5. 使用 nohup 或 systemd 保持运行
nohup streamlit run web/app.py --server.port=8501 --server.address=0.0.0.0 > web.log 2>&1 &

# 6. 配置防火墙开放 8501 端口
ufw allow 8501
```

**优点**：稳定、可绑定域名、性能可控  
**缺点**：需要服务器、有成本

---

### 方案三：使用 Streamlit Cloud（免费托管）

**适用场景**：免费、简单、无需维护

**步骤**：

1. 将代码推送到 GitHub
```bash
# 初始化 git
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourname/arXiv-ai-Agent.git
git push -u origin main
```

2. 访问 https://streamlit.io/cloud

3. 使用 GitHub 账号登录，点击 "New app"

4. 选择仓库和分支，填入：
   - Main file path: `web/app.py`

5. 点击 Deploy！

6. 获得永久链接：
   `https://yourname-arxiv-ai-agent.streamlit.app`

**优点**：完全免费、自动部署、自带域名  
**缺点**：代码必须公开、有资源限制

---

## 📊 三种方案对比

| 方案 | 成本 | 难度 | 稳定性 | 适用场景 |
|------|------|------|--------|----------|
| **ngrok** | 免费 | ⭐⭐ | 临时 | 快速分享、测试 |
| **自有服务器** | 50-100元/月 | ⭐⭐⭐⭐ | 高 | 长期服务、生产环境 |
| **Streamlit Cloud** | 免费 | ⭐⭐ | 中 | 个人项目、开源项目 |

---

## 🔧 Web 界面功能

### 已实现功能
- ✅ 首页仪表盘（关键指标）
- ✅ 论文搜索（关键词 + 日期筛选）
- ✅ 研究方向分析（8个方向）
- ✅ 热点趋势图表
- ✅ 实时统计分析
- ✅ 论文详情查看
- ✅ CSV 数据导出

### 页面截图预览

```
🏠 首页
├── 关键指标卡片（总数、极度推荐、热门方向、今日新增）
└── 最近高分论文列表

🔍 论文搜索
├── 关键词输入框
├── 日期范围选择
└── 搜索结果列表

📊 研究方向
├── 热门方向柱状图
└── 8 个方向 Tab 切换

🔥 热点趋势
├── 多方向趋势对比
└── 新兴关键词词云

📈 统计分析
├── 推荐等级饼图
├── 子主题分布
├── 时间趋势折线
└── 数据导出按钮
```

---

## 📝 配置文件

创建 `.streamlit/config.toml` 自定义配置：

```toml
[server]
port = 8501
headless = true
enableCORS = false

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"
```

---

## 🎯 推荐方案

根据你的需求：

1. **现在就想给朋友看** → 用 **ngrok**（5分钟搞定）
2. **长期给团队使用** → 用 **自有服务器 + Docker**
3. **开源项目展示** → 用 **Streamlit Cloud**

需要我帮你部署其中任何一种吗？🏠
