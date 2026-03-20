import os
import uuid
import threading
from datetime import datetime, timezone, timedelta

from flask import Flask, render_template, request, jsonify
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from riot_service import get_player_analysis, get_player_analysis_incremental

# ================================================================
#  APP, CACHE & LIMITER
# ================================================================

app = Flask(__name__)

app.config["CACHE_TYPE"]            = "FileSystemCache"
app.config["CACHE_DIR"]             = os.path.join(os.path.dirname(__file__), ".cache")
app.config["CACHE_DEFAULT_TIMEOUT"] = 60 * 60 * 24 * 30  # 30 dias
app.config["CACHE_THRESHOLD"]       = 5000

cache = Cache(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

VALID_REGIONS   = {"americas", "europe", "asia", "sea"}
UPDATE_COOLDOWN = timedelta(hours=2)

# ================================================================
#  JOB STORE (em memória — sobrevive dentro do mesmo worker)
# ================================================================

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()

def _new_job() -> str:
    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {
            "status":   "pending",
            "step":     "Iniciando...",
            "current":  0,
            "total":    0,
            "result":   None,
            "error":    None,
        }
    return job_id

def _update_job(job_id: str, **kwargs):
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id].update(kwargs)

def _get_job(job_id: str) -> dict | None:
    with _jobs_lock:
        return dict(_jobs.get(job_id, {}))

def _cleanup_old_jobs():
    """Remove jobs com mais de 10 minutos para não vazar memória."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    with _jobs_lock:
        to_delete = [
            jid for jid, j in _jobs.items()
            if j.get("status") in ("done", "error")
            and datetime.fromisoformat(j.get("finished_at", datetime.now(timezone.utc).isoformat())) < cutoff
        ]
        for jid in to_delete:
            del _jobs[jid]

# ================================================================
#  HELPERS DE CACHE
# ================================================================

def _cache_key(name: str, tag: str, region: str) -> str:
    return f"lol:{name.lower()}:{tag.lower()}:{region.lower()}"

def _is_stale(timestamp_iso: str) -> bool:
    cached_at = datetime.fromisoformat(timestamp_iso)
    if cached_at.tzinfo is None:
        cached_at = cached_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - cached_at > UPDATE_COOLDOWN

# ================================================================
#  WORKER — roda em thread separada
# ================================================================

def _run_analysis(job_id: str, name: str, tag: str, region: str, force: bool):
    """Executa a análise em background e atualiza o job store."""

    def on_progress(step: str, message: str, current: int, total: int):
        _update_job(job_id, step=message, current=current, total=total)

    key    = _cache_key(name, tag, region)
    cached = cache.get(key)

    try:
        # Caso 1: cache fresco
        if cached and not force and not _is_stale(cached["timestamp"]):
            print(f"[CACHE HIT] {name}#{tag}")
            _update_job(job_id, status="done", result=cached["result"],
                        finished_at=datetime.now(timezone.utc).isoformat())
            return

        # Caso 2: cache stale ou force
        if cached:
            action = "FORCE" if force else "STALE"
            print(f"[CACHE {action}] {name}#{tag} — update incremental")
            updated = get_player_analysis_incremental(
                name            = name,
                tag             = tag,
                region          = region,
                cached_matches  = cached["matches_raw"],
                latest_match_id = cached["latest_match_id"],
                patch           = cached["patch"],
                puuid_cached    = cached["puuid"],
                profile_icon_id = cached["profile_icon_id"],
                on_progress     = on_progress,
            )
            if updated is None:
                cached["timestamp"] = datetime.now(timezone.utc).isoformat()
                cache.set(key, cached)
                _update_job(job_id, status="done", result=cached["result"],
                            finished_at=datetime.now(timezone.utc).isoformat())
                return

            cache.set(key, updated)
            _update_job(job_id, status="done", result=updated["result"],
                        finished_at=datetime.now(timezone.utc).isoformat())
            return

        # Caso 3: busca completa
        print(f"[CACHE MISS] {name}#{tag} — busca completa")
        payload = get_player_analysis(name, tag, region, on_progress=on_progress)
        cache.set(key, payload)
        _update_job(job_id, status="done", result=payload["result"],
                    finished_at=datetime.now(timezone.utc).isoformat())

    except ValueError as e:
        _update_job(job_id, status="error", error=str(e),
                    finished_at=datetime.now(timezone.utc).isoformat())
    except Exception as e:
        print(f"[JOB ERROR] {job_id}: {e}")
        _update_job(job_id, status="error", error="Erro interno no servidor. Tente novamente.",
                    finished_at=datetime.now(timezone.utc).isoformat())

# ================================================================
#  ROUTES
# ================================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/analyze", methods=["POST"])
@limiter.limit("5 per minute")
def analyze():
    _cleanup_old_jobs()

    data   = request.get_json(silent=True) or {}
    name   = str(data.get("playerName", "")).strip()[:64]
    tag    = str(data.get("playerTag",  "")).strip()[:32]
    region = str(data.get("region",     "")).strip().lower()
    force  = bool(data.get("force", False))

    if not name or not tag:
        return jsonify({"error": "Nome e tag sao obrigatorios."}), 400
    if region not in VALID_REGIONS:
        return jsonify({"error": "Regiao invalida."}), 400

    job_id = _new_job()
    thread = threading.Thread(
        target=_run_analysis,
        args=(job_id, name, tag, region, force),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id}), 202


@app.route("/status/<job_id>", methods=["GET"])
def status(job_id: str):
    job = _get_job(job_id)
    if not job:
        return jsonify({"error": "Job nao encontrado."}), 404

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
    return jsonify({"error": "Muitas requisicoes. Aguarde um momento e tente novamente."}), 429


if __name__ == "__main__":
    app.run(debug=True)