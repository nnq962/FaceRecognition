# gunicorn.conf.py
bind = "0.0.0.0:9621"
workers = 2
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = False
accesslog = "-"
errorlog = "-"
loglevel = "info"