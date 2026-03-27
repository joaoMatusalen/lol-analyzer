FROM python:3.12-slim

RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup --home /home/appuser appuser
    
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /tmp/cache && chown -R appuser:appgroup /tmp/cache

USER appuser

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "server.wsgi:app"]