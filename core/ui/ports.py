"""UI 栈端口约定。

- 开发（``launcher.py -d`` / ``dev-cli -ui``）：浏览器入口 ``UI_DEV_PORT``（8000，CRA dev server）；
  BFF API 在 ``UI_PROD_PORT``（8888），由 ``fed/package.json`` 的 ``proxy`` 转发，勿单独访问 8888。
- 生产（``launcher.py``）：唯一入口 ``UI_PROD_PORT``（8888，BFF 托管 fed/build）。

启动任一种模式前会清掉 8000/8888，避免 dev/prod 双栈并存。
"""

UI_DEV_PORT = 8000
UI_PROD_PORT = 8888

# 兼容旧名
FED_DEV_PORT = UI_DEV_PORT
BFF_DEFAULT_PORT = UI_PROD_PORT

ALL_UI_PORTS = (UI_DEV_PORT, UI_PROD_PORT)
