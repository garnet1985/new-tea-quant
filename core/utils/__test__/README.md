# Utils 模块单元测试

## 测试文件结构

```
core/utils/__test__/
├── __init__.py
├── test_deterministic_random.py  # math 确定性随机
└── test_date_utils.py            # 日期工具类测试
```

图标测试见 ``core/infra/cmd_layout/__test__/test_icon.py``。

## 运行测试

```bash
pytest core/utils/__test__/ -v
```
