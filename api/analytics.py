import pandas as pd
from datetime import timedelta

from .parser import PINGS_LIST, LANE_MAP


def analyze_general_results(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}

    return {
        "matchResult": {
            "total_win":  int(df["win"].sum()),
            "total_loss": int((~df["win"]).sum()),
            "win_rate":   round(df["win"].mean() * 100, 2),
        },
        "sizePlayed": {
            "total_matchs":      int(df["win"].count()),
            "total_time_played": str(timedelta(seconds=int(df["gameDuration"].sum()))),
        },
        "kda": {
            "kda_ratio":     round((df["kills"].sum() + df["assists"].sum()) / max(df["deaths"].sum(), 1), 2),
            "total_kills":   int(df["kills"].sum()),
            "total_deaths":  int(df["deaths"].sum()),
            "total_assists": int(df["assists"].sum()),
            "avg_kills":     round(df["kills"].mean(), 1),
            "avg_deaths":    round(df["deaths"].mean(), 1),
            "avg_assists":   round(df["assists"].mean(), 1),
        },
        "economy": {
            "total_gold": int(df["goldEarned"].sum()),
            "avg_gold":   round(df["goldEarned"].mean()),
        },
        "damage": {
            "total": int(df["totalDamageDealtToChampions"].sum()),
            "avg":   round(df["totalDamageDealtToChampions"].mean()),
        },
        "farm": {
            "total": int(df["totalMinionsKilled"].sum()),
            "avg":   int(df["totalMinionsKilled"].mean()),
        },
        "vision": {
            "total": int(df["visionScore"].sum()),
            "avg":   int(df["visionScore"].mean()),
        },
        "multikills": {
            "double": int(df["doubleKills"].sum()),
            "triple": int(df["tripleKills"].sum()),
            "quadra": int(df["quadraKills"].sum()),
            "penta":  int(df["pentaKills"].sum()),
        },
        "objectives": {
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
        },
        "pings": {
            "total":          int(df[PINGS_LIST].sum().sum()),
            "avg_per_game":   round(df[PINGS_LIST].sum(axis=1).mean(), 1),
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
        },
    }


def analyze_most_played_champion(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}

    champion = df["championName"].value_counts().idxmax()
    dfc      = df[df["championName"] == champion]

    return {
        "champion": champion,
        "matchResult": {
            "total_win":  int(dfc["win"].sum()),
            "total_loss": int((~dfc["win"]).sum()),
            "win_rate":   round(dfc["win"].mean() * 100, 2),
        },
        "sizePlayed": {
            "total_matchs":      int(dfc["win"].count()),
            "total_time_played": str(timedelta(seconds=int(dfc["gameDuration"].sum()))),
        },
        "kda": {
            "kda_ratio":     round((dfc["kills"].sum() + dfc["assists"].sum()) / max(dfc["deaths"].sum(), 1), 2),
            "total_kills":   int(dfc["kills"].sum()),
            "total_deaths":  int(dfc["deaths"].sum()),
            "total_assists": int(dfc["assists"].sum()),
            "avg_kills":     round(dfc["kills"].mean(), 1),
            "avg_deaths":    round(dfc["deaths"].mean(), 1),
            "avg_assists":   round(dfc["assists"].mean(), 1),
        },
        "economy": {
            "total_gold": int(dfc["goldEarned"].sum()),
            "avg_gold":   round(dfc["goldEarned"].mean()),
        },
        "damage": {
            "total": int(dfc["totalDamageDealtToChampions"].sum()),
            "avg":   round(dfc["totalDamageDealtToChampions"].mean()),
        },
        "farm": {
            "total": int(dfc["totalMinionsKilled"].sum()),
            "avg":   int(dfc["totalMinionsKilled"].mean()),
        },
        "vision": {
            "total": int(dfc["visionScore"].sum()),
            "avg":   int(dfc["visionScore"].mean()),
        },
        "multikills": {
            "double": int(dfc["doubleKills"].sum()),
            "triple": int(dfc["tripleKills"].sum()),
            "quadra": int(dfc["quadraKills"].sum()),
            "penta":  int(dfc["pentaKills"].sum()),
        },
    }


def analyze_monthly_evolution(df: pd.DataFrame) -> dict:
    df       = df.copy()
    df["date"]  = pd.to_datetime(df["gameCreation"], unit="ms")
    df["month"] = df["date"].dt.to_period("M")

    g = df.groupby("month").agg(
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

    labels = ["/".join(reversed(str(r).split("-"))) for r in g["month"]]

    return {
        "labels":      labels,
        "avg_farm":    [round(v, 1) for v in g["avg_farm"]],
        "avg_vision":  [round(v, 1) for v in g["avg_vision"]],
        "avg_gold":    [round(v, 0) for v in g["avg_gold"]],
        "avg_deaths":  [round(v, 1) for v in g["avg_deaths"]],
        "avg_kills":   [round(v, 1) for v in g["avg_kills"]],
        "avg_assists": [round(v, 1) for v in g["avg_assists"]],
        "avg_damage":  [round(v, 0) for v in g["avg_damage"]],
        "win_rate":    [round(v * 100, 1) for v in g["win_rate"]],
        "games":       [int(v) for v in g["games"]],
    }


def analyze_lane_stats(df: pd.DataFrame) -> dict:
    df = df.copy()
    df["lane_label"] = df["teamPosition"].map(LANE_MAP).fillna("Outros")
    df = df[df["lane_label"] != "Outros"]

    lane_order = ["Top", "Jungle", "Mid", "Adc", "Support"]
    g = df.groupby("lane_label").agg(
        games = ("matchId", "count"),
        wins  = ("win",     "sum"),
    ).reindex(lane_order, fill_value=0).reset_index()

    g["winrate"] = (g["wins"] / g["games"].replace(0, 1) * 100).round(1)

    return {
        "labels":  lane_order,
        "games":   [int(v)   for v in g["games"]],
        "winrate": [float(v) for v in g["winrate"]],
    }


def analyze_time_patterns(df: pd.DataFrame) -> dict:
    df = df.copy()
    df["date"] = pd.to_datetime(df["gameCreation"], unit="ms")

    day_order  = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]
    day_map_en = {
        "Monday": "Segunda", "Tuesday": "Terca", "Wednesday": "Quarta",
        "Thursday": "Quinta", "Friday": "Sexta", "Saturday": "Sabado", "Sunday": "Domingo",
    }
    df["day_name"] = df["date"].dt.day_name().map(day_map_en)

    df_day = df.groupby("day_name").agg(
        games         = ("matchId",      "count"),
        wins          = ("win",          "sum"),
        total_seconds = ("gameDuration", "sum"),
    ).reindex(day_order, fill_value=0)

    df_day["winrate"]      = (df_day["wins"] / df_day["games"].replace(0, 1) * 100).round(1)
    df_day["hours_played"] = (df_day["total_seconds"] / 3600).round(1)

    df["hour_block"] = df["date"].dt.hour
    df_hour = df.groupby("hour_block").agg(
        games = ("matchId", "count"),
        wins  = ("win",     "sum"),
    ).reindex(range(24), fill_value=0)
    df_hour["winrate"] = (df_hour["wins"] / df_hour["games"].replace(0, 1) * 100).round(1)

    return {
        "weekday": {
            "labels":       day_order,
            "hours_played": [float(v) for v in df_day["hours_played"]],
            "winrate":      [float(v) for v in df_day["winrate"]],
            "games":        [int(v)   for v in df_day["games"]],
        },
        "hourly": {
            "labels":  [f"{h:02d}h" for h in range(24)],
            "winrate": [float(v) for v in df_hour["winrate"]],
            "games":   [int(v)   for v in df_hour["games"]],
        },
    }


def analyze_class_stats(df: pd.DataFrame) -> dict:
    CLASS_ORDER = ["Fighter", "Tank", "Mage", "Assassin", "Marksman", "Support"]

    df = df.copy()
    df = df[df["classTag"] != "Unknown"]

    g = (
        df.groupby("classTag").agg(games=("matchId", "count"), wins=("win", "sum")).reset_index()
        if not df.empty
        else pd.DataFrame(columns=["classTag", "games", "wins"])
    )
    g["winrate"] = (g["wins"] / g["games"].replace(0, 1) * 100).round(1)

    full = g.set_index("classTag").reindex(CLASS_ORDER, fill_value=0).reset_index()

    return {
        "labels":  CLASS_ORDER,
        "games":   [int(v)   for v in full["games"]],
        "winrate": [float(v) for v in full["winrate"]],
    }


def analyze_game_modes(df: pd.DataFrame) -> dict:
    ORDER = ["CLASSIC", "ARAM", "CHERRY", "NEXUSBLITZ", "URF", "ONEFORALL", "TUTORIAL"]
    total = max(len(df), 1)

    g = df.groupby("gameMode").agg(
        games = ("matchId", "count"),
        wins  = ("win",     "sum"),
    ).reindex(ORDER, fill_value=0).reset_index()

    g["percentage"] = (g["games"] / total * 100).round(1)
    g["winrate"]    = (g["wins"] / g["games"].replace(0, 1) * 100).round(1)
    g.loc[g["games"] == 0, "winrate"] = 0.0

    return {
        "labels":      ORDER,
        "games":       [int(v)   for v in g["games"]],
        "percentages": [float(v) for v in g["percentage"]],
        "winrate":     [float(v) for v in g["winrate"]],
    }


def analyze_match_history(df: pd.DataFrame, patch: str) -> list:
    """Últimas 20 partidas formatadas para o histórico do dashboard."""
    GAME_MODE_LABELS = {
        "CLASSIC":    "Summoner's Rift",
        "ARAM":       "ARAM",
        "CHERRY":     "Arena",
        "NEXUSBLITZ": "Nexus Blitz",
        "URF":        "URF",
        "ONEFORALL":  "One for All",
        "TUTORIAL":   "Tutorial",
    }

    df = df.copy()
    df["date"] = pd.to_datetime(df["gameCreation"], unit="ms")
    df = df.sort_values("date", ascending=False).head(20)

    history = []
    for _, row in df.iterrows():
        k, d, a = int(row["kills"]), int(row["deaths"]), int(row["assists"])
        ds      = int(row["gameDuration"])
        history.append({
            "matchId":      row["matchId"],
            "champion":     row["championName"],
            "champion_img": f"https://ddragon.leagueoflegends.com/cdn/{patch}/img/champion/{row['championName']}.png",
            "win":          bool(row["win"]),
            "kills":        k,
            "deaths":       d,
            "assists":      a,
            "kda":          round((k + a) / max(d, 1), 2),
            "damage":       int(row["totalDamageDealtToChampions"]),
            "gold":         int(row["goldEarned"]),
            "cs":           int(row["totalMinionsKilled"]),
            "duration":     f"{ds // 60}m {ds % 60:02d}s",
            "gameMode":     GAME_MODE_LABELS.get(row["gameMode"], row["gameMode"]),
            "date":         row["date"].strftime("%d/%m/%Y"),
        })

    return history
