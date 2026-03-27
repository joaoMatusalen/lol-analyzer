import logging
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

from .client import account_info, fetch_match_ids, fetch_match_info

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────

# Maps each platform code to its routing region for Match v5 / Account v1
ROUTING_TO_PLATFORM = {
    "NA1" : "americas",
    "BR1" : "americas",
    "LA1" : "americas",
    "LA2" : "europe",
    "EUW1": "europe",
    "EUN1": "europe",
    "TR1" : "europe",
    "RU"  : "europe",
    "ME1" : "europe",
    "KR"  : "asia",
    "JP1" : "asia",
    "OC1" : "asia",
    "SG2" : "asia",
    "TW2" : "asia",
    "VN2" : "asia",
}

# Maximum number of matches to collect per analysis
MAX_MATCHES = 20

# All ping column names present in the Riot match data
PINGS_LIST = [
    "allInPings", "assistMePings", "commandPings", "dangerPings",
    "enemyMissingPings", "enemyVisionPings", "holdPings", "getBackPings",
    "needVisionPings", "onMyWayPings", "pushPings", "visionClearedPings",
]

# Maps raw Riot API lane strings to display-friendly labels
LANE_MAP = {
    "TOP":     "Top",
    "JUNGLE":  "Jungle",
    "MIDDLE":  "Mid",
    "BOTTOM":  "Adc",
    "UTILITY": "Support",
    "":        "Outros",
    "NONE":    "Outros",
}


# ── Internal helpers ──────────────────────────────────────────────

def _paginate_match_ids(region: str, puuid: str, after_match_id: str = None) -> list:
    """
    Paginates the Match v5 IDs endpoint, collecting up to MAX_MATCHES IDs.

    In incremental mode (after_match_id is provided), pagination stops early
    as soon as the known match ID is encountered in a page, so only truly
    new matches are returned.

    Args:
        region:         Routing region for Match v5.
        puuid:          Player unique identifier.
        after_match_id: If set, collect only matches newer than this ID.

    Returns:
        Ordered list of match ID strings (newest first).
    """
    all_ids = []
    start   = 0

    while len(all_ids) < MAX_MATCHES:
        batch = min(100, MAX_MATCHES - len(all_ids))
        page  = fetch_match_ids(region, puuid, count=batch, start=start)

        if not page:
            break
        if after_match_id and after_match_id in page:
            # Stop at the known match — only take what comes before it
            all_ids.extend(page[:page.index(after_match_id)])
            break

        all_ids.extend(page)

        # End of available matches from the API
        if len(page) < batch:
            break
        start += batch

    logger.info(f"Collected {len(all_ids)} match IDs.")
    return all_ids


