import time
import os
from dotenv import load_dotenv
import requests
import pandas as pd
from datetime import timedelta, datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

token = os.getenv("RIOT_API")

# ================================================================
#  Constantes
# ================================================================

# Mapa de routing global -> plataforma regional (necessário para summoner-v4)
ROUTING_TO_PLATFORM = {
    "americas": "br1",
    "europe":   "euw1",
    "asia":     "kr",
    "sea":      "sg2",
    "na":       "na1",
    "la1":      "la1",
    "la2":      "la2",
    "oce":      "oc1",
    "ru":       "ru",
    "tr":       "tr1",
    "jp":       "jp1",
}

# Limite de partidas coletadas por jogador
MAX_MATCHES = 30

# All pings list
pings_list = [
    "allInPings",
    "assistMePings",
    "commandPings",
    "dangerPings",
    "enemyMissingPings",
    "enemyVisionPings",
    "holdPings",
    "getBackPings",
    "needVisionPings",
    "onMyWayPings",
    "pushPings",
    "visionClearedPings"
]

# All lanes list
lane_list = {
    "TOP":     "Top",
    "JUNGLE":  "Jungle",
    "MIDDLE":  "Mid",
    "BOTTOM":  "Adc",
    "UTILITY": "Support",
    "":        "Outros",
    "NONE":    "Outros",
}

# ================================================================
#  API HELPERS
# ================================================================

def _riot_headers() -> dict:
    """Retorna os headers padrão de autenticação da Riot API."""
    return {"X-Riot-Token": token}

def try_request_api(url: str, params: dict = None) -> dict:
    """Executa GET com retry automático em caso de rate limit (429)."""
    max_retries = 5
    for _ in range(max_retries):
        resp = requests.get(url, headers=_riot_headers(), params=params, timeout=10)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 121))
            print(f"Rate limit atingido. Aguardando {retry_after}s...")
            time.sleep(retry_after)
        elif resp.status_code == 200:
            return resp.json()
        else:
            print(f"Erro {resp.status_code}: {resp.text}")
            return {}
    return {}

def convert_to_dataframe(matches_data: list) -> pd.DataFrame:
    """Converte lista de dicionários de partidas em DataFrame."""
    return pd.DataFrame(matches_data)

# ================================================================
#  API ENDPOINTS
# ================================================================

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
    """
    Busca dados do summoner (incluindo profileIconId) pelo puuid.
    Usa a plataforma regional (ex: br1), não o routing global (ex: americas).
    """
    url = f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    return try_request_api(url)

def get_latest_patch() -> str:
    try:
        resp = requests.get(
            "https://ddragon.leagueoflegends.com/api/versions.json",
            timeout=5
        )
        return resp.json()[0]
    except Exception:
        return "15.8.1"  # fallback caso a requisição falhe

# ================================================================
#  CHAMPION CLASS LOOKUP (Data Dragon)
# ================================================================

def get_champion_classes(patch: str) -> dict:
    """
    Retorna um dict {championName: tag_primária} a partir do Data Dragon.
    Mapeia tanto pelo nome de exibição quanto pela chave interna do DDragon
    para cobrir edge cases (ex: 'Wukong' / 'MonkeyKing').
    """
    try:
        resp = requests.get(
            f"https://ddragon.leagueoflegends.com/cdn/{patch}/data/en_US/champion.json",
            timeout=5
        )
        data = resp.json().get("data", {})
    except Exception:
        return {}

    mapping = {}
    for champ_key, info in data.items():
        tags        = info.get("tags", [])
        primary_tag = tags[0] if tags else "Unknown"
        mapping[info["name"]] = primary_tag   # nome de exibição  (ex: "Wukong")
        mapping[champ_key]    = primary_tag   # chave interna     (ex: "MonkeyKing")

    return mapping

# ================================================================
#  COLETA DE PARTIDAS
# ================================================================

def _fetch_match_ids(region: str, puuid: str, count_per_page: int = 100, after_match_id: str = None) -> list:
    """
    Pagina a API até coletar IDs de partidas do jogador.
    Se after_match_id for informado, coleta apenas partidas mais recentes que ele.
    Respeita o limite global MAX_MATCHES.
    """
    all_ids = []
    start   = 0

    while len(all_ids) < MAX_MATCHES:
        batch = min(count_per_page, MAX_MATCHES - len(all_ids))
        page  = fetch_match_ids(region, puuid, count=batch, start=start)
        if not page:
            break

        # Se estamos em modo incremental, para quando encontrar o match já conhecido
        if after_match_id and after_match_id in page:
            idx = page.index(after_match_id)
            all_ids.extend(page[:idx])
            break

        all_ids.extend(page)

        if len(page) < batch:
            break
        start += batch

    print(f"Total de IDs coletados: {len(all_ids)}")
    return all_ids


