import uuid
import threading
import logging
from datetime import datetime, timezone, timedelta

from flask_caching import Cache

from api import get_player_analysis, get_player_analysis_incremental

logger = logging.getLogger(__name__)

# ── In-memory job store ───────────────────────────────────────────

# Dict mapping job_id (UUID string) → job state dict.
# Access is protected by _lock to prevent race conditions between threads.
_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def new_job() -> str:
    """
    Creates a new job entry in the store with 'pending' status.

    Returns:
        A UUID4 string that uniquely identifies the new job.
    """
    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {
            "status":      "pending",
            "step":        "progress.starting",
            "current":     0,
            "total":       0,
            "result":      None,
            "error":       None,
            "finished_at": None,
        }
    return job_id


def update_job(job_id: str, **kwargs) -> None:
    """
    Applies keyword-argument updates to an existing job entry.

    No-ops silently if the job_id is not found (e.g. after cleanup).
    """
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(kwargs)


def get_job(job_id: str) -> dict | None:
    """
    Returns a shallow copy of the job state dict, or an empty dict
    if the job_id does not exist.
    """
    with _lock:
        return dict(_jobs.get(job_id, {}))


def cleanup_old_jobs() -> None:
    """
    Removes completed or failed jobs that finished more than 3 minutes ago.

    Called before each new /analyze request to prevent unbounded memory growth.
    """
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


# ── Background worker ─────────────────────────────────────────────

def run_analysis(job_id: str, name: str, tag: str, region: str, force: bool, cache: Cache) -> None:
    """
    Main worker function executed in a background daemon thread.

    Implements a three-tier cache strategy:
        1. Cache hit (fresh):   Return cached result immediately.
        2. Cache stale / force: Run incremental update and refresh cache.
        3. Cache miss:          Run full analysis and populate cache.

    Progress updates are pushed to the job store via on_progress so the
    frontend polling loop can display them in real time.

    Args:
        job_id: Identifier of the job to update throughout execution.
        name:   Riot game name.
        tag:    Riot tag line.
        region: Routing region.
        force:  When True, skip the freshness check and always update.
        cache:  Flask-Caching instance shared with the main app.
    """
    cache_key = f"lol:{name.lower()}:{tag.lower()}:{region.lower()}"
    cached    = cache.get(cache_key)

    # Helper: push a progress event to the job store
    def on_progress(step: str, message: str, current: int, total: int) -> None:
        update_job(job_id, step=message, current=current, total=total)

    # Helper: mark the job as successfully completed
    def _finish(result: dict) -> None:
        update_job(job_id, status="done", result=result,
                   finished_at=datetime.now(timezone.utc).isoformat())

    # Helper: mark the job as failed with an error message
    def _fail(message: str) -> None:
        update_job(job_id, status="error", error=message,
                   finished_at=datetime.now(timezone.utc).isoformat())

    # Cache entries older than this threshold are considered stale
    UPDATE_COOLDOWN = timedelta(hours=2)

    def _is_stale(ts: str) -> bool:
        """Returns True if the cached timestamp exceeds UPDATE_COOLDOWN."""
        cached_at = datetime.fromisoformat(ts)
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - cached_at > UPDATE_COOLDOWN

    try:
        # ── Tier 1: fresh cache ───────────────────────────────────
        if cached and not force and not _is_stale(cached["timestamp"]):
            logger.info(f"[CACHE HIT] {name}#{tag}")
            _finish(cached["result"])
            return

        # ── Tier 2: stale cache or forced refresh ─────────────────
        if cached:
            action = "FORCE" if force else "STALE"
            logger.info(f"[CACHE {action}] {name}#{tag}")

            updated = get_player_analysis_incremental(
                name                  = name,
                tag                   = tag,
                region                = region,
                cached_matches        = cached["matches_raw"],
                latest_match_id_cache = cached["latest_match_id_cache"],
                patch                 = cached["patch"],
                puuid_cached          = cached["puuid"],
                profile_icon_id       = cached["profile_icon_id"],
                on_progress           = on_progress,
            )

            if updated is None:
                # No new matches — just refresh the timestamp and return cached result
                cached["timestamp"] = datetime.now(timezone.utc).isoformat()
                cache.set(cache_key, cached)
                _finish(cached["result"])
                return

            cache.set(cache_key, updated)
            _finish(updated["result"])
            return

        # ── Tier 3: cache miss — full analysis ────────────────────
        logger.info(f"[CACHE MISS] {name}#{tag}")
        payload = get_player_analysis(name, tag, region, on_progress=on_progress)
        cache.set(cache_key, payload)
        _finish(payload["result"])

    except ValueError as e:
        # Expected errors (account not found, no matches) use i18n keys
        _fail(str(e))
    except Exception as e:
        logger.warning(f"[JOB ERROR] {job_id}: {e}")
        _fail("error.internal")


def start_job(name: str, tag: str, region: str, force: bool, cache: Cache) -> str:
    """
    Creates a job and immediately starts a background daemon thread for it.

    The thread is daemonised so it does not prevent the process from shutting down.

    Args:
        name:   Riot game name.
        tag:    Riot tag line.
        region: Routing region.
        force:  When True, bypass the cache freshness check.
        cache:  Flask-Caching instance to read/write player data.

    Returns:
        The UUID string of the newly created job.
    """
    job_id = new_job()
    thread = threading.Thread(
        target=run_analysis,
        args=(job_id, name, tag, region, force, cache),
        daemon=True,
    )
    thread.start()
    return job_id