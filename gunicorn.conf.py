import multiprocessing

# Workers
workers         = multiprocessing.cpu_count() * 2 + 1
worker_class    = "gevent"
worker_connections = 100

# Servidor
bind            = "0.0.0.0:5000"
timeout         = 120
keepalive       = 5

# Logs
accesslog       = "-"   # stdout
errorlog        = "-"   # stderr
loglevel        = "info"
