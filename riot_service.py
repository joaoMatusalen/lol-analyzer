#%%
import time
import os
from dotenv import load_dotenv
import requests
import pandas as pd
from datetime import timedelta, datetime

load_dotenv()

token = os.getenv("RIOT_API")

# ================================================================
#  Variables suport
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

    # list for suport code

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
    "BOTTOM":  "ADC",
    "UTILITY": "Support",
    "":        "Outros",
    "NONE":    "Outros",
}

# ================================================================
#  API HELPERS
# ================================================================

def editLinkApi(link: str):
    return link, {"api_key": token}

def tryRequestApi(url, params):
    max_retries = 5
    for i in range(max_retries):
        resp = requests.get(url, params=params)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 121))
            print(f"Rate limit atingido. Aguardando {retry_after}s...")
            time.sleep(retry_after)
        elif resp.status_code == 200:
            return resp.json()
        else:
            print(f"Erro {resp.status_code}: {resp.text}")
            return {}  # FIX: retorna imediatamente em vez de continuar o loop
    return {}

def convertToDataFrame(matchesData):
    """Converte lista de dicionários de partidas em DataFrame."""
    return pd.DataFrame(matchesData)

# ================================================================
#  API ENDPOINTS
# ================================================================

def accountInfo(region: str, nome: str, tag: str):
    url, params = editLinkApi(
        f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{nome}/{tag}"
    )
    return tryRequestApi(url, params)

def idMatchs(region: str, puuid: str, count=5, start=0):
    url, params = editLinkApi(
        f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start={start}&count={count}"
    )
    return tryRequestApi(url, params)

def infoMatchs(region: str, idMatch: str):
    url, params = editLinkApi(
        f"https://{region}.api.riotgames.com/lol/match/v5/matches/{idMatch}"
    )
    return tryRequestApi(url, params)

def summonerInfo(platform: str, puuid: str):
    """
    Busca dados do summoner (incluindo profileIconId) pelo puuid.
    Usa a plataforma regional (ex: br1), não o routing global (ex: americas).
    """
    url, params = editLinkApi(
        f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    )
    return tryRequestApi(url, params)

def get_latest_patch():

    try:
        resp = requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=5)
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

def collectMultipleMatchesData(region: str, nome: str, tag: str):
    """
    Coleta dados de partidas de um jogador específico.

    Args:
        region (str): Região de routing do jogador (ex: "americas")
        nome (str): Nome do jogador
        tag (str): Tag do jogador

    Returns:
        tuple: (puuid: str, matchesData: list)
    """

    # Collect acount
    account = accountInfo(region, nome, tag)

    if not account or "puuid" not in account:
        print("Não foi possível obter informações da conta. Verifique nome, tag e região.")
        return None, []

    # Declare Puuid
    puuid = account["puuid"]

    # Collect all Matchs id
    allMatchIds = []
    start_index = 0
    count_per_request = 5

    count_per_request_teste = 5

    while True:
        matchIds_page = idMatchs(region, puuid, count=count_per_request, start=start_index)

        #if len(matchIds_page) < count_per_request:
        if start_index > 1:
            allMatchIds.extend(matchIds_page)
            break  # Sem mais partidas para buscar
        allMatchIds.extend(matchIds_page)
        start_index += count_per_request

    allMatchIds.extend(matchIds_page)
    start_index += count_per_request

    print(f"Total de IDs coletados: {len(allMatchIds)}")

    # Collect all Matchs data
    matchesData = []

    for i, matchId in enumerate(allMatchIds):
        print(matchId)
        print(f"Coletando partida {i+1}/{len(allMatchIds)}: {matchId}")

        # Collect Match info .json
        matchInfo = infoMatchs(region, matchId)

        if not matchInfo or "info" not in matchInfo:
            print(f"Não foi possível obter dados da partida {matchId}")
            continue

        # Check the player in match    
        participants = matchInfo["info"]["participants"]

        playerData = next((p for p in participants if p["puuid"] == puuid), None)

        if playerData is None:
            print(f"Jogador não encontrado na partida {matchId}")
            continue

        gameMode = matchInfo["info"]["gameMode"]
        isClassic = gameMode == "CLASSIC"

        # Team objectives — somente no modo CLASSIC
        # No modo (CHERRY) a estrutura de times é diferente e pode não conter os campos de objetivos.

        if isClassic:
            playerTeamId = playerData["teamId"]
            teamData     = next((t for t in matchInfo["info"]["teams"] if t["teamId"] == playerTeamId), None)
            
            if teamData is None:
                print(f"Time do jogador não encontrado na partida {matchId}")
                continue
            
            baronKills    = teamData["objectives"]["baron"]["kills"]
            dragonKills   = teamData["objectives"]["dragon"]["kills"]
            hordeKills    = teamData["objectives"]["horde"]["kills"]
            riftHeraldKills = teamData["objectives"]["riftHerald"]["kills"]
            towerKills    = teamData["objectives"]["tower"]["kills"]
            inhibitorKills = teamData["objectives"]["inhibitor"]["kills"]
        else:
            baronKills = dragonKills = hordeKills = 0
            riftHeraldKills = towerKills = inhibitorKills = 0

        matchData = {
            # Match
            "matchId":                     matchId,
            "gameCreation":                matchInfo["info"]["gameCreation"],
            "gameDuration":                matchInfo["info"]["gameDuration"],
            "gameMode":                    gameMode,

            # Champion
            "championName":                playerData["championName"],
            "championId":                  playerData["championId"],

            # Statistics Player
            "kills":                       playerData["kills"],
            "deaths":                      playerData["deaths"],
            "assists":                     playerData["assists"],
            "lane":                        playerData["lane"],
            "pentaKills":                  playerData["pentaKills"],
            "win":                         playerData["win"],
            "totalDamageDealtToChampions": playerData["totalDamageDealtToChampions"],
            "totalMinionsKilled":          playerData["totalMinionsKilled"] if isClassic else 0,
            "goldEarned":                  playerData["goldEarned"],
            "visionScore":                 playerData["visionScore"] if isClassic else 0,
            "wardsPlaced":                 playerData["wardsPlaced"],
            "wardsKilled":                 playerData["wardsKilled"],
            "firstBloodKill":              playerData["firstBloodKill"],
            "doubleKills":                 playerData["doubleKills"],
            "tripleKills":                 playerData["tripleKills"],
            "quadraKills":                 playerData["quadraKills"],
            "teamPosition":                playerData["teamPosition"],
            "totalDamageTaken":            playerData["totalDamageTaken"],

            # Team Objectives (0 fora do CLASSIC)
            "baronKills":                  baronKills,
            "dragonKills":                 dragonKills,
            "hordeKills":                  hordeKills,
            "riftHeraldKills":             riftHeraldKills,
            "towerKills":                  towerKills,
            "inhibitorKills":              inhibitorKills,

            # Pings
            "allInPings":                  playerData["allInPings"],
            "assistMePings":               playerData["assistMePings"],
            "commandPings":                playerData["commandPings"],
            "dangerPings":                 playerData["dangerPings"],
            "enemyMissingPings":           playerData["enemyMissingPings"],
            "enemyVisionPings":            playerData["enemyVisionPings"],
            "holdPings":                   playerData["holdPings"],
            "getBackPings":                playerData["getBackPings"],
            "needVisionPings":             playerData["needVisionPings"],
            "onMyWayPings":                playerData["onMyWayPings"],
            "pushPings":                   playerData["pushPings"],
            "visionClearedPings":          playerData["visionClearedPings"],
        }

        matchesData.append(matchData)

    return puuid, matchesData

