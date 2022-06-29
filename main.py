import time
from requests import get
import csv
from os import path
from os import walk
from os import remove
import json

# Need to regenerate API key every 24 hours at https://developer.riotgames.com/
API_KEY = "RGAPI-99e23a75-b56b-4d31-9cea-6d6abd014fc7"
BASE_URL = "https://region.api.riotgames.com"
SUMMONERS_DATA = "summoners_data"
SUMMONERS_IDS = "summoners_id"
GAMES = "games"
MATCH_IDS = "match_ids"
MATCH = "match"
PARTICIPANT = "participant"
TEAM = "team"
MATCH_IDS_STATS = "match_ids_stats.csv"
TEAM_STATS = "team_stats.csv"
STATS = "stats.csv"
PARTICIPANT_STATS = "participant_stats.csv"
TARGET_SIZE = 200
# These variables are for simple indexing unique keys
PARTICIPANT_ID_AUTO_INC = 1
MATCH_ID_AUTO_INC = 1
TEAM_ID_AUTO_INC = 1


NEW_FILE = True


def get_players_matches(
    puuid: str, results_per_page: int = 100, page: int = 0, region: str = "europe"
):
    base = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/"
    data = get(
        f"{base}{puuid}/ids?type=ranked&start={page*results_per_page}&count={results_per_page}&api_key={API_KEY}"
    )
    return data.json()


def get_summoners_puuid(summoner_id: str, region: str):
    customised_url = BASE_URL.replace("region", region)
    data = get(
        f"{customised_url}/lol/summoner/v4/summoners/{summoner_id}?api_key={API_KEY}"
    )
    return data.json()


def get_league(region: str):
    suffix = "_" + region + ".csv"
    pathfile = path.join(SUMMONERS_IDS, SUMMONERS_IDS + suffix)
    if path.exists(pathfile):
        with open(pathfile) as f:
            reader = csv.reader(f)
            data = [row for row in reader]
            return data

    customised_url = BASE_URL.replace("region", region)
    data = get(
        f"{customised_url}/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5?api_key={API_KEY}"
    )
    data = data.json()
    summoners_ids = [[d["summonerId"]] for d in data["entries"]]
    with open(pathfile, "w") as f:
        writer = csv.writer(f)
        writer.writerows(summoners_ids)
        return summoners_ids


def save_game_json(match_id: str, region: str = "europe"):
    file_path = path.join(GAMES, match_id)
    base = f"https://{region}.api.riotgames.com/lol/match/v5/matches"
    if path.exists(file_path):
        return
    data = get(f"{base}/{match_id}?api_key={API_KEY}")
    if data.status_code != 200:
        raise Exception("Rate limit occur")

    data = data.json()

    with open(file_path, "w") as f:
        f.write(json.dumps(data))


def get_players_data(region: str):
    suffix = "_" + region + ".csv"
    filepath = path.join(SUMMONERS_DATA, SUMMONERS_DATA + suffix)
    if path.exists(filepath):
        with open(filepath) as f:
            reader = csv.DictReader(f)
            data = [row for row in reader]
            return data

    summoners_ids = [i[0] for i in get_league(region)]
    # Get summoners data and store it in csv file
    summoners_data = []
    for summoner_id in summoners_ids:
        time.sleep(1)
        summoners_data.append(get_summoners_puuid(summoner_id, region))
    with open(filepath, "w") as f:
        writer = csv.DictWriter(f, summoners_data[0].keys())
        writer.writeheader()
        writer.writerows(summoners_data)
    return summoners_data


def get_matches_id(region: str):
    suffix = "_" + region + ".csv"
    pathfile = path.join(MATCH_IDS + "_" + region, MATCH_IDS + suffix)
    if path.exists(pathfile):
        with open(pathfile) as f:
            reader = csv.reader(f)
            data = [row[0] for row in reader]
            return data

    if region == "euw1" or region == "eun1":
        main_region = "europe"
    elif region == "na1":
        main_region = "americas"
    else:
        main_region = "asia"

    players = get_players_data(region)
    current_page = 0
    match_ids = set()
    while len(match_ids) < TARGET_SIZE:
        for player in players:
            time.sleep(1)
            matches = get_players_matches(
                player["puuid"], 100, current_page, main_region
            )
            for m in matches:
                match_ids.add(m)
        current_page += 1
    with open(pathfile, "w") as f:
        writer = csv.writer(f)
        writer.writerows([[m] for m in match_ids])
    return match_ids


def get_schema(schema: str):
    file_name = ""
    if schema == MATCH:
        file_name = "matchStatsStructure.json"
    elif schema == TEAM:
        file_name = "teamStatsStructure.json"
    elif schema == PARTICIPANT:
        file_name = "statsStructure.json"
    else:
        print("Bad schema request")
        return

    with open(f"{path.curdir}/{file_name}", "r") as f:
        raw_structure = json.load(f)
    schema_structure = []
    for k in raw_structure.keys():
        schema_structure.append(k)

    return schema_structure


def data_cleanse_and_feature_selection_save_to_csv(match_id: str):
    reader_path = path.join(GAMES, match_id)
    if path.exists(reader_path):
        with open(reader_path) as f:
            data = json.load(f)

    global PARTICIPANT_ID_AUTO_INC
    global MATCH_ID_AUTO_INC
    global TEAM_ID_AUTO_INC
    team_stats_schema = get_schema(TEAM)
    stats_schema = get_schema(PARTICIPANT)
    stats_data = []
    team_stats_data = []
    participants_data = []
    if not data["info"]:
        print(data)

    for p in data["info"].get("participants"):

        selected_features_item = {condition: p[condition] for condition in stats_schema}
        stats_data.append(
            {
                "p_id": PARTICIPANT_ID_AUTO_INC,
                **selected_features_item,
                "win": 1 if selected_features_item["win"] else 0,
            }
        )
        participants_data.append(
            {
                "p_id": PARTICIPANT_ID_AUTO_INC,
                "t_id": TEAM_ID_AUTO_INC
                if len(participants_data) < 5
                else TEAM_ID_AUTO_INC + 1,
                "m_id": MATCH_ID_AUTO_INC,
            }
        )
        PARTICIPANT_ID_AUTO_INC += 1

    selected_features_match_id = {
        "m_id": MATCH_ID_AUTO_INC,
        "gameId": data["info"].get("gameId"),
        "matchId": match_id,
        "gameDuration": data["info"].get("gameDuration"),
        "season": data["info"].get("gameVersion").split(".")[0],
        "gameVersion": data["info"].get("gameVersion"),
    }
    for team in data["info"]["teams"]:
        team_data = {}
        for i in team_stats_schema:
            if "." in i:
                nested_indices = i.split(".")
                value = (
                    team.get(nested_indices[0])
                    .get(nested_indices[1])
                    .get(nested_indices[2])
                )
                team_data = {**team_data, i: value}
        team_data = {
            **team_data,
            "win": 1 if team["win"] else 0,
            "teamId": TEAM_ID_AUTO_INC
            if len(team_stats_data) < 1
            else TEAM_ID_AUTO_INC + 1,
            "m_id": MATCH_ID_AUTO_INC,
        }
        team_stats_data.append(team_data)
    MATCH_ID_AUTO_INC += 1
    TEAM_ID_AUTO_INC += 2
    global NEW_FILE
    with open(PARTICIPANT_STATS, "a+", newline="") as f:
        writer = csv.DictWriter(f, participants_data[0].keys())
        # if not path.exists(f"{path.curdir}/{PARTICIPANT_STATS}"):
        if NEW_FILE:
            writer.writeheader()
        writer.writerows(participants_data)

    with open(STATS, "a+", newline="") as f:
        writer = csv.DictWriter(f, stats_data[0].keys())
        # if not path.exists(f"{path.curdir}/{STATS}"):
        if NEW_FILE:
            writer.writeheader()
        writer.writerows(stats_data)

    with open(TEAM_STATS, "a+", newline="") as f:
        writer = csv.DictWriter(f, team_stats_data[0].keys())
        # if not path.exists(f"{path.curdir}/{TEAM_STATS}"):
        if NEW_FILE:
            writer.writeheader()
        writer.writerows(team_stats_data)

    with open(MATCH_IDS_STATS, "a+", newline="") as f:
        writer = csv.writer(f)
        # if not path.exists(f"{path.curdir}/{MATCH_IDS_STATS}"):
        if NEW_FILE:
            writer.writerow(selected_features_match_id.keys())
            NEW_FILE = False
        writer.writerow(selected_features_match_id.values())


def generate_data_files():
    regions = {"europe": ["eun1", "euw1"], "americas": ["na1"], "asia": ["jp1", "kr"]}
    sub_regions_to_regions = {}
    for key, values in regions.items():
        for v in values:
            sub_regions_to_regions = {**sub_regions_to_regions, v: key}
    sub_regions = []
    matches_distributed = {}
    for region in regions.values():
        for r in region:
            sub_regions.append(r)
    for sr in sub_regions:
        matches_distributed = {**matches_distributed, sr: get_matches_id(sr)}
    for sr in matches_distributed.keys():
        for match in matches_distributed[sr]:
            time.sleep(2)
            save_game_json(match, sub_regions_to_regions[sr])

# a utility function to remove incorrect files
def check_and_delete_broken_files(match_id: str):
    file_path = path.join(GAMES, match_id)
    if path.exists(file_path):
        with open(file_path) as f:
            data = json.load(f)
    try:
        if data["info"]:
            pass
    except:
        remove(file_path)
        print(match_id + " has been deleted")

if __name__ == "__main__":
    # This function does 4 API intersections till we get the games data
    #generate_data_files()
    # Next function goes over all match files, extracting and parsing relevant data to seperated files,
    filenames = next(walk("./games"), (None, None, []))[2]
    # Check for broken files, can be caused by bad resposnse from the api to riot
    #for f in filenames:
        #check_and_delete_broken_files(f)
    for f in filenames:
        data_cleanse_and_feature_selection_save_to_csv(f)

