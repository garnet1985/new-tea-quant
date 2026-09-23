# New Tea Quant — 运行环境镜像（仓库根目录构建）
# 用法见 docs/docker.md

FROM python:3.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    NTQ_SKIP_AUTO_VENV=1

WORKDIR /app

# 依赖安装走 Utils.pkg（国内清华 / npmmirror，国外官方源）。
COPY requirements.txt .
COPY core/__init__.py /app/core/__init__.py
COPY core/infra/__init__.py /app/core/infra/__init__.py
COPY core/infra/utils /app/core/infra/utils
RUN python -c "import subprocess,sys; from core.infra.utils import Utils; f=Utils.pkg.pip_args(); raise SystemExit(subprocess.call([sys.executable,'-m','pip','install',*f,'--upgrade','pip']) or subprocess.call([sys.executable,'-m','pip','install',*f,'-r','requirements.txt']))"

COPY . .

# 默认仅展示 CLI；实际任务请用 docker compose run 覆盖 command
CMD ["python", "cli.py", "--help"]