def _parse_match(match_info: dict, puuid: str, match_id: str) -> dict | None:
    """Extrai os dados relevantes de uma partida para o jogador indicado pelo puuid."""
    if not match_info or "info" not in match_info:
        print(f"Dados ausentes na partida {match_id}")
        return None

    participants = match_info["info"]["participants"]
    player_data  = next((p for p in participants if p["puuid"] == puuid), None)

    if player_data is None:
        print(f"Jogador não encontrado na partida {match_id}")
        return None

    game_mode  = match_info["info"]["gameMode"]
    is_classic = game_mode == "CLASSIC"

    # Objetivos de time — somente no modo CLASSIC
    # No modo CHERRY (Arena) a estrutura de times é diferente e pode não conter esses campos.
    baron_kills = dragon_kills = horde_kills = 0
    rift_herald_kills = tower_kills = inhibitor_kills = 0

    if is_classic:
        player_team_id = player_data["teamId"]
        team_data = next(
            (t for t in match_info["info"]["teams"] if t["teamId"] == player_team_id),
            None
        )
        if team_data:
            obj = team_data.get("objectives", {})
            baron_kills       = obj.get("baron",      {}).get("kills", 0)
            dragon_kills      = obj.get("dragon",     {}).get("kills", 0)
            horde_kills       = obj.get("horde",      {}).get("kills", 0)
            rift_herald_kills = obj.get("riftHerald", {}).get("kills", 0)
            tower_kills       = obj.get("tower",      {}).get("kills", 0)
            inhibitor_kills   = obj.get("inhibitor",  {}).get("kills", 0)

    return {
        # Partida
        "matchId":                     match_id,
        "gameCreation":                match_info["info"]["gameCreation"],
        "gameDuration":                match_info["info"]["gameDuration"],
        "gameMode":                    game_mode,

        # Campeão
        "championName":                player_data["championName"],
        "championId":                  player_data["championId"],

        # Estatísticas do jogador
        "kills":                       player_data["kills"],
        "deaths":                      player_data["deaths"],
        "assists":                     player_data["assists"],
        "lane":                        player_data["lane"],
        "pentaKills":                  player_data["pentaKills"],
        "win":                         player_data["win"],
        "totalDamageDealtToChampions": player_data["totalDamageDealtToChampions"],
        "totalMinionsKilled":          player_data["totalMinionsKilled"] if is_classic else 0,
        "goldEarned":                  player_data["goldEarned"],
        "visionScore":                 player_data["visionScore"] if is_classic else 0,
        "wardsPlaced":                 player_data["wardsPlaced"],
        "wardsKilled":                 player_data["wardsKilled"],
        "firstBloodKill":              player_data["firstBloodKill"],
        "doubleKills":                 player_data["doubleKills"],
        "tripleKills":                 player_data["tripleKills"],
        "quadraKills":                 player_data["quadraKills"],
        "teamPosition":                player_data["teamPosition"],
        "totalDamageTaken":            player_data["totalDamageTaken"],

        # Objetivos do time (0 fora do CLASSIC)
        "baronKills":                  baron_kills,
        "dragonKills":                 dragon_kills,
        "hordeKills":                  horde_kills,
        "riftHeraldKills":             rift_herald_kills,
        "towerKills":                  tower_kills,
        "inhibitorKills":              inhibitor_kills,

        # Pings — .get() com fallback 0 para compatibilidade com partidas antigas
        "allInPings":                  player_data.get("allInPings",         0),
        "assistMePings":               player_data.get("assistMePings",       0),
        "commandPings":                player_data.get("commandPings",        0),
        "dangerPings":                 player_data.get("dangerPings",         0),
        "enemyMissingPings":           player_data.get("enemyMissingPings",   0),
        "enemyVisionPings":            player_data.get("enemyVisionPings",    0),
        "holdPings":                   player_data.get("holdPings",           0),
        "getBackPings":                player_data.get("getBackPings",        0),
        "needVisionPings":             player_data.get("needVisionPings",     0),
        "onMyWayPings":                player_data.get("onMyWayPings",        0),
        "pushPings":                   player_data.get("pushPings",           0),
        "visionClearedPings":          player_data.get("visionClearedPings",  0),
    }


