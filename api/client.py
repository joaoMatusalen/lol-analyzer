import time
import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

# Riot API token loaded from environment variable
_token = os.environ["RIOT_API"]
logger = logging.getLogger(__name__)


def _headers() -> dict:
    """Returns the authentication header required by every Riot API request."""
    return {"X-Riot-Token": _token}


def try_request_api(url: str, params: dict = None) -> dict:
    """
    Performs a GET request with automatic retry on rate limit (HTTP 429).

    Retries up to 5 times, honoring the Retry-After header when present.
    Returns an empty dict on non-200 responses or after exhausting retries.
    """
    for _ in range(5):
        resp = requests.get(url, headers=_headers(), params=params, timeout=10)
        if resp.status_code == 429:
            # Respect the server-specified cooldown; default to 121s if header is absent
            retry_after = int(resp.headers.get("Retry-After", 121))
            logger.info(f"Rate limited. Waiting {retry_after}s...")
            time.sleep(retry_after)
        elif resp.status_code == 200:
            return resp.json()
        else:
            logger.warning(f"Error {resp.status_code}: {resp.text}")
            return {}
    return {}


def account_info(region: str, name: str, tag: str) -> dict:
    """
    Fetches basic account data (puuid, gameName, tagLine) by Riot ID.

    Args:
        region: Routing region (e.g. "americas", "europe", "asia").
        name:   Riot game name (without the # tag).
        tag:    Riot tag line (without the leading #).
    """
    url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
    return try_request_api(url)


def fetch_match_ids(region: str, puuid: str, count: int = 100, start: int = 0) -> list:
    """
    Retrieves a paginated list of match IDs for a given puuid.

    Args:
        region: Routing region used for Match v5.
        puuid:  Player's unique identifier.
        count:  Number of IDs to request in this page (max 100).
        start:  Pagination offset.
    """
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    return try_request_api(url, params={"start": start, "count": count}) or []


def fetch_match_info(region: str, match_id: str) -> dict:
    """
    Fetches the full match data object for a given match ID.

    Args:
        region:   Routing region used for Match v5.
        match_id: Riot match identifier (e.g. "BR1_1234567890").
    """
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    return try_request_api(url)


def summoner_info(platform: str, puuid: str) -> dict:
    """
    Fetches summoner data (including profileIconId) by puuid via Summoner v4.

    Args:
        platform: Regional platform code (e.g. "br1", "euw1", "na1").
        puuid:    Player's unique identifier.
    """
    url = f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    return try_request_api(url)


def get_latest_patch() -> str:
    """
    Returns the latest League of Legends patch version string from Data Dragon.

    Falls back to a hardcoded version string if the request fails,
    ensuring champion images and data can still be loaded.
    """
    try:
        resp = requests.get(
            "https://ddragon.leagueoflegends.com/api/versions.json",
            timeout=5,
        )
        return resp.json()[0]
    except Exception:
        return "15.8.1"


def get_champion_classes(patch: str) -> dict:
    """
    Builds a mapping of champion name → primary class tag from Data Dragon.

    Both the display name (e.g. "Wukong") and the internal key (e.g. "MonkeyKing")
    are mapped to handle edge cases in the Riot API responses.

    Args:
        patch: Game version string (e.g. "15.8.1").

    Returns:
        Dict mapping champion name/key strings to their primary tag
        (e.g. {"Ahri": "Mage", "Garen": "Fighter", ...}).
    """
    try:
        resp = requests.get(
            f"https://ddragon.leagueoflegends.com/cdn/{patch}/data/en_US/champion.json",
            timeout=5,
        )
        data = resp.json().get("data", {})
    except Exception:
        return {}

    mapping = {}
    for champ_key, info in data.items():
        tags        = info.get("tags", [])
        primary_tag = tags[0] if tags else "Unknown"
        # Map both display name and internal key to cover mismatches
        mapping[info["name"]] = primary_tag
        mapping[champ_key]    = primary_tag

    return mapping