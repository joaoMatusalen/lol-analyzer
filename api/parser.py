import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

from .client import account_info, fetch_match_ids, fetch_match_info

# ── Constantes ────────────────────────────────────────────────────

ROUTING_TO_PLATFORM = {
"NA1" : "americas",
"BR1" : "americas",
"LA1" : "americas",
"LA2" : "europe",
"EUW1" : "europe",
"EUN1" : "europe", 
"TR1" : "europe", 
"RU" :  "europe", 
"ME1" : "europe", 
"KR" :  "asia",
"JP1" : "asia",
"OC1" : "asia",
"SG2" : "asia",
"TW2" : "asia",
"VN2" : "asia",
}

MAX_MATCHES = 20

PINGS_LIST = [
    "allInPings", "assistMePings", "commandPings", "dangerPings",
    "enemyMissingPings", "enemyVisionPings", "holdPings", "getBackPings",
    "needVisionPings", "onMyWayPings", "pushPings", "visionClearedPings",
]

LANE_MAP = {
    "TOP":     "Top",
    "JUNGLE":  "Jungle",
    "MIDDLE":  "Mid",
    "BOTTOM":  "Adc",
    "UTILITY": "Support",
    "":        "Outros",
    "NONE":    "Outros",
}


# ── Helpers internos ──────────────────────────────────────────────

def _paginate_match_ids(region: str, puuid: str, after_match_id: str = None) -> list:
    """
    Pagina a API coletando IDs até MAX_MATCHES.
    Se after_match_id for informado, para ao encontrá-lo (modo incremental).
    """
    all_ids = []
    start   = 0

    while len(all_ids) < MAX_MATCHES:
        batch = min(100, MAX_MATCHES - len(all_ids))
        page  = fetch_match_ids(region, puuid, count=batch, start=start)

        if not page:
            break
        if after_match_id and after_match_id in page:
            all_ids.extend(page[:page.index(after_match_id)])
            break

        all_ids.extend(page)

        if len(page) < batch:
            break
        start += batch

    print(f"IDs coletados: {len(all_ids)}")
    return all_ids


def _parse_match(match_info: dict, puuid: str, match_id: str) -> dict | None:
    """Extrai os campos relevantes de uma partida para o jogador indicado pelo puuid."""
    if not match_info or "info" not in match_info:
        print(f"Dados ausentes: {match_id}")
        return None

    player = next(
        (p for p in match_info["info"]["participants"] if p["puuid"] == puuid),
        None,
    )
    if player is None:
        print(f"Jogador ausente: {match_id}")
        return None

    game_mode  = match_info["info"]["gameMode"]
    is_classic = game_mode == "CLASSIC"

    baron = dragon = horde = herald = tower = inhibitor = 0
    if is_classic:
        team = next(
            (t for t in match_info["info"]["teams"] if t["teamId"] == player["teamId"]),
            None,
        )
        if team:
            obj     = team.get("objectives", {})
            baron   = obj.get("baron",      {}).get("kills", 0)
            dragon  = obj.get("dragon",     {}).get("kills", 0)
            horde   = obj.get("horde",      {}).get("kills", 0)
            herald  = obj.get("riftHerald", {}).get("kills", 0)
            tower   = obj.get("tower",      {}).get("kills", 0)
            inhibitor = obj.get("inhibitor", {}).get("kills", 0)

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
        "lane":                        player["lane"] if is_classic else 'unknown',
        "pentaKills":                  player["pentaKills"],
        "win":                         player["win"],
        "totalDamageDealtToChampions": player["totalDamageDealtToChampions"],
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
        "baronKills":                  baron,
        "dragonKills":                 dragon,
        "hordeKills":                  horde,
        "riftHeraldKills":             herald,
        "towerKills":                  tower,
        "inhibitorKills":              inhibitor,
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
    """Busca detalhes de partidas em paralelo com ThreadPoolExecutor."""
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
                print(f"Erro ao parsear {match_id}: {e}")
                parsed = None
            if parsed:
                matches.append(parsed)
            if on_progress:
                on_progress(received, total)

    return matches


# ── API pública ───────────────────────────────────────────────────

def collect_player_matches(
    region: str,
    name: str,
    tag: str,
    after_match_id: str = None,
    on_progress=None,
) -> tuple[str | None, list]:
    """
    Coleta dados de partidas de um jogador.
    Se after_match_id for informado, busca apenas partidas mais recentes (incremental).
    """
    account = account_info(region, name, tag)
    if not account or "puuid" not in account:
        print("Conta não encontrada.")
        return None, []

    puuid     = account["puuid"]
    match_ids = _paginate_match_ids(region, puuid, after_match_id=after_match_id)
    
    if not match_ids:
        return puuid, [], []
    
    last_match_id = match_ids[0]

    return puuid, last_match_id, _fetch_parallel(region, match_ids, puuid, on_progress=on_progress)


def convert_to_dataframe(df: list) -> pd.DataFrame:
    return pd.DataFrame(df)