def _fetch_match_details(region: str, match_ids: list, puuid: str, max_workers: int = 10, on_progress=None) -> list:
    """
    Busca os detalhes de múltiplas partidas em paralelo.
    on_progress(current, total): callback opcional chamado a cada partida recebida.
    """
    matches  = []
    total    = len(match_ids)
    received = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_match_info, region, mid): mid
            for mid in match_ids
        }
        for future in as_completed(futures):
            match_id  = futures[future]
            received += 1
            print(f"Partida recebida {received}/{total}: {match_id}")
            try:
                parsed = _parse_match(future.result(), puuid, match_id)
            except Exception as e:
                print(f"Erro ao processar partida {match_id}: {e}")
                parsed = None
            if parsed:
                matches.append(parsed)
            if on_progress:
                on_progress(received, total)

    return matches


def collect_player_matches(region: str, name: str, tag: str, after_match_id: str = None, on_progress=None) -> tuple[str | None, list]:
    """
    Coleta dados de partidas de um jogador.

    Args:
        region:         Região de routing (ex: "americas")
        name:           Nome do jogador
        tag:            Tag do jogador
        after_match_id: Se informado, coleta apenas partidas mais recentes que este ID (update incremental)
        on_progress:    Callback opcional(current, total) chamado a cada partida processada

    Returns:
        Tupla (puuid, lista de dicionários de partida)
    """
    account = account_info(region, name, tag)

    if not account or "puuid" not in account:
        print("Não foi possível obter informações da conta. Verifique nome, tag e região.")
        return None, []

    puuid     = account["puuid"]
    match_ids = _fetch_match_ids(region, puuid, after_match_id=after_match_id)

    if not match_ids:
        return puuid, []

    matches = _fetch_match_details(region, match_ids, puuid, on_progress=on_progress)
    return puuid, matches

# ================================================================
#  ANÁLISES
# ================================================================

def analyze_general_results(df):

    if df.empty:
        return {}

    general_results = {}

    general_results["matchResult"] = {
        "total_win":  int(df["win"].sum()),
        "total_loss": int((~df["win"]).sum()),
        "win_rate":   round(df["win"].mean() * 100, 2),
    }

    general_results["sizePlayed"] = {
        "total_matchs":      int(df["win"].count()),
        "total_time_played": str(timedelta(seconds=int(df["gameDuration"].sum())))
    }

    general_results["kda"] = {
        "kda_ratio":    round((df["kills"].sum() + df["assists"].sum()) / max(df["deaths"].sum(), 1), 2),
        "total_kills":  int(df["kills"].sum()),
        "total_deaths": int(df["deaths"].sum()),
        "total_assists":int(df["assists"].sum()),
        "avg_kills":    round(df["kills"].mean(), 1),
        "avg_deaths":   round(df["deaths"].mean(), 1),
        "avg_assists":  round(df["assists"].mean(), 1),
    }

    general_results["economy"] = {
        "total_gold": int(df["goldEarned"].sum()),
        "avg_gold":   round(df["goldEarned"].mean()),
    }

    general_results["damage"] = {
        "total": int(df["totalDamageDealtToChampions"].sum()),
        "avg":   round(df["totalDamageDealtToChampions"].mean()),
    }

    general_results["farm"] = {
        "total": int(df["totalMinionsKilled"].sum()),
        "avg":   int(df["totalMinionsKilled"].mean()),
    }

    general_results["vision"] = {
        "total": int(df["visionScore"].sum()),
        "avg":   int(df["visionScore"].mean()),
    }

    general_results["multikills"] = {
        "double": int(df["doubleKills"].sum()),
        "triple": int(df["tripleKills"].sum()),
        "quadra": int(df["quadraKills"].sum()),
        "penta":  int(df["pentaKills"].sum()),
    }

    general_results["objectives"] = {
        "total_dragons":         int(df["dragonKills"].sum()),
        "avg_dragons":           round(df["dragonKills"].mean(), 1),
        "total_barons":          int(df["baronKills"].sum()),
        "avg_barons":            round(df["baronKills"].mean(), 1),
        "total_towers":          int(df["towerKills"].sum()),
        "avg_towers":            round(df["towerKills"].mean(), 1),
        "total_rift_heralds":    int(df["riftHeraldKills"].sum()),
        "avg_rift_heralds":      round(df["riftHeraldKills"].mean(), 1),
        "total_horde_heralds":   int(df["hordeKills"].sum()),
        "avg_horde_heralds":     round(df["hordeKills"].mean(), 1),
        "total_inhibitor_kills": int(df["inhibitorKills"].sum()),
        "avg_inhibitor_kills":   round(df["inhibitorKills"].mean(), 1),
    }
    
    general_results["pings"] = {
        "total":          int(df[pings_list].sum().sum()),
        "avg_per_game":   round(df[pings_list].sum(axis=1).mean(), 1),
        "all_in":         int(df["allInPings"].sum()),
        "assist_me":      int(df["assistMePings"].sum()),
        "command":        int(df["commandPings"].sum()),
        "danger":         int(df["dangerPings"].sum()),
        "enemy_missing":  int(df["enemyMissingPings"].sum()),
        "enemy_vision":   int(df["enemyVisionPings"].sum()),
        "hold":           int(df["holdPings"].sum()),
        "get_back":       int(df["getBackPings"].sum()),
        "need_vision":    int(df["needVisionPings"].sum()),
        "on_my_way":      int(df["onMyWayPings"].sum()),
        "push":           int(df["pushPings"].sum()),
        "vision_cleared": int(df["visionClearedPings"].sum()),
    }

    return general_results

