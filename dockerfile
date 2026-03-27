# Base image using Python 3.12 slim for a smaller footprint
FROM python:3.12-slim

# Create a system group and user for security (avoiding root execution)
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup --home /home/appuser appuser
    
# Set the working directory for the application
WORKDIR /app

# Copy requirements and install dependencies without cache to reduce image size
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application source code
COPY . .

# Create cache directory and set proper permissions for the non-root user
RUN mkdir -p /tmp/cache && chown -R appuser:appgroup /tmp/cache

# Switch to the non-privileged user
USER appuser

# Expose the application port
EXPOSE 8000

# Command to start the application using Gunicorn with a custom configuration
CMD ["gunicorn", "-c", "gunicorn.conf.py", "server.wsgi:app"]