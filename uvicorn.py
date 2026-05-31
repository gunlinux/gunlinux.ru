workers = 2
backlog = 2048
worker_class = "uvicorn.workers.UvicornWorker"
debug = False
daemon = False
bind = ["0.0.0.0:5000"]

accesslog = "-"
errorlog = "-"
loglevel = "info"
wsgi_app = "main:app"
