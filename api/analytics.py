import pandas as pd
from datetime import timedelta

from .parser import PINGS_LIST, LANE_MAP


# ── Internal helper ───────────────────────────────────────────────

def _classic_only(df: pd.DataFrame) -> pd.DataFrame:
    """Returns only matches played in CLASSIC (Summoner's Rift) mode."""
    return df[df["gameMode"] == "CLASSIC"]


# ── General analysis ──────────────────────────────────────────────

def analyze_general_results(df: pd.DataFrame) -> dict:
    """
    Computes aggregate statistics across all matches for a player.

    Farm, vision and objectives are restricted to CLASSIC matches only,
    since those metrics are not meaningful in other game modes (ARAM, Arena, etc.).

    Returns a dict with the following top-level keys:
        matchResult, sizePlayed, kda, economy, damage,
        farm, vision, multikills, objectives, pings
    """
    if df.empty:
        return {}

    # Farm, vision and objectives only make sense in CLASSIC matches
    df_classic = _classic_only(df)

    farm_avg     = int(df_classic["totalMinionsKilled"].mean()) if not df_classic.empty else 0
    farm_total   = int(df_classic["totalMinionsKilled"].sum())  if not df_classic.empty else 0
    vision_avg   = int(df_classic["visionScore"].mean())        if not df_classic.empty else 0
    vision_total = int(df_classic["visionScore"].sum())         if not df_classic.empty else 0

    objectives = {}
    if not df_classic.empty:
        objectives = {
            "total_dragons":         int(df_classic["dragonKills"].sum()),
            "avg_dragons":           round(df_classic["dragonKills"].mean(), 1),
            "total_barons":          int(df_classic["baronKills"].sum()),
            "avg_barons":            round(df_classic["baronKills"].mean(), 1),
            "total_towers":          int(df_classic["towerKills"].sum()),
            "avg_towers":            round(df_classic["towerKills"].mean(), 1),
            "total_rift_heralds":    int(df_classic["riftHeraldKills"].sum()),
            "avg_rift_heralds":      round(df_classic["riftHeraldKills"].mean(), 1),
            "total_horde_heralds":   int(df_classic["hordeKills"].sum()),
            "avg_horde_heralds":     round(df_classic["hordeKills"].mean(), 1),
            "total_inhibitor_kills": int(df_classic["inhibitorKills"].sum()),
            "avg_inhibitor_kills":   round(df_classic["inhibitorKills"].mean(), 1),
        }

    return {
        "matchResult": {
            "total_win":  int(df["win"].sum()),
            "total_loss": int((~df["win"]).sum()),
            "win_rate":   round(df["win"].mean() * 100, 2),
        },
        "sizePlayed": {
            "total_matchs":      int(df["win"].count()),
            # Human-readable total play time (e.g. "12:34:56")
            "total_time_played": str(timedelta(seconds=int(df["gameDuration"].sum()))),
        },
        "kda": {
            # KDA formula: (kills + assists) / max(deaths, 1) to avoid division by zero
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
            "total": farm_total,
            "avg":   farm_avg,
        },
        "vision": {
            "total": vision_total,
            "avg":   vision_avg,
        },
        "multikills": {
            "double": int(df["doubleKills"].sum()),
            "triple": int(df["tripleKills"].sum()),
            "quadra": int(df["quadraKills"].sum()),
            "penta":  int(df["pentaKills"].sum()),
        },
        "objectives": objectives,
        # Individual ping type totals and per-game average
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
    """
    Returns detailed statistics for the player's most-played champion.

    Uses the same structure as analyze_general_results but scoped
    to matches where the most frequent champion was played.
    Farm and vision are restricted to CLASSIC matches only.
    """
    if df.empty:
        return {}

    # Identify the champion with the highest match count
    champion = df["championName"].value_counts().idxmax()
    dfChampion = df[df["championName"] == champion]

    # Filter for CLASSIC-only metrics
    dfChampion_classic = _classic_only(dfChampion)
    farm_avg     = int(dfChampion_classic["totalMinionsKilled"].mean()) if not dfChampion_classic.empty else 0
    farm_total   = int(dfChampion_classic["totalMinionsKilled"].sum())  if not dfChampion_classic.empty else 0
    vision_avg   = int(dfChampion_classic["visionScore"].mean())        if not dfChampion_classic.empty else 0
    vision_total = int(dfChampion_classic["visionScore"].sum())         if not dfChampion_classic.empty else 0

    return {
        "champion": champion,
        "matchResult": {
            "total_win":  int(dfChampion["win"].sum()),
            "total_loss": int((~dfChampion["win"]).sum()),
            "win_rate":   round(dfChampion["win"].mean() * 100, 2),
        },
        "sizePlayed": {
            "total_matchs":      int(dfChampion["win"].count()),
            "total_time_played": str(timedelta(seconds=int(dfChampion["gameDuration"].sum()))),
        },
        "kda": {
            "kda_ratio":     round((dfChampion["kills"].sum() + dfChampion["assists"].sum()) / max(dfChampion["deaths"].sum(), 1), 2),
            "total_kills":   int(dfChampion["kills"].sum()),
            "total_deaths":  int(dfChampion["deaths"].sum()),
            "total_assists": int(dfChampion["assists"].sum()),
            "avg_kills":     round(dfChampion["kills"].mean(), 1),
            "avg_deaths":    round(dfChampion["deaths"].mean(), 1),
            "avg_assists":   round(dfChampion["assists"].mean(), 1),
        },
        "economy": {
            "total_gold": int(dfChampion["goldEarned"].sum()),
            "avg_gold":   round(dfChampion["goldEarned"].mean()),
        },
        "damage": {
            "total": int(dfChampion["totalDamageDealtToChampions"].sum()),
            "avg":   round(dfChampion["totalDamageDealtToChampions"].mean()),
        },
        "farm": {
            "total": farm_total,
            "avg":   farm_avg,
        },
        "vision": {
            "total": vision_total,
            "avg":   vision_avg,
        },
        "multikills": {
            "double": int(dfChampion["doubleKills"].sum()),
            "triple": int(dfChampion["tripleKills"].sum()),
            "quadra": int(dfChampion["quadraKills"].sum()),
            "penta":  int(dfChampion["pentaKills"].sum()),
        },
        "pings": {
            "total":        int(dfChampion[PINGS_LIST].sum().sum()),
            "avg_per_game": round(dfChampion[PINGS_LIST].sum(axis=1).mean(), 1),
        },
    }


# ── Chart data builders ───────────────────────────────────────────

def analyze_daily_evolution(df: pd.DataFrame) -> dict:
    """
    Builds daily performance evolution data for the charts.
    
    Returns a dict with labels (dates) and per-metric daily averages.
    """
    if df.empty:
        return {}

    df = df.copy()
    df["date"] = pd.to_datetime(df["gameCreation"], unit="ms")
    df["day"]  = df["date"].dt.date

    # Aggregate all-mode metrics by day
    g_all = df.groupby("day").agg(
        avg_kills   = ("kills",                       "mean"),
        avg_deaths  = ("deaths",                      "mean"),
        avg_assists = ("assists",                      "mean"),
        avg_damage  = ("totalDamageDealtToChampions",  "mean"),
        win_rate    = ("win",                          "mean"),
        games       = ("matchId",                      "count"),
    ).reset_index().sort_values("day")

    # Aggregate CLASSIC-only metrics by day and left-join onto all-mode data
    df_classic = _classic_only(df)
    if not df_classic.empty:
        df_classic = df_classic.copy()
        df_classic["day"] = df_classic["date"].dt.date
        g_classic = df_classic.groupby("day").agg(
            avg_farm   = ("totalMinionsKilled", "mean"),
            avg_vision = ("visionScore",        "mean"),
            avg_gold   = ("goldEarned",         "mean"),
        ).reset_index()
        # Days with no CLASSIC matches will have 0 for farm/vision/gold
        g_all = g_all.merge(g_classic, on="day", how="left").fillna(0)
    else:
        g_all["avg_farm"]   = 0
        g_all["avg_vision"] = 0
        g_all["avg_gold"]   = 0

    labels = [str(d) for d in g_all["day"]]

    return {
        "labels":      labels,
        "avg_kills":   [round(v, 1) for v in g_all["avg_kills"]],
        "avg_deaths":  [round(v, 1) for v in g_all["avg_deaths"]],
        "avg_assists": [round(v, 1) for v in g_all["avg_assists"]],
        "avg_damage":  [round(v, 0) for v in g_all["avg_damage"]],
        "avg_farm":    [round(v, 1) for v in g_all["avg_farm"]],
        "avg_vision":  [round(v, 1) for v in g_all["avg_vision"]],
        "avg_gold":    [round(v, 0) for v in g_all["avg_gold"]],
        # Convert 0-1 mean to percentage for chart rendering
        "win_rate":    [round(v * 100, 1) for v in g_all["win_rate"]],
        "games":       [int(v) for v in g_all["games"]],
    }


def analyze_lane_stats(df: pd.DataFrame) -> dict:
    """
    Computes games played and win rate per lane position.

    Restricted to CLASSIC matches because other modes have no defined positions.
    Rows with position 'Outros' (unrecognized / none) are excluded.
    Results are always returned in the canonical lane order:
        Top, Jungle, Mid, Adc, Support
    """
    df_classic = _classic_only(df)

    if df_classic.empty:
        return {"labels": [], "games": [], "winrate": []}

    df_c = df_classic.copy()
    df_c["lane_label"] = df_c["teamPosition"].map(LANE_MAP).fillna("Outros")
    df_c = df_c[df_c["lane_label"] != "Outros"]

    lane_order = ["Top", "Jungle", "Mid", "Adc", "Support"]
    g = df_c.groupby("lane_label").agg(
        games = ("matchId", "count"),
        wins  = ("win",     "sum"),
    ).reindex(lane_order, fill_value=0).reset_index()

    # Avoid division by zero for lanes with no matches
    g["winrate"] = (g["wins"] / g["games"].replace(0, 1) * 100).round(1)

    return {
        "labels":  lane_order,
        "games":   [int(v)   for v in g["games"]],
        "winrate": [float(v) for v in g["winrate"]],
    }


def analyze_time_patterns(df: pd.DataFrame) -> dict:
    """
    Breaks down play patterns by weekday and by hour of day.

    Weekday data includes hours played and win rate per day of the week.
    Hourly data includes win rate for each hour block (00h–23h).
    Day names are stored internally in Portuguese to match the frontend labels.
    """
    if df.empty:
        return {}

    df = df.copy()
    df["date"] = pd.to_datetime(df["gameCreation"], unit="ms")

    # Canonical weekday order used throughout the app
    day_order  = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]
    # Map English day names (from pandas) to Portuguese abbreviations
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

    # Group by hour-of-day block (0–23) and reindex to guarantee all 24 slots
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
    """
    Computes games played and win rate grouped by champion class tag.

    The classTag column must be pre-populated by the service layer via Data Dragon.
    Champions with an 'Unknown' tag (not found in the mapping) are excluded.
    Results are always returned in the canonical class order.
    """
    if df.empty:
        return {}

    CLASS_ORDER = ["Fighter", "Tank", "Mage", "Assassin", "Marksman", "Support"]

    df = df.copy()
    df = df[df["classTag"] != "Unknown"]

    g = (
        df.groupby("classTag").agg(games=("matchId", "count"), wins=("win", "sum")).reset_index()
        if not df.empty
        else pd.DataFrame(columns=["classTag", "games", "wins"])
    )
    g["winrate"] = (g["wins"] / g["games"].replace(0, 1) * 100).round(1)

    # Reindex to guarantee all six classes appear even with 0 games
    full = g.set_index("classTag").reindex(CLASS_ORDER, fill_value=0).reset_index()

    return {
        "labels":  CLASS_ORDER,
        "games":   [int(v)   for v in full["games"]],
        "winrate": [float(v) for v in full["winrate"]],
    }


