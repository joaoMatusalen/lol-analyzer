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
    Transforma a lista bruta de partidas no payload completo para o frontend.
    Reutilizado tanto na busca completa quanto no update incremental.
    """
    df = convert_to_dataframe(matches_raw)
 
    class_map    = get_champion_classes(patch)
    df["classTag"] = df["championName"].map(class_map).fillna("Unknown")
 
    general  = analyze_general_results(df)
    champion = analyze_most_played_champion(df)
 
    return {
        "player_info": {"name": name, "tag": tag, "region": region},
        "geral_matchs":     general,
        "champion_results": champion,
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
    Busca completa do zero. Coleta até MAX_MATCHES partidas.
    on_progress(step, message, current, total): callback opcional de progresso.
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

        # Find platform for summoner V4
    
    platform = defaultdict(list)

    for k, v in ROUTING_TO_PLATFORM.items():
        platform[v].append(k)

    for platform_summoner in platform[region]:
        summoner = summoner_info(platform_summoner, puuid)

        if summoner != {}:
            profile_icon_id = summoner.get("profileIconId", 1)
            break
        else:
            profile_icon_id = 1

    result = _build_result(matches, name, tag, region, patch)
    result["player_icon_img"] = (
        f"https://ddragon.leagueoflegends.com/cdn/{patch}/img/profileicon/{profile_icon_id}.png"
    )

    if on_progress:
        on_progress("done", "progress.done", 0, 0)

    return {
        "result":          result,
        "matches_raw":     matches,
        "latest_match_id_cache": last_match_id,
        "timestamp":       datetime.now(timezone.utc).isoformat(),
        "patch":           patch,
        "puuid":           puuid,
        "profile_icon_id": profile_icon_id,
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
    Update incremental: busca apenas partidas posteriores a latest_match_id_cache,
    junta com o histórico em cache e reprocessa.
    Retorna None se não houver partidas novas.
    """
    logger.info(f"[INCREMENTAL] {name}#{tag} desde {latest_match_id_cache}")

    if on_progress:
        on_progress("account", "Verificando novas partidas...", 0, 0)

    patch = get_latest_patch()

    def _prog(current, total):
        if on_progress:
            on_progress("collecting", "progress.newmatchs", current, total)

    puuid, last_match_id, new_matches = collect_player_matches(
        region, name, tag, after_match_id=latest_match_id_cache, on_progress=_prog
    )

    if not new_matches:
        logger.info(f"[INCREMENTAL] Sem partidas novas para {name}#{tag}.")
        return None
    
    # Find platform for summoner V4
    
    platform = defaultdict(list)

    for k, v in ROUTING_TO_PLATFORM.items():
        platform[v].append(k)

    for platform_summoner in platform[region]:
        summoner = summoner_info(platform_summoner, puuid)

        if summoner != {}:
            profile_icon_id = summoner.get("profileIconId", 1)
            break
        else:
            profile_icon_id = 1

    if on_progress:
        on_progress("processing", "Processando estatisticas...", 0, 0)

    all_matches = (new_matches + cached_matches)[:MAX_MATCHES]
    result      = _build_result(all_matches, name, tag, region, patch)
    result["player_icon_img"] = (
        f"https://ddragon.leagueoflegends.com/cdn/{patch}/img/profileicon/{profile_icon_id}.png"
    )

    if on_progress:
        on_progress("done", "progress.done", 0, 0)

    return {
        "result":          result,
        "matches_raw":     all_matches,
        "latest_match_id_cache": last_match_id,
        "timestamp":       datetime.now(timezone.utc).isoformat(),
        "patch":           patch,
        "puuid":           puuid_cached,
        "profile_icon_id": profile_icon_id,
    }
