import time
import os
import requests
from dotenv import load_dotenv

load_dotenv()

_token = os.getenv("RIOT_API")


def _headers() -> dict:
    return {"X-Riot-Token": _token}


def try_request_api(url: str, params: dict = None) -> dict:
    """GET com retry automático em rate limit (429)."""
    for _ in range(5):
        resp = requests.get(url, headers=_headers(), params=params, timeout=10)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 121))
            print(f"Rate limit. Aguardando {retry_after}s...")
            time.sleep(retry_after)
        elif resp.status_code == 200:
            return resp.json()
        else:
            print(f"Erro {resp.status_code}: {resp.text}")
            return {}
    return {}


def account_info(region: str, name: str, tag: str) -> dict:
    url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
    return try_request_api(url)


def fetch_match_ids(region: str, puuid: str, count: int = 100, start: int = 0) -> list:
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    return try_request_api(url, params={"start": start, "count": count}) or []


def fetch_match_info(region: str, match_id: str) -> dict:
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    return try_request_api(url)


def summoner_info(platform: str, puuid: str) -> dict:
    """Busca profileIconId pelo puuid usando a plataforma regional (ex: br1)."""
    url = f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    return try_request_api(url)


def get_latest_patch() -> str:
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
    Retorna {championName: tag_primária} via Data Dragon.
    Mapeia nome de exibição e chave interna para cobrir edge cases (ex: Wukong/MonkeyKing).
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
        mapping[info["name"]] = primary_tag
        mapping[champ_key]    = primary_tag

    return mapping
