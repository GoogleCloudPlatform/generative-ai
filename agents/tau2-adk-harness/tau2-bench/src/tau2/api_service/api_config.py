# Copyright Sierra

# Server binding and timeouts
bind = ["0.0.0.0:8000"]
startup_timeout = 120.0  # Reduced from 500.0
timeout_keep_alive = 30  # Close idle connections after this many seconds
graceful_timeout = 120  # Reduced from 300

# Worker configurations
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"
threads = 8  # Number of threads per worker

# Logging configurations
log_level = "info"  # Options: critical, error, warning, info, debug
access_log = True
use_colors = True

# # SSL/TLS configurations (for HTTPS)
# ssl_keyfile = "path/to/key.pem"  # Path to SSL key file
# ssl_certfile = "path/to/cert.pem"  # Path to SSL certificate file

# Performance and resource limits
limit_concurrency = 1000  # Maximum number of concurrent connections
limit_max_requests = 10000  # Restart workers after this many requests
backlog = 2048  # Maximum number of pending connections

# Application reload (development)
reload = False  # Auto-reload on code changes
reload_dirs = ["app"]  # Directories to watch for changes