# ================================================================
#  ANÁLISES
# ================================================================

def analyze_general_results(df):

    if df.empty:
        return {}

    general_results = {}

    filter = df["gameMode"] == "CLASSIC"

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
        "avg":   int(df["totalMinionsKilled"][filter].mean()),
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

    dfChamp

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


# ==============================================================
#  ENTRY POINT
# ================================================================

def get_player_analysis(name: str, tag: str, region: str):

    print(f"Coletando dados para {name}#{tag}...")

    # Patch buscado antes da coleta — necessário para get_champion_classes e URLs de imagem
    patch = get_latest_patch()

    puuid, allMatchesData = collectMultipleMatchesData(region, name, tag)

    if not allMatchesData:
        raise ValueError(f"Nenhuma partida encontrada para {name}#{tag} na região {region}.")

    df_matches = convertToDataFrame(allMatchesData)

    # Adiciona coluna classTag via Data Dragon
    class_map = get_champion_classes(patch)
    df_matches["classTag"] = df_matches["championName"].map(class_map).fillna("Unknown")

    general_results  = analyze_general_results(df_matches)
    champion_results = analyze_most_played_champion(df_matches)
    champion_name    = champion_results["champion"]

    chart_monthly    = analyze_monthly_evolution(df_matches)
    chart_lanes      = analyze_lane_stats(df_matches)
    chart_time       = analyze_time_patterns(df_matches)
    chart_classes    = analyze_class_stats(df_matches)
    chart_game_modes = analyze_game_modes(df_matches)

    platform = ROUTING_TO_PLATFORM.get(region, "br1")
    summoner = summonerInfo(platform, puuid)
    profile_icon_id = summoner.get("profileIconId", 1) if summoner else 1

    return {
        "player_info": {
            "name":   name,
            "tag":    tag,
            "region": region,
        },
        "geral_matchs":     general_results,
        "champion_results": champion_results,
        "champion_img":     f"https://ddragon.leagueoflegends.com/cdn/{patch}/img/champion/{champion_name}.png",
        "player_icon_img":  f"https://ddragon.leagueoflegends.com/cdn/{patch}/img/profileicon/{profile_icon_id}.png",
        "charts": {
            "monthly":    chart_monthly,
            "lanes":      chart_lanes,
            "time":       chart_time,
            "classes":    chart_classes,
            "game_modes": chart_game_modes,
        },
    }