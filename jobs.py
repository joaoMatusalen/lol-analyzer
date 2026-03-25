import uuid
import threading
import logging
from datetime import datetime, timezone, timedelta

from flask_caching import Cache

from api import get_player_analysis, get_player_analysis_incremental

logger = logging.getLogger(__name__)

# ── Job store ─────────────────────────────────────────────────────

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def new_job() -> str:
    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {
            "status":      "pending",
            "step":        "Iniciando...",
            "current":     0,
            "total":       0,
            "result":      None,
            "error":       None,
            "finished_at": None,
        }
    return job_id


def update_job(job_id: str, **kwargs) -> None:
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(kwargs)


def get_job(job_id: str) -> dict | None:
    with _lock:
        return dict(_jobs.get(job_id, {}))


def cleanup_old_jobs() -> None:
    """Remove jobs finalizados com mais de 3 minutos."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=3)
    with _lock:
        to_delete = [
            jid for jid, job in _jobs.items()
            if job["status"] in ("done", "error")
            and job["finished_at"]
            and datetime.fromisoformat(job["finished_at"]) < cutoff
        ]
        for jid in to_delete:
            del _jobs[jid]


# ── Worker ────────────────────────────────────────────────────────

def run_analysis(job_id: str, name: str, tag: str, region: str, force: bool, cache: Cache) -> None:
    """Executa a análise em background e atualiza o job store."""

    cache_key = f"lol:{name.lower()}:{tag.lower()}:{region.lower()}"
    cached    = cache.get(cache_key)

    def on_progress(step: str, message: str, current: int, total: int) -> None:
        update_job(job_id, step=message, current=current, total=total)

    def _finish(result: dict) -> None:
        update_job(job_id, status="done", result=result,
                   finished_at=datetime.now(timezone.utc).isoformat())

    def _fail(message: str) -> None:
        update_job(job_id, status="error", error=message,
                   finished_at=datetime.now(timezone.utc).isoformat())

    UPDATE_COOLDOWN = timedelta(hours=2)

    def _is_stale(ts: str) -> bool:
        cached_at = datetime.fromisoformat(ts)
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - cached_at > UPDATE_COOLDOWN

    try:
        # Cache fresco
        if cached and not force and not _is_stale(cached["timestamp"]):
            logger.info(f"[CACHE HIT] {name}#{tag}")
            _finish(cached["result"])
            return

        # Cache stale ou force
        if cached:
            action = "FORCE" if force else "STALE"
            logger.info(f"[CACHE {action}] {name}#{tag}")

            updated = get_player_analysis_incremental(
                name            = name,
                tag             = tag,
                region          = region,
                cached_matches  = cached["matches_raw"],
                latest_match_id_cache = cached["latest_match_id_cache"],
                patch           = cached["patch"],
                puuid_cached    = cached["puuid"],
                profile_icon_id = cached["profile_icon_id"],
                on_progress     = on_progress,
            )

            if updated is None:
                cached["timestamp"] = datetime.now(timezone.utc).isoformat()
                cache.set(cache_key, cached)
                _finish(cached["result"])
                return

            cache.set(cache_key, updated)
            _finish(updated["result"])
            return

        # Busca completa
        logger.info(f"[CACHE MISS] {name}#{tag}")
        payload = get_player_analysis(name, tag, region, on_progress=on_progress)
        cache.set(cache_key, payload)
        _finish(payload["result"])

    except ValueError as e:
        _fail(str(e))
    except Exception as e:
        logger.warning(f"[JOB ERROR] {job_id}: {e}")
        _fail("error.internal")


def start_job(name: str, tag: str, region: str, force: bool, cache: Cache) -> str:
    """Cria um job e dispara a thread. Retorna o job_id."""
    job_id = new_job()
    thread = threading.Thread(
        target=run_analysis,
        args=(job_id, name, tag, region, force, cache),
        daemon=True,
    )
    thread.start()
    return job_id