def _parse_match(match_info: dict, puuid: str, match_id: str) -> dict | None:
    """
    Extracts the relevant fields from a raw match object for a specific player.

    Objective and CLASSIC-specific stats (farm, vision, objectives) are only
    populated for CLASSIC matches; all other modes receive zero values.

    Args:
        match_info: Full match data dict returned by the Riot API.
        puuid:      Target player's unique identifier.
        match_id:   Match identifier, used for logging.

    Returns:
        Flat dict of parsed match fields, or None if the data is invalid
        or the player is not found among the participants.
    """
    if not match_info or "info" not in match_info:
        logger.warning(f"Missing data for match: {match_id}")
        return None

    # Find this player's participant block
    player = next(
        (p for p in match_info["info"]["participants"] if p["puuid"] == puuid),
        None,
    )
    if player is None:
        logger.warning(f"Player not found in match: {match_id}")
        return None

    game_mode  = match_info["info"]["gameMode"]
    is_classic = game_mode == "CLASSIC"

    # Objective kills are sourced from the team block, not the participant block
    baron = dragon = horde = herald = tower = inhibitor = 0
    if is_classic:
        team = next(
            (t for t in match_info["info"]["teams"] if t["teamId"] == player["teamId"]),
            None,
        )
        if team:
            obj       = team.get("objectives", {})
            baron     = obj.get("baron",      {}).get("kills", 0)
            dragon    = obj.get("dragon",     {}).get("kills", 0)
            horde     = obj.get("horde",      {}).get("kills", 0)
            herald    = obj.get("riftHerald", {}).get("kills", 0)
            tower     = obj.get("tower",      {}).get("kills", 0)
            inhibitor = obj.get("inhibitor",  {}).get("kills", 0)

    return {
        "matchId":                     match_id,
        "gameCreation":                match_info["info"]["gameCreation"],
        "gameDuration":                match_info["info"]["gameDuration"],
        "gameMode":                    game_mode,
        "championName":                player["championName"],
        "championId":                  player["championId"],
        "kills":                       player["kills"],
        "deaths":                      player["deaths"],
        "assists":                     player["assists"],
        # Lane is only meaningful in CLASSIC; set to 'unknown' for other modes
        "lane":                        player["lane"] if is_classic else "unknown",
        "pentaKills":                  player["pentaKills"],
        "win":                         player["win"],
        "totalDamageDealtToChampions": player["totalDamageDealtToChampions"],
        # CS and vision score are 0 outside of CLASSIC
        "totalMinionsKilled":          player["totalMinionsKilled"] if is_classic else 0,
        "goldEarned":                  player["goldEarned"],
        "visionScore":                 player["visionScore"] if is_classic else 0,
        "wardsPlaced":                 player["wardsPlaced"],
        "wardsKilled":                 player["wardsKilled"],
        "firstBloodKill":              player["firstBloodKill"],
        "doubleKills":                 player["doubleKills"],
        "tripleKills":                 player["tripleKills"],
        "quadraKills":                 player["quadraKills"],
        "teamPosition":                player["teamPosition"],
        "totalDamageTaken":            player["totalDamageTaken"],
        # Objective counts — always 0 for non-CLASSIC modes
        "baronKills":                  baron,
        "dragonKills":                 dragon,
        "hordeKills":                  horde,
        "riftHeraldKills":             herald,
        "towerKills":                  tower,
        "inhibitorKills":              inhibitor,
        # Ping counts — use .get() with a default of 0 for safety
        "allInPings":                  player.get("allInPings",        0),
        "assistMePings":               player.get("assistMePings",      0),
        "commandPings":                player.get("commandPings",       0),
        "dangerPings":                 player.get("dangerPings",        0),
        "enemyMissingPings":           player.get("enemyMissingPings",  0),
        "enemyVisionPings":            player.get("enemyVisionPings",   0),
        "holdPings":                   player.get("holdPings",          0),
        "getBackPings":                player.get("getBackPings",       0),
        "needVisionPings":             player.get("needVisionPings",    0),
        "onMyWayPings":                player.get("onMyWayPings",       0),
        "pushPings":                   player.get("pushPings",          0),
        "visionClearedPings":          player.get("visionClearedPings", 0),
    }


def _fetch_parallel(region: str, match_ids: list, puuid: str, on_progress=None) -> list:
    """
    Fetches and parses multiple matches concurrently using a thread pool.

    Uses up to 5 worker threads to speed up the data collection phase.
    Progress is reported via an optional callback after each match resolves.

    Args:
        region:      Routing region for fetch_match_info.
        match_ids:   List of match IDs to fetch.
        puuid:       Target player's unique identifier.
        on_progress: Optional callable(current: int, total: int) for progress tracking.

    Returns:
        List of parsed match dicts (failed or empty matches are excluded).
    """
    matches  = []
    total    = len(match_ids)
    received = 0

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_match_info, region, mid): mid for mid in match_ids}
        for future in as_completed(futures):
            match_id  = futures[future]
            received += 1
            try:
                parsed = _parse_match(future.result(), puuid, match_id)
            except Exception as e:
                logger.warning(f"Error parsing {match_id}: {e}")
                parsed = None
            if parsed:
                matches.append(parsed)
            if on_progress:
                on_progress(received, total)

    return matches


# ── Public API ────────────────────────────────────────────────────

def collect_player_matches(
    region: str,
    name: str,
    tag: str,
    after_match_id: str = None,
    on_progress=None,
) -> tuple[str | None, str | None, list]:
    """
    Collects parsed match data for a player, with optional incremental mode.

    In full mode (after_match_id=None), fetches up to MAX_MATCHES recent matches.
    In incremental mode, fetches only matches newer than after_match_id.

    Args:
        region:         Routing region (e.g. "americas").
        name:           Riot game name.
        tag:            Riot tag line.
        after_match_id: If provided, only newer matches are collected.
        on_progress:    Optional callable(current: int, total: int).

    Returns:
        Tuple of (puuid, latest_match_id, matches_list).
        Returns (None, None, []) if the account is not found.
        Returns (puuid, [], []) if no new match IDs are available.
    """
    account = account_info(region, name, tag)
    if not account or "puuid" not in account:
        logger.warning("Account not found.")
        return None, None, []

    puuid     = account["puuid"]
    match_ids = _paginate_match_ids(region, puuid, after_match_id=after_match_id)

    if not match_ids:
        return puuid, [], []

    # The API returns IDs newest-first, so index 0 is the most recent match
    last_match_id = match_ids[0]

    return puuid, last_match_id, _fetch_parallel(region, match_ids, puuid, on_progress=on_progress)


def convert_to_dataframe(matches: list) -> pd.DataFrame:
    """Converts a list of parsed match dicts into a pandas DataFrame."""
    return pd.DataFrame(matches)