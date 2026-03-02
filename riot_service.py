import time
import os
from dotenv import load_dotenv
import requests
import pandas as pd
from datetime import timedelta, datetime

load_dotenv()

token = os.getenv("RIOT_API")

def editLinkApi(link:str):

    apiToken = token
    return link, {"api_key": apiToken}

def tryRequestApi(url, params):

    max_retries = 5

    for i in range(max_retries):

        resp = requests.get(url, params=params)

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("New retry after:", 121)) # Padrão de 121 segundos
            print(f"Request limit reached. New retry in {retry_after} seconds...")
            time.sleep(retry_after)
        elif resp.status_code == 200:
            return resp.json()
        else:
            print(f"Error {resp.status_code}: {resp.text}")
            break

    return {}

def convertToDataFrame(matchesData):
    """
    Converts a list of match data into a pandas DataFrame

    Args:
        matchesData (list): List of dictionaries containing match data

    Returns:
        pandas.DataFrame: DataFrame containing match data
    """
    return pd.DataFrame(matchesData)

# ---------- Functions Api links ----------

def accountInfo(region:str, nome:str, tag:str):

    linkApi = "https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{nome}/{tag}"
    linkApi = linkApi.format(region=region, nome=nome, tag=tag)
    url, params = editLinkApi(linkApi)

    return tryRequestApi(url, params)

def idMatchs(region:str, puuid:str, count=50, start=0):

    linkApi = "https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start={start}&count={count}"
    linkApi = linkApi.format(region=region, puuid=puuid, count=count, start=start)
    url, params = editLinkApi(linkApi)

    return tryRequestApi(url, params)

def infoMatchs(region, idMatch):

    linkApi = "https://{region}.api.riotgames.com/lol/match/v5/matches/{idMatch}"
    linkApi = linkApi.format(region=region, idMatch=idMatch)
    url, params = editLinkApi(linkApi)

    return tryRequestApi(url, params)

# ---------- Collect Matches ----------

def collectMultipleMatchesData(region, nome, tag):
    """
    Collects data from all matches for a specific player.

    Args:

        region (str): Player's region (e.g., "americas")
        name (str): Player's name
        tag (str): Player's tag

    Returns:

        list: List of dictionaries containing match data
    """

    # Get account information
    account = accountInfo(region, nome, tag)
    if not account:
        print("We were unable to retrieve account information. Please check the name, tag and region.")
        return []
    puuid = account["puuid"]
    
    allMatchIds = []
    start_index = 0
    count_per_request = 30 

    ##while True:
    matchIds_page = idMatchs(region, puuid, count=60, start=0)
    
    ##if start_index < 30:
    ##    break # No more match IDs to retrieve
    
    allMatchIds.extend(matchIds_page)
    start_index += count_per_request
    
    print(f"All IDs from the matchs collected : {len(allMatchIds)}")

    # List for storing match data
    matchesData = []
    
    # Collect data from all matchs id
    for i, matchId in enumerate(allMatchIds):
        print(f"Collecting match data {i+1}/{len(allMatchIds)}: {matchId}")
        
        # Get mactch information
        matchInfo = infoMatchs(region, matchId)
        
        if not matchInfo:
            print(f"It was not possible to obtain information for the match {matchId}")
            continue
        
        # Find player position in the player list
        participants = matchInfo["info"]["participants"]
        playerPosition = None
        
        for j, participant in enumerate(participants):
            if participant["puuid"] == puuid:
                playerPosition = j
                break
        
        if playerPosition is None:
            print(f"Player not found in the match {matchId}")
            continue
        
        # Extract data from the matchs
        playerData = participants[playerPosition]
        
        matchData = {
            "matchId": matchId,
            "gameCreation": matchInfo["info"]["gameCreation"],
            "gameDuration": matchInfo["info"]["gameDuration"],
            "gameMode": matchInfo["info"]["gameMode"],
            "championName": playerData["championName"],
            "championId": playerData["championId"],
            "kills": playerData["kills"],
            "deaths": playerData["deaths"],
            "assists": playerData["assists"],
            "lane": playerData["lane"],
            "pentaKills": playerData["pentaKills"],
            "win": playerData["win"],
            "totalDamageDealtToChampions": playerData["totalDamageDealtToChampions"],
            "totalMinionsKilled": playerData["totalMinionsKilled"],
            "goldEarned": playerData["goldEarned"],
            "visionScore": playerData["visionScore"],
            "wardsPlaced": playerData["wardsPlaced"],
            "wardsKilled": playerData["wardsKilled"],
            "firstBloodKill": playerData["firstBloodKill"],
            "doubleKills": playerData["doubleKills"],
            "tripleKills": playerData["tripleKills"],
            "quadraKills": playerData["quadraKills"],
            "teamPosition": playerData["teamPosition"],
            "totalDamageTaken": playerData["totalDamageTaken"]
        }
        
        matchesData.append(matchData)
    
    return matchesData