def analyze_most_played_champion(df):

    if df.empty:
        return {}

    most_played = df["championName"].value_counts().idxmax()
    dfChamp = df[df["championName"] == most_played]

    champ_results = {}

    champ_results["champion"] = most_played

    champ_results["matchResult"] = {
        "total_win":  int(dfChamp["win"].sum()),
        "total_loss": int((~dfChamp["win"]).sum()),
        "win_rate":   round(dfChamp["win"].mean() * 100, 2),
    }

    champ_results["sizePlayed"] = {
        "total_matchs":      int(dfChamp["win"].count()),
        "total_time_played": str(timedelta(seconds=int(dfChamp["gameDuration"].sum())))
    }

    champ_results["kda"] = {
        "kda_ratio":    round((dfChamp["kills"].sum() + dfChamp["assists"].sum()) / max(dfChamp["deaths"].sum(), 1), 2),
        "total_kills":  int(dfChamp["kills"].sum()),
        "total_deaths": int(dfChamp["deaths"].sum()),
        "total_assists":int(dfChamp["assists"].sum()),
        "avg_kills":    round(dfChamp["kills"].mean(), 1),
        "avg_deaths":   round(dfChamp["deaths"].mean(), 1),
        "avg_assists":  round(dfChamp["assists"].mean(), 1),
    }

    champ_results["economy"] = {
        "total_gold": int(dfChamp["goldEarned"].sum()),
        "avg_gold":   round(dfChamp["goldEarned"].mean()),
    }

    champ_results["damage"] = {
        "total": int(dfChamp["totalDamageDealtToChampions"].sum()),
        "avg":   round(dfChamp["totalDamageDealtToChampions"].mean()),
    }

    champ_results["farm"] = {
        "total": int(dfChamp["totalMinionsKilled"].sum()),
        "avg":   int(dfChamp["totalMinionsKilled"].mean()),
    }

    champ_results["vision"] = {
        "total": int(dfChamp["visionScore"].sum()),
        "avg":   int(dfChamp["visionScore"].mean()),
    }

    champ_results["multikills"] = {
        "double": int(dfChamp["doubleKills"].sum()),
        "triple": int(dfChamp["tripleKills"].sum()),
        "quadra": int(dfChamp["quadraKills"].sum()),
        "penta":  int(dfChamp["pentaKills"].sum()),
    }

    return champ_results

# ================================================================
#  CHART DATA
# ================================================================

