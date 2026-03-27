import multiprocessing

# ── Workers ───────────────────────────────────────────────────────

# Standard formula: (2 × CPU cores) + 1 for I/O-bound workloads
workers            = multiprocessing.cpu_count() * 2 + 1
# gevent enables async I/O within each worker, suitable for Riot API polling
worker_class       = "gevent"
worker_connections = 100

# ── Server ────────────────────────────────────────────────────────

bind      = "0.0.0.0:8000"
# Generous timeout to accommodate Riot API rate-limit waits (up to 121s)
timeout   = 120
keepalive = 5

# ── Logging ───────────────────────────────────────────────────────

# Send both access and error logs to stdout/stderr for container environments
accesslog = "-"
errorlog  = "-"
loglevel  = "info"