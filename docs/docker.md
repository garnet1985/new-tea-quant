# Docker 运行说明

可选的本地 / 单机 OOTB 环境：**`Dockerfile`** 与 **`docker-compose.yml`** 在仓库根目录；日常开发更常用本机 `venv` + `python launcher.py` / `python cli.py`。CI 会对 compose 做 `config` 校验并对 `Dockerfile` 执行 `docker build`。

命令均在**仓库根目录**执行。

## 前置

- 已安装 [Docker](https://docs.docker.com/get-docker/) 与 [Docker Compose](https://docs.docker.com/compose/)（Docker Desktop 通常已包含 Compose V2）。

## 一次性构建并启动

```bash
docker compose up -d --build
```

默认**只启动 `postgres`**（端口 `5432:5432`，数据卷 `ntq_pgdata`）。应用服务 `ntq` 带 `profiles: [ntq]`，避免 `compose up` 时立刻跑完退出。

数据库就绪后，首次建议在应用容器内跑 CLI 安装：

```bash
docker compose --profile ntq run --rm ntq python install.py
```

查看用户 CLI：

```bash
docker compose --profile ntq run --rm ntq python cli.py --help
```

## 日常用法（容器内）

- **进入 shell**：

  ```bash
  docker compose --profile ntq run --rm ntq bash
  ```

  容器内常用：

  ```bash
  python cli.py -h
  python cli.py r stock_list          # renew 等（见 cli.py -h）
  python launcher.py                  # UI 安装引导 / 启动（需按 README 配置）
  ```

- **单次命令**（不进 shell）：

  ```bash
  docker compose --profile ntq run --rm ntq python cli.py -h
  ```

## 数据库与配置

- Compose 已设置与框架一致的 `DB_POSTGRESQL_*`（见 `docker-compose.yml`），会覆盖 `core/default_config` 里的 `localhost` 等默认值。
- 宿主机 **`./userspace`** 挂载到容器 **`/app/userspace`**；敏感信息勿提交（见 `.gitignore`）。
- 默认开发密码为 `ntq_dev`，**上线或公网前务必修改**，并勿把 `5432` 暴露到公网。

## 仅构建镜像

```bash
docker build -t new-tea-quant:local .
```

镜像默认 `CMD` 为 `python cli.py --help`；实际任务用 `docker compose --profile ntq run ...` 覆盖命令。

## 说明

- 容器内已设 `NTQ_SKIP_AUTO_VENV=1`，避免入口脚本再切本机 `venv/`。
- 演示数据、第三方 Token（如 Tushare）仍按根目录 `README.md` 与 `userspace/` 文档自行配置；镜像不含付费行情数据。

## Apple Silicon（M 系列）

若 x86 镜像兼容有问题，可尝试：

```bash
docker build --platform linux/amd64 -t new-tea-quant:local .
```
