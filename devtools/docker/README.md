# Docker 运行说明

## 前置

- 已安装 [Docker](https://docs.docker.com/get-docker/) 与 [Docker Compose](https://docs.docker.com/compose/)（Docker Desktop 通常已包含 Compose V2）。

## 一次性构建并启动

在**仓库根目录**（与 `docker-compose.yml` 同级）执行：

```bash
docker compose up -d --build
```

默认**只启动 `postgres`**（端口映射 `5432:5432`，数据卷 `ntq_pgdata`）。`ntq` 服务带 `profiles: [ntq]`，避免一启动就跑完命令退出。

数据库就绪后，首次建议执行一键安装（在应用容器里跑 `install.py`）：

```bash
docker compose --profile ntq run --rm ntq python install.py
```

查看 CLI：

```bash
docker compose --profile ntq run --rm ntq python start-cli.py --help
```

## 日常用法

- **进入应用容器 shell**：

  ```bash
  docker compose --profile ntq run --rm ntq bash
  ```

  在容器内：

  ```bash
  python start-cli.py scan
  python start-cli.py simulate
  ```

- **单次命令**（不进入 shell）：

  ```bash
  docker compose --profile ntq run --rm ntq python start-cli.py scan
  ```

## 数据库与配置

- Compose 里已为 NTQ 设置与框架一致的环境变量（见 `docker-compose.yml` 中 `DB_POSTGRESQL_*`），会覆盖 `core/default_config` 里的 `localhost` 等默认值。
- 宿主机目录 **`./userspace`** 挂载到容器 **`/app/userspace`**，本地策略与配置会持久化；敏感信息仍勿提交到 Git（见仓库 `.gitignore`）。
- 默认开发密码为 `ntq_dev`，**上线或公网前务必修改** `postgres` 服务的环境变量与 `DB_POSTGRESQL_PASSWORD`，并勿暴露 `5432` 到公网。

## 仅构建镜像（不启动 Compose）

```bash
docker build -t new-tea-quant:local .
```

## 说明

- 容器内已设置 `NTQ_SKIP_AUTO_VENV=1`，避免 `start-cli.py` 再尝试切换到本机 `venv/`。
- 演示数据、第三方 Token（如 Tushare）仍需按仓库 `README.md` 与 `userspace/` 下文档自行配置；镜像不包含付费行情数据。
- 仓库 CI 会对 `docker-compose.yml` 做 `config` 校验并对 `Dockerfile` 执行 `docker build`，避免镜像长期无法构建。

## Apple Silicon（M 系列）说明

若本机构建或运行 x86 镜像遇到兼容问题，可尝试：

```bash
docker build --platform linux/amd64 -t new-tea-quant:local .
```

或选用官方多架构基础镜像时的后续说明（以你本机 Docker 版本为准）。
