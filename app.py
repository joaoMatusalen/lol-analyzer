from flask import Flask, render_template, request, jsonify
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from server.jobs import start_job, get_job, cleanup_old_jobs

# ── App setup ────────────────────────────────────────────────────

app = Flask(__name__)

app.config["CACHE_TYPE"]            = "FileSystemCache"
app.config["CACHE_DIR"]             = "/tmp/cache"
app.config["CACHE_DEFAULT_TIMEOUT"] = 60 * 60 * 24 * 30   # 30 days
app.config["CACHE_THRESHOLD"]       = 5000

cache = Cache(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

VALID_REGIONS = {"americas", "europe", "asia", "sea"}

# ── Routes ───────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/analyze", methods=["POST"])
@limiter.limit("5 per minute")
def analyze():
    cleanup_old_jobs()

    body   = request.get_json(silent=True) or {}
    name   = str(body.get("playerName", "")).strip()[:16]
    tag    = str(body.get("playerTag",  "")).strip()[:7]
    region = str(body.get("region",     "")).strip().lower()
    force  = bool(body.get("force", False))

    if tag.startswith('#'):
        tag = tag[1:]   

    if not name or not tag:
        return jsonify({"error": "Nome e tag são obrigatorios."}), 400
    if region not in VALID_REGIONS:
        return jsonify({"error": "Região invalida."}), 400

    job_id = start_job(name, tag, region, force, cache)
    return jsonify({"job_id": job_id}), 202


@app.route("/status/<job_id>", methods=["GET"])
def status(job_id: str):
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Job não encontrado."}), 404

    response = {
        "status":  job["status"],
        "step":    job["step"],
        "current": job["current"],
        "total":   job["total"],
    }
    if job["status"] == "done":
        response["result"] = job["result"]
    elif job["status"] == "error":
        response["error"] = job["error"]

    return jsonify(response)


@app.errorhandler(429)
def rate_limit_handler(e):
    return jsonify({"error": "Muitas requisições. Aguarde e tente novamente."}), 429


if __name__ == "__main__":
    app.run(debug=True)