# ---------- Analyze Matches ----------

def analyze_general_status (df):

    general_status = {}

    # Win Total/Rate

    general_status["matchResult"] = {

        'total_win' : int(df['win'].sum()), 
        'total_loss' : int((~df['win']).sum()), 
        'win_rate' : round(df['win'].mean() * 100, 2), # Convert to percentage
        'total_time_played': str(timedelta(seconds=int(df['gameDuration'].sum())))
    }

    general_status["kda"] = {

        "kda_ratio": round(
            (df['kills'].sum() + df['assists'].sum()) /
             max(df['deaths'].sum(), 1), 2),
        "total_kills": int(df['kills'].sum()),
        "total_deaths": int(df['deaths'].sum()),
        "total_assists": int(df['assists'].sum()),
        "avg_kills": round(df['kills'].mean(), 2),
        "avg_deaths": round(df['deaths'].mean(), 2),
        "avg_assists": round(df['assists'].mean(), 2),

    }

    general_status["economy"] = {
        
        "total_gold": int(df['goldEarned'].sum()),
        "avg_gold": round(df['goldEarned'].mean(), 2)
    }

    # --------- Damage ---------
    general_status['damage'] = {
        "total": int(df['totalDamageDealtToChampions'].sum()),
        "avg": round(df['totalDamageDealtToChampions'].mean(), 2)
    }

    # --------- Farm ---------
    general_status['farm'] = {
        "total": int(df['totalMinionsKilled'].sum()),
        "avg": int(df['totalMinionsKilled'].mean())
    }

    # --------- Vision ---------
    general_status['vision'] = {
        "total": int(df['visionScore'].sum()),
        "avg": int(df['visionScore'].mean())
    }

    # --------- Multikills ---------
    general_status['multikills'] = {
        "double": int(df['doubleKills'].sum()),
        "triple": int(df['tripleKills'].sum()),
        "quadra": int(df['quadraKills'].sum()),
        "penta": int(df['pentaKills'].sum())
    }

    return general_status