def analyze_monthly_evolution(df):

    # Copy to don't affect the original df
    df = df.copy()

    # Time fix month
    df["date"]  = pd.to_datetime(df["gameCreation"], unit="ms")
    df["month"] = df["date"].dt.to_period("M")

    dfMonth = df.groupby("month").agg(
        avg_farm    = ("totalMinionsKilled",          "mean"),
        avg_vision  = ("visionScore",                 "mean"),
        avg_gold    = ("goldEarned",                  "mean"),
        avg_deaths  = ("deaths",                      "mean"),
        avg_kills   = ("kills",                       "mean"),
        avg_assists = ("assists",                     "mean"),
        avg_damage  = ("totalDamageDealtToChampions", "mean"),
        win_rate    = ("win",                         "mean"),
        games       = ("matchId",                     "count"),
    ).reset_index().sort_values("month")

    # "2025-10" → "10/2025"
    labels = ["/".join(reversed(str(r).split("-"))) for r in dfMonth["month"]]

    # Return the month avg
    return {
        "labels":      labels,
        "avg_farm":    [round(v, 1) for v in dfMonth["avg_farm"]],
        "avg_vision":  [round(v, 1) for v in dfMonth["avg_vision"]],
        "avg_gold":    [round(v, 0) for v in dfMonth["avg_gold"]],
        "avg_deaths":  [round(v, 1) for v in dfMonth["avg_deaths"]],
        "avg_kills":   [round(v, 1) for v in dfMonth["avg_kills"]],
        "avg_assists": [round(v, 1) for v in dfMonth["avg_assists"]],
        "avg_damage":  [round(v, 0) for v in dfMonth["avg_damage"]],
        "win_rate":    [round(v * 100, 1) for v in dfMonth["win_rate"]],
        "games":       [int(v) for v in dfMonth["games"]],
    }

def analyze_lane_stats(df):
    
    # Copy to don't affect the original df
    df = df.copy()

    # Filter the lanes and add the correct name
    df["lane_label"] = (df["teamPosition"].map(lane_list)
                                          .fillna("Outros"))
    
    df = df[df["lane_label"] != "Outros"]

    # Data order
    lane_order = ["Top", "Jungle", "Mid", "Adc", "Support"]

    grouped = df.groupby("lane_label").agg(
        games = ("matchId", "count"),
        wins  = ("win",     "sum"),
    ).reindex(lane_order, fill_value=0).reset_index()

    grouped["winrate"] = (grouped["wins"] / grouped["games"].replace(0, 1) * 100).round(1)

    return {
        "labels":  lane_order,
        "games":   [int(v)   for v in grouped["games"]],
        "winrate": [float(v) for v in grouped["winrate"]],
    }

def analyze_time_patterns(df):

    # Copy to don't affect the original df
    df = df.copy()

    # Time fix
    df["date"] = pd.to_datetime(df["gameCreation"], unit="ms")

    day_order  = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    day_map_en = {
        "Monday": "Segunda", "Tuesday": "Terça", "Wednesday": "Quarta",
        "Thursday": "Quinta", "Friday": "Sexta", "Saturday": "Sábado", "Sunday": "Domingo"
    }

    # Translate day name to pt-br
    df["day_name"] = df["date"].dt.day_name().map(day_map_en)

    df_day = df.groupby("day_name").agg(
        games         = ("matchId",      "count"),
        wins          = ("win",          "sum"),
        total_seconds = ("gameDuration", "sum"),
    ).reindex(day_order, fill_value=0)

    df_day["winrate"]      = (df_day["wins"] / df_day["games"].replace(0, 1) * 100).round(1)
    df_day["hours_played"] = (df_day["total_seconds"] / 3600).round(1)

    df["hour_block"] = df["date"].dt.hour
    hour_order = [f"{h:02d}h" for h in range(0, 24)]

    df_hour = df.groupby("hour_block").agg(
        games = ("matchId", "count"),
        wins  = ("win",     "sum"),
    ).reindex(range(0, 24), fill_value=0)

    df_hour["winrate"] = (df_hour["wins"] / df_hour["games"].replace(0, 1) * 100).round(1)

    return {
        "weekday": {
            "labels":       day_order,
            "hours_played": [float(v) for v in df_day["hours_played"]],
            "winrate":      [float(v) for v in df_day["winrate"]],
            "games":        [int(v)   for v in df_day["games"]],
        },
        "hourly": {
            "labels":  hour_order,
            "winrate": [float(v) for v in df_hour["winrate"]],
            "games":   [int(v)   for v in df_hour["games"]],
        },
    }

