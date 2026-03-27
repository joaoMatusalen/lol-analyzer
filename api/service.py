import logging
from datetime import datetime, timezone
from collections import defaultdict

from .client import get_latest_patch, get_champion_classes, summoner_info
from .parser import collect_player_matches, convert_to_dataframe, ROUTING_TO_PLATFORM, MAX_MATCHES
from .analytics import (
    analyze_general_results,
    analyze_most_played_champion,
    analyze_daily_evolution,
    analyze_lane_stats,
    analyze_time_patterns,
    analyze_class_stats,
    analyze_game_modes,
    analyze_match_history,
)

logger = logging.getLogger(__name__)


def _build_result(matches_raw: list, name: str, tag: str, region: str, patch: str) -> dict:
    """
    Transforms a raw list of match dicts into the full frontend payload.

    Attaches champion class tags to the DataFrame before running analytics,
    so that class-based charts can filter by champion type.
    This function is shared between full and incremental analysis flows.

    Args:
        matches_raw: List of parsed match dicts from the parser layer.
        name:        Player's Riot game name.
        tag:         Player's Riot tag line.
        region:      Routing region string.
        patch:       Current game patch version (used for Data Dragon URLs).

    Returns:
        Dict with player_info, stats, chart data and match history,
        ready to be serialised and sent to the frontend.
    """
    df = convert_to_dataframe(matches_raw)

    # Enrich the DataFrame with champion class tags from Data Dragon
    class_map      = get_champion_classes(patch)
    df["classTag"] = df["championName"].map(class_map).fillna("Unknown")

    general  = analyze_general_results(df)
    champion = analyze_most_played_champion(df)

    return {
        "player_info":      {"name": name, "tag": tag, "region": region},
        "geral_matchs":     general,
        "champion_results": champion,
        # Data Dragon URL for the most-played champion's square portrait
        "champion_img":     f"https://ddragon.leagueoflegends.com/cdn/{patch}/img/champion/{champion['champion']}.png",
        "match_history":    analyze_match_history(df, patch),
        "charts": {
            "daily":      analyze_daily_evolution(df),
            "lanes":      analyze_lane_stats(df),
            "time":       analyze_time_patterns(df),
            "classes":    analyze_class_stats(df),
            "game_modes": analyze_game_modes(df),
        },
    }


def get_player_analysis(name: str, tag: str, region: str, on_progress=None) -> dict:
    """
    Performs a full analysis from scratch, fetching up to MAX_MATCHES matches.

    Raises ValueError with an i18n key if the account is not found or
    no matches are available.

    Args:
        name:        Riot game name.
        tag:         Riot tag line.
        region:      Routing region (e.g. "americas").
        on_progress: Optional callable(step, message, current, total)
                     for streaming progress updates to the job store.

    Returns:
        Dict containing the frontend result payload plus caching metadata:
        result, matches_raw, latest_match_id_cache, timestamp, patch,
        puuid and profile_icon_id.
    """
    logger.info(f"[FULL] {name}#{tag}")

    if on_progress:
        on_progress("account", "progress.account", 0, 0)

    patch = get_latest_patch()

    def _prog(current, total):
        if on_progress:
            on_progress("collecting", "progress.collecting", current, total)

    puuid, last_match_id, matches = collect_player_matches(region, name, tag, on_progress=_prog)

    if not matches:
        raise ValueError("error.no_match")
    if not puuid:
        raise ValueError("error.account_not_found")

    if on_progress:
        on_progress("processing", "progress.processing", 0, 0)

    # Build a reverse mapping from routing region → list of platform codes
    # so we can try each platform until Summoner v4 returns a valid response
    platform_map = defaultdict(list)
    for k, v in ROUTING_TO_PLATFORM.items():
        platform_map[v].append(k)

    profile_icon_id = 1  # Default icon if all platform attempts fail
    for platform_code in platform_map[region]:
        summoner = summoner_info(platform_code, puuid)
        if summoner:
            profile_icon_id = summoner.get("profileIconId", 1)
            break

    result = _build_result(matches, name, tag, region, patch)
    result["player_icon_img"] = (
        f"https://ddragon.leagueoflegends.com/cdn/{patch}/img/profileicon/{profile_icon_id}.png"
    )

    if on_progress:
        on_progress("done", "progress.done", 0, 0)

    return {
        "result":                result,
        "matches_raw":           matches,
        # Used on the next incremental update to detect new matches
        "latest_match_id_cache": last_match_id,
        "timestamp":             datetime.now(timezone.utc).isoformat(),
        "patch":                 patch,
        "puuid":                 puuid,
        "profile_icon_id":       profile_icon_id,
    }


def get_player_analysis_incremental(
    name: str,
    tag: str,
    region: str,
    cached_matches: list,
    latest_match_id_cache: str,
    patch: str,
    puuid_cached: str,
    profile_icon_id: int,
    on_progress=None,
) -> dict | None:
    """
    Incremental update: fetches only matches newer than latest_match_id_cache,
    merges them with the cached match history and reprocesses all analytics.

    Returns None if no new matches have been played since the last update,
    allowing the caller to reuse the existing cached result.

    Args:
        name:                  Riot game name.
        tag:                   Riot tag line.
        region:                Routing region.
        cached_matches:        Previously collected match dicts from cache.
        latest_match_id_cache: Match ID of the most recent cached match.
        patch:                 Patch version stored in cache (may be refreshed).
        puuid_cached:          Cached player PUUID (returned unchanged).
        profile_icon_id:       Cached profile icon ID (may be refreshed).
        on_progress:           Optional callable(step, message, current, total).

    Returns:
        Full payload dict (same shape as get_player_analysis) or None.
    """
    logger.info(f"[INCREMENTAL] {name}#{tag} since {latest_match_id_cache}")

    if on_progress:
        on_progress("account", "Checking for new matches...", 0, 0)

    # Always fetch the latest patch in case it changed since last cache write
    patch = get_latest_patch()

    def _prog(current, total):
        if on_progress:
            on_progress("collecting", "progress.newmatchs", current, total)

    puuid, last_match_id, new_matches = collect_player_matches(
        region, name, tag, after_match_id=latest_match_id_cache, on_progress=_prog
    )

    if not new_matches:
        logger.info(f"[INCREMENTAL] No new matches for {name}#{tag}.")
        return None

    # Refresh profile icon in case the player changed it
    platform_map = defaultdict(list)
    for k, v in ROUTING_TO_PLATFORM.items():
        platform_map[v].append(k)

    for platform_code in platform_map[region]:
        summoner = summoner_info(platform_code, puuid)
        if summoner:
            profile_icon_id = summoner.get("profileIconId", 1)
            break

    if on_progress:
        on_progress("processing", "Processing statistics...", 0, 0)

    # Prepend new matches and cap the total at MAX_MATCHES
    all_matches = (new_matches + cached_matches)[:MAX_MATCHES]
    result      = _build_result(all_matches, name, tag, region, patch)
    result["player_icon_img"] = (
        f"https://ddragon.leagueoflegends.com/cdn/{patch}/img/profileicon/{profile_icon_id}.png"
    )

    if on_progress:
        on_progress("done", "progress.done", 0, 0)

    return {
        "result":                result,
        "matches_raw":           all_matches,
        "latest_match_id_cache": last_match_id,
        "timestamp":             datetime.now(timezone.utc).isoformat(),
        "patch":                 patch,
        # Return the original cached PUUID — it never changes for the same account
        "puuid":                 puuid_cached,
        "profile_icon_id":       profile_icon_id,
    }