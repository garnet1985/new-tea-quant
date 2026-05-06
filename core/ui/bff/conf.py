import os

conf = {
    "DEBUG": False,
    "PORT": 5001,
    "HOST": '127.0.0.1',
    "CORS_ALLOW_ORIGINS": ['http://localhost:3000'],
    "CORS_ALLOW_METHODS": ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    "CORS_ALLOW_HEADERS": ['Content-Type', 'Authorization'],
    "CORS_ALLOW_CREDENTIALS": True,
    "CORS_MAX_AGE": 3600,
    # Werkzeug 开发服务器是否多线程处理并发请求。默认 False，便于在主线程内跑工作台步骤，
    # 与 ProcessWorker 的 signal 注册兼容。需要并发时可设环境变量 BFF_THREADED=1。
    "THREADED": os.environ.get("BFF_THREADED", "").lower() in ("1", "true", "yes"),
}