def analyzeMatchData(df):
    """
    Realiza análises nos dados das partidas coletadas.
    
    Args:
        df (pandas.DataFrame): DataFrame com os dados das partidas.
        
    Returns:
        dict: Dicionário contendo os resultados das análises.
    """
    analysisResults = {}
    
    # KDA (Kills + Assists / Deaths)
    df['kda'] = (df['kills'] + df['assists']) / df['deaths'].replace(0, 1) # Avoid division by zero
    analysisResults['average_kda'] = df['kda'].mean()
    
    # Win Total/Rate
    analysisResults['total_win'] = df['win'].sum() 
    analysisResults['total_loss'] = (~df['win']).sum() 
    analysisResults['win_rate'] = df['win'].mean() * 100 # Convert to percentage
    
    # stats per game
    analysisResults['total_kills'] = df['kills'].sum()
    analysisResults['average_kills'] = df['kills'].mean()
    analysisResults['total_deaths'] = df['deaths'].sum()
    analysisResults['average_deaths'] = df['deaths'].mean()
    analysisResults['total_assists'] = df['assists'].sum()
    analysisResults['average_assists'] = df['assists'].mean()
    analysisResults['total_damage_dealt'] = df['totalDamageDealtToChampions'].sum()
    analysisResults['average_damage_dealt'] = df['totalDamageDealtToChampions'].mean()
    analysisResults['total_minions_killed'] = df['totalMinionsKilled'].sum()
    analysisResults['average_minions_killed'] = df['totalMinionsKilled'].mean()
    analysisResults['total_gold_earned'] = df['goldEarned'].sum()
    analysisResults['average_gold_earned'] = df['goldEarned'].mean()
    analysisResults['total_vision_score'] = df['visionScore'].sum()
    analysisResults['average_vision_score'] = df['visionScore'].mean()
    
    # Total stats
    analysisResults['total_penta_kills'] = df['pentaKills'].sum()
    analysisResults['total_double_kills'] = df['doubleKills'].sum()
    analysisResults['total_triple_kills'] = df['tripleKills'].sum()
    analysisResults['total_quadra_kills'] = df['quadraKills'].sum()

    # Most played champion, KDA and Win Rate
    champion_stats = df.groupby("championName").agg(
        games_played=("championName", "size"),
        total_kills=("kills", "sum"),
        total_deaths=("deaths", "sum"),
        total_assists=("assists", "sum"),
        total_wins=("win", "sum")
    ).reset_index()
    champion_stats["kda"] = (champion_stats["total_kills"] + champion_stats["total_assists"]) / champion_stats["total_deaths"].replace(0, 1)
    champion_stats["win_rate"] = (champion_stats["total_wins"] / champion_stats["games_played"]) * 100

    # Order for games_played in asc and catch the first champion
    champion_stats = champion_stats.sort_values("games_played", ascending=False)
    most_played_champion = champion_stats.iloc[0]

    analysisResults["most_played_champion"] = most_played_champion["championName"]
    analysisResults["most_played_champion_total_kills"] = most_played_champion["total_kills"]
    analysisResults["most_played_champion_total_deaths"] = most_played_champion["total_deaths"]
    analysisResults["most_played_champion_total_assists"] = most_played_champion["total_assists"]
    analysisResults["most_played_champion"] = most_played_champion["championName"]
    analysisResults["most_played_champion_kda"] = most_played_champion["kda"]
    analysisResults["most_played_champion_win_rate"] = most_played_champion["win_rate"]
    analysisResults["most_played_champion_qtd_matchs"] = most_played_champion["games_played"]

    # Most played lane, KDA and Win Rate
    lane_stats = df.groupby("lane").agg(
        games_played=("lane", "size"),
        total_kills=("kills", "sum"),
        total_deaths=("deaths", "sum"),
        total_assists=("assists", "sum"),
        total_wins=("win", "sum")
    ).reset_index()
    lane_stats["kda"] = (lane_stats["total_kills"] + lane_stats["total_assists"]) / lane_stats["total_deaths"].replace(0, 1)
    lane_stats["win_rate"] = (lane_stats["total_wins"] / lane_stats["games_played"]) * 100
    most_played_lane = lane_stats.loc[lane_stats["games_played"].idxmax()]
    
    analysisResults["most_played_lane"] = most_played_lane["lane"]
    analysisResults["most_played_lane_total_kills"] = most_played_lane["total_kills"]
    analysisResults["most_played_lane_total_deaths"] = most_played_lane["total_deaths"]
    analysisResults["most_played_lane_total_assists"] = most_played_lane["total_assists"]
    analysisResults["most_played_lane_kda"] = most_played_lane["kda"]
    analysisResults["most_played_lane_win_rate"] = most_played_lane["win_rate"]

    # Most played game mode
    most_played_game_mode = df["gameMode"].value_counts().idxmax()
    analysisResults["most_played_game_mode"] = most_played_game_mode

    # Time matchs
    analysisResults['total_time_played'] = str(timedelta(seconds=int(df['gameDuration'].sum())))
    analysisResults['last_match_played'] = datetime.fromtimestamp(df["gameCreation"].iloc[-1]/1000).strftime("%d/%m/%Y")

    return analysisResults

def get_player_analysis(name, tag, region):
    
    player_name = name
    player_tag = tag
    player_region = region

    print(f"Coletando dados de partidas para {player_name}#{player_tag}...")

    allMatchesData = collectMultipleMatchesData(player_region, player_name, player_tag)

    if allMatchesData:
        df_matches = convertToDataFrame(allMatchesData)
        analysis_results = analyze_general_status(df_matches)
        
        return {
            "player_info": {
                "name": player_name,
                "tag": player_tag,
                "region": region,
            },
            "geral_matchs": analysis_results,
        }