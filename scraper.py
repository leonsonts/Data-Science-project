from bs4 import BeautifulSoup
from requests import get
from lxml import etree
import csv
from os import path

WEBSITE_BASE_URL = "https://u.gg/lol/champions/*/build"
CHAMPS = "champions"
# Validate response


def csv_extend_with_scraping(filename, new_file):
    file_path = path.join(CHAMPS, new_file)
    resource_path = path.join(CHAMPS, filename)
    if path.exists(file_path):
        return
    with open(resource_path) as f:
        reader = csv.DictReader(f)
        data = [row for row in reader]
    new_data = []
    for d in data:
        customized_url = WEBSITE_BASE_URL.replace("*", d["name"])
        if d["name"] == "Nunu & Willump":
            customized_url = WEBSITE_BASE_URL.replace("*", "nunu")
        if d["name"] == "Renata Glasc":
            customized_url = WEBSITE_BASE_URL.replace("*", "renata")
        web_data = get(customized_url)
        bs = BeautifulSoup(web_data.text, 'html.parser')
        dom = etree.HTML(str(bs))
        champ_tier_value = dom.xpath("//div[contains(@class, 'tier')]//text()")[0]
        champ_wr_label = dom.xpath("//div[contains(@class, 'win-rate')]//text()")[1]
        champ_wr_value = dom.xpath("//div[contains(@class, 'win-rate')]//text()")[0]
        champ_role = dom.xpath("//div[contains(@class, 'role-value')]//text()")[0]
        new_item = {**d, "Tier": champ_tier_value, champ_wr_label: champ_wr_value, "Role": champ_role}
        new_data.append(new_item)
    with open(file_path, "w") as f:
        writer = csv.DictWriter(f, new_data[0].keys())
        writer.writeheader()
        writer.writerows(new_data)


csv_extend_with_scraping("champions.csv", "champions_extended.csv")