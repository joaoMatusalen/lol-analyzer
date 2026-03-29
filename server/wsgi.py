# WSGI entry point used by Gunicorn and other WSGI servers.
# Import the Flask app instance here so the server can locate it.
from app import app

if __name__ == "__main__":
    # For local development only — use Gunicorn in production.
    app.run(debug=False)