def analyze_game_modes(df: pd.DataFrame) -> dict:
    """
    Computes match count, percentage share and win rate per game mode.

    Only the five known modes are tracked; any others are silently ignored
    because they are not represented in the frontend labels.
    Win rate is set to 0.0 for modes with no recorded matches.
    """
    if df.empty:
        return {}

    ORDER = ["CLASSIC", "ARAM", "CHERRY", "NEXUSBLITZ", "URF"]
    total = max(len(df), 1)

    g = df.groupby("gameMode").agg(
        games = ("matchId", "count"),
        wins  = ("win",     "sum"),
    ).reindex(ORDER, fill_value=0).reset_index()

    g["percentage"] = (g["games"] / total * 100).round(1)
    g["winrate"]    = (g["wins"] / g["games"].replace(0, 1) * 100).round(1)
    # Ensure modes with no games show 0% win rate instead of a computed value
    g.loc[g["games"] == 0, "winrate"] = 0.0

    return {
        "labels":      ORDER,
        "games":       [int(v)   for v in g["games"]],
        "percentages": [float(v) for v in g["percentage"]],
        "winrate":     [float(v) for v in g["winrate"]],
    }


def analyze_match_history(df: pd.DataFrame, patch: str) -> list:
    """
    Builds a list of recent match summaries for the match history panel.

    Returns the 20 most recent matches sorted by date descending.
    Champion portrait URLs are generated from Data Dragon using the current patch.
    Duration is formatted as "Xm YYs" for display.
    """
    if df.empty:
        return []

    # Human-readable labels for each known game mode
    GAME_MODE_LABELS = {
        "CLASSIC":    "Summoner's Rift",
        "ARAM":       "ARAM",
        "CHERRY":     "Arena",
        "NEXUSBLITZ": "Nexus Blitz",
        "URF":        "URF",
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
            # Data Dragon CDN URL for the champion's square portrait
            "champion_img": f"https://ddragon.leagueoflegends.com/cdn/{patch}/img/champion/{row['championName']}.png",
            "win":          bool(row["win"]),
            "kills":        k,
            "deaths":       d,
            "assists":      a,
            # KDA ratio: clamp deaths at 1 to avoid division by zero
            "kda":          round((k + a) / max(d, 1), 2),
            "damage":       int(row["totalDamageDealtToChampions"]),
            "gold":         int(row["goldEarned"]),
            "cs":           int(row["totalMinionsKilled"]),
            "duration":     f"{ds // 60}m {ds % 60:02d}s",
            # Fall back to raw mode key if not in the label map
            "gameMode":     GAME_MODE_LABELS.get(row["gameMode"], row["gameMode"]),
            "date":         row["date"].strftime("%d/%m/%Y"),
        })

    return history