# New Tea Quant — 运行环境镜像（仓库根目录构建）
# 用法见 docker/README.md

FROM python:3.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    NTQ_SKIP_AUTO_VENV=1

WORKDIR /app

# 多数依赖有 wheel；若 pip 在部分平台需编译，再安装 build-essential / libpq-dev
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# 默认仅展示 CLI；实际任务请用 docker compose run 覆盖 command
CMD ["python", "start-cli.py", "--help"]
