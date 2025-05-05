import multiprocessing
import os

# Gunicorn configuration for optimal FastAPI performance
# This helps prevent duplicate processing issues

# Worker Management
# Use 2-4 workers per CPU core
# For more guidance: https://docs.gunicorn.org/en/latest/design.html#how-many-workers
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))

# Worker class - use Uvicorn's worker
worker_class = "uvicorn.workers.UvicornWorker"

# Connection handling
worker_connections = 1000
keepalive = 5
timeout = 120
graceful_timeout = 30

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"

# Prevent duplicate processing by setting a proper worker timeout
# and pre-fork model
preload_app = True
max_requests = 1000
max_requests_jitter = 100  # Adds randomness to prevent all workers restarting simultaneously

# Prevent workers from reloading on file changes
reload = False

# Prevent accidental file double-binding
bind = os.getenv("BIND", "0.0.0.0:8000") 