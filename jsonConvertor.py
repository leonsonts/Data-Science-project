import json
from os import path
import csv
#fullChampsData is a resource from https://developer.riotgames.com/docs/lol
CHAMPIONS = "champions"
def json_reader_convertor(filename, new_filename):
    file_path = path.join(CHAMPIONS, new_filename)
    if path.exists(file_path):
        return

    with open(f"{CHAMPIONS}/{filename}.json", "r") as f:
        data = json.load(f)
    data = data["data"]
    champs = []
    for item in data.values():
        new_item = {"name": item["name"],"title": item["title"], "id": item["key"],  "tags": item["tags"]}
        champs.append(new_item)
    with open(file_path, "w") as f:
        writer = csv.DictWriter(f, champs[0].keys())
        writer.writeheader()
        writer.writerows(champs)


json_reader_convertor("fullChampionsData", "champions.csv")