def analyze_class_stats(df: pd.DataFrame) -> dict:
    """
    Frequência e winrate por classe de campeão (tag primária).
    Sempre retorna todas as 6 classes, mesmo que o jogador não tenha jogado com elas.
    """
    CLASS_ORDER = ["Fighter", "Tank", "Mage", "Assassin", "Marksman", "Support"]

    df = df.copy()
    df = df[df["classTag"] != "Unknown"]

    grouped = df.groupby("classTag").agg(
        games = ("matchId", "count"),
        wins  = ("win",     "sum"),
    ).reset_index() if not df.empty else pd.DataFrame(columns=["classTag", "games", "wins"])

    grouped["winrate"] = (grouped["wins"] / grouped["games"].replace(0, 1) * 100).round(1)

    # Garante todas as 6 classes na ordem fixa, com 0 para as ausentes
    full = (
        grouped.set_index("classTag")
               .reindex(CLASS_ORDER, fill_value=0)
               .reset_index()
    )

    return {
        "labels":  CLASS_ORDER,
        "games":   [int(v)   for v in full["games"]],
        "winrate": [float(v) for v in full["winrate"]],
    }

def analyze_game_modes(df: pd.DataFrame) -> dict:
    """Contagem, percentagem e winrate por modo de jogo. Sempre retorna os 7 modos fixos."""

    GAME_MODE_ORDER = ["CLASSIC", "ARAM", "CHERRY", "NEXUSBLITZ", "URF", "ONEFORALL", "TUTORIAL"]

    total = max(len(df), 1)

    grouped = df.groupby("gameMode").agg(
        games = ("matchId", "count"),
        wins  = ("win",     "sum"),
    ).reindex(GAME_MODE_ORDER, fill_value=0).reset_index()

    grouped["percentage"] = (grouped["games"] / total * 100).round(1)
    grouped["winrate"]    = (grouped["wins"] / grouped["games"].replace(0, 1) * 100).round(1)
    grouped.loc[grouped["games"] == 0, "winrate"] = 0.0

    return {
        "labels":      GAME_MODE_ORDER,
        "games":       [int(v)   for v in grouped["games"]],
        "percentages": [float(v) for v in grouped["percentage"]],
        "winrate":     [float(v) for v in grouped["winrate"]],
    }


