FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖（含 streamlit 和 python-dotenv）
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir streamlit python-dotenv

# 复制项目文件
COPY . .

# 创建结果目录
RUN mkdir -p /app/results /app/tradingagents/dataflows/data_cache

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV TRADINGAGENTS_RESULTS_DIR=/app/results

# 启动脚本：Railway 会注入 $PORT，Streamlit 必须监听该端口
CMD streamlit run app.py \
    --server.port=${PORT:-8501} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
