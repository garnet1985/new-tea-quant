"""UI 栈端口约定。

- **BFF**（API，开发/生产共用）：``UI_BFF_PORT``（8888）。开发模式下不挂载 ``fed/build``（见 ``NTQ_UI_DEV``）。
- **开发前端**：``UI_DEV_PORT``（8000，CRA）；``/api`` 由 proxy 转发到 :8888。
- **生产前端**：由 BFF :8888 托管 ``fed/build``。

同一时刻只应跑一种 UI 栈（dev 或 prod）；``uk`` 会结束 8000 + 8888 上的 NTQ 进程。
"""

UI_DEV_PORT = 8000
UI_BFF_PORT = 8888

# 兼容旧名
UI_PROD_PORT = UI_BFF_PORT
FED_DEV_PORT = UI_DEV_PORT
BFF_DEFAULT_PORT = UI_BFF_PORT

ALL_UI_PORTS = (UI_DEV_PORT, UI_BFF_PORT)
