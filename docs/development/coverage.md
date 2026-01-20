# 测试覆盖率配置说明

## 📊 覆盖率报告生成

### 本地生成 HTML 报告

```bash
# 生成 HTML 覆盖率报告
pytest --cov=core --cov-report=html --cov-config=.coveragerc $(find core -type d -name "__test__" | tr '\n' ' ')

# 查看报告
open htmlcov/index.html  # Mac
# 或
xdg-open htmlcov/index.html  # Linux
```

### 生成终端报告

```bash
# 生成终端覆盖率报告
pytest --cov=core --cov-report=term --cov-config=.coveragerc $(find core -type d -name "__test__" | tr '\n' ' ')
```

## 🌐 开源项目覆盖率展示方式

### 方式 1：使用 Coverage 服务（推荐）

大多数开源项目使用 CI/CD + Coverage 服务来展示覆盖率：

1. **Codecov** (https://codecov.io)
   - 支持 GitHub、Gitee
   - 自动生成 badge 和详细报告
   - 在 README 中显示：`![codecov](https://codecov.io/gh/username/repo/branch/main/graph/badge.svg)`

2. **Coveralls** (https://coveralls.io)
   - 类似 Codecov，提供覆盖率跟踪

3. **GitHub Actions 集成示例**：

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests with coverage
        run: |
          pytest --cov=core --cov-report=xml --cov-config=.coveragerc $(find core -type d -name "__test__" | tr '\n' ' ')
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: unittests
```

### 方式 2：GitHub Pages 托管 HTML 报告（可选）

如果确实需要通过 GitHub Pages 托管 HTML 报告：

1. **通过 CI 自动生成和部署**（推荐）：
   - 在 CI 中生成 `htmlcov/`
   - 部署到 `gh-pages` 分支
   - 不需要提交 `htmlcov/` 到主分支

2. **手动提交**（不推荐）：
   - 如果必须手动提交，可以：
     - 在 `.gitignore` 中注释掉 `htmlcov/`
     - 手动生成并提交 HTML 报告
   - **缺点**：会导致仓库变大、历史混乱、合并冲突

## ⚙️ 当前配置

- ✅ `.coverage` - 已忽略（SQLite 数据库文件）
- ✅ `htmlcov/` - 已忽略（HTML 报告目录）
- ✅ `.coveragerc` - 配置文件，已提交到仓库

## 📝 建议

对于开源项目，**推荐使用方式 1（Coverage 服务）**：
- ✅ 自动化，无需手动操作
- ✅ 提供历史趋势和详细报告
- ✅ 在 README 中显示 badge
- ✅ 不污染仓库历史

如果需要 HTML 报告，建议通过 CI 自动生成和部署到 GitHub Pages，而不是手动提交到主分支。