def analyze_match_history(df: pd.DataFrame, patch: str) -> list:
    """
    Retorna as últimas 20 partidas formatadas para o histórico.
    Cada item contém: matchId, champion, win, kills, deaths, assists,
    kda, damage, gold, duration, gameMode, gameCreation.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["gameCreation"], unit="ms")
    df = df.sort_values("date", ascending=False).head(20)

    GAME_MODE_LABELS = {
        "CLASSIC":    "Summoner's Rift",
        "ARAM":       "ARAM",
        "CHERRY":     "Arena",
        "NEXUSBLITZ": "Nexus Blitz",
        "URF":        "URF",
        "ONEFORALL":  "One for All",
        "TUTORIAL":   "Tutorial",
    }

    history = []
    for _, row in df.iterrows():
        kills   = int(row["kills"])
        deaths  = int(row["deaths"])
        assists = int(row["assists"])
        kda     = round((kills + assists) / max(deaths, 1), 2)

        duration_s = int(row["gameDuration"])
        duration   = f"{duration_s // 60}m {duration_s % 60:02d}s"

        history.append({
            "matchId":      row["matchId"],
            "champion":     row["championName"],
            "champion_img": f"https://ddragon.leagueoflegends.com/cdn/{patch}/img/champion/{row['championName']}.png",
            "win":          bool(row["win"]),
            "kills":        kills,
            "deaths":       deaths,
            "assists":      assists,
            "kda":          kda,
            "damage":       int(row["totalDamageDealtToChampions"]),
            "gold":         int(row["goldEarned"]),
            "cs":           int(row["totalMinionsKilled"]),
            "duration":     duration,
            "gameMode":     GAME_MODE_LABELS.get(row["gameMode"], row["gameMode"]),
            "date":         row["date"].strftime("%d/%m/%Y"),
        })

    return history


# ================================================================
#  ENTRY POINT
# ================================================================

def _build_result(matches_raw: list, name: str, tag: str, region: str, patch: str) -> dict:
    """
    Recebe a lista bruta de dicionários de partidas e devolve o payload
    completo para o frontend. Separado para ser reutilizado no update incremental.
    """
    df_matches = convert_to_dataframe(matches_raw)

    class_map = get_champion_classes(patch)
    df_matches["classTag"] = df_matches["championName"].map(class_map).fillna("Unknown")

    general_results  = analyze_general_results(df_matches)
    champion_results = analyze_most_played_champion(df_matches)
    champion_name    = champion_results["champion"]

    return {
        "player_info": {
            "name":   name,
            "tag":    tag,
            "region": region,
        },
        "geral_matchs":     general_results,
        "champion_results": champion_results,
        "champion_img":     f"https://ddragon.leagueoflegends.com/cdn/{patch}/img/champion/{champion_name}.png",
        "match_history":    analyze_match_history(df_matches, patch),
        "charts": {
            "monthly":    analyze_monthly_evolution(df_matches),
            "lanes":      analyze_lane_stats(df_matches),
            "time":       analyze_time_patterns(df_matches),
            "classes":    analyze_class_stats(df_matches),
            "game_modes": analyze_game_modes(df_matches),
        },
    }


def get_player_analysis(name: str, tag: str, region: str, on_progress=None) -> dict:
    """
    Busca completa. Coleta ate MAX_MATCHES partidas do zero.
    on_progress(step, message, current, total): callback de progresso opcional.
    """
    print(f"[FULL] Coletando dados para {name}#{tag}...")

    def _prog(current, total):
        if on_progress:
            on_progress("collecting", f"Analisando partidas...", current, total)

    if on_progress:
        on_progress("account", "Buscando conta...", 0, 0)

    patch = get_latest_patch()
    puuid, matches_raw = collect_player_matches(region, name, tag, on_progress=_prog)

    if not matches_raw:
        raise ValueError(f"Nenhuma partida encontrada para {name}#{tag} na regiao {region}.")
    if not puuid:
        raise ValueError(f"Nao foi possivel identificar o jogador {name}#{tag}.")

    if on_progress:
        on_progress("processing", "Processando estatisticas...", 0, 0)

    platform        = ROUTING_TO_PLATFORM.get(region, "br1")
    summoner        = summoner_info(platform, puuid)
    profile_icon_id = summoner.get("profileIconId", 1) if summoner else 1

    result = _build_result(matches_raw, name, tag, region, patch)
    result["player_icon_img"] = (
        f"https://ddragon.leagueoflegends.com/cdn/{patch}/img/profileicon/{profile_icon_id}.png"
    )

    if on_progress:
        on_progress("done", "Concluido!", 0, 0)

    return {
        "result":          result,
        "matches_raw":     matches_raw,
        "latest_match_id": matches_raw[0]["matchId"] if matches_raw else None,
        "timestamp":       datetime.now(timezone.utc).isoformat(),
        "patch":           patch,
        "puuid":           puuid,
        "profile_icon_id": profile_icon_id,
    }


def get_player_analysis_incremental(
    name: str, tag: str, region: str,
    cached_matches: list, latest_match_id: str,
    patch: str, puuid_cached: str, profile_icon_id: int,
    on_progress=None,
) -> dict:
    """
    Update incremental. Busca apenas partidas mais recentes que latest_match_id.
    """
    print(f"[INCREMENTAL] Atualizando {name}#{tag} a partir de {latest_match_id}...")

    def _prog(current, total):
        if on_progress:
            on_progress("collecting", "Buscando novas partidas...", current, total)

    if on_progress:
        on_progress("account", "Verificando novas partidas...", 0, 0)

    patch = get_latest_patch()

    _, new_matches = collect_player_matches(
        region, name, tag, after_match_id=latest_match_id, on_progress=_prog
    )

    if not new_matches:
        print(f"[INCREMENTAL] Nenhuma partida nova para {name}#{tag}.")
        return None

    if on_progress:
        on_progress("processing", "Processando estatisticas...", 0, 0)

    all_matches = (new_matches + cached_matches)[:MAX_MATCHES]

    result = _build_result(all_matches, name, tag, region, patch)
    result["player_icon_img"] = (
        f"https://ddragon.leagueoflegends.com/cdn/{patch}/img/profileicon/{profile_icon_id}.png"
    )

    if on_progress:
        on_progress("done", "Concluido!", 0, 0)

    return {
        "result":          result,
        "matches_raw":     all_matches,
        "latest_match_id": all_matches[0]["matchId"],
        "timestamp":       datetime.now(timezone.utc).isoformat(),
        "patch":           patch,
        "puuid":           puuid_cached,
        "profile_icon_id": profile_icon_id,
    }