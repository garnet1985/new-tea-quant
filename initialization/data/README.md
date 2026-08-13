# 初始化数据包目录

## 进 Git 的文件（安装用）

| 文件 | 说明 |
|------|------|
| `data_demo.zip` | **固定文件名**，`python dev-cli.py -ex` 每次覆盖，提交时只更新这一份 |
| `data_demo.meta.json` | 小包：记录版本、股票数、日期窗（便于核对） |
| `example_*.zip` | 可选：体积更小的体验包 |

**不要**提交 `data_v0.3.3_500_....zip` 这类带版本号的副本（可用 `dev-cli -ex -- --tagged` 本地留档，已 gitignore）。

## 打包

```bash
python dev-cli.py -ex
git add initialization/data/data_demo.zip initialization/data/data_demo.meta.json
git commit -m "chore: refresh demo data"
```

若曾把 `data_v*.zip` 提交进仓库，先从索引移除（不删本地文件）：

```bash
git rm --cached initialization/data/data_v*.zip 2>/dev/null || true
```

## 安装

本目录内**只能有 1 个**非 `example_*` 的 zip 参与导入（即 `data_demo.zip`）。然后：

```bash
python core/infra/setup/core/steps/import_data/install.py
```

## 远端仓库已经因多个 zip 变大

Git 会保留历史里的旧 blob；要缩小 clone 体积需一次性清理历史（与协作者协调后 force push）：

```bash
git filter-repo --path-glob 'initialization/data/data_v*.zip' --invert-paths
```

之后只维护 `data_demo.zip` 即可；每次重打包仍会在**新提交**里换一个 zip blob（约 8MB），但不会像多个文件名那样叠 N 份。
