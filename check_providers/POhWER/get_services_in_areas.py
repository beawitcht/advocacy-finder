import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent


def get_services(timeout=10):

    with open(BASE_DIR / "served_areas.json", "r", encoding="utf-8") as f:
        areas = json.load(f)
    results = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0"
    }

    for area, url in areas.items():
        try:
            r = requests.get(url, timeout=timeout, headers=headers)
            r.raise_for_status()
        except Exception as e:
            results[area] = {"error": str(e)}
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        values = []
        body = soup.find("section", class_="headerTextSubsite")

        list = body.find("ul")
        items = list.find_all("li")

        for item in items:

            if item.find_all("span"):
                for sub_item in item.find_all("span"):
                    if not sub_item.find("a"):
                        continue
                    text = sub_item.get_text(strip=True)
                    if text and text not in values:
                        values.append(text)
            else:
                text = item.get_text(strip=True)
                if text and text not in values:
                    values.append(text)

        results[area] = values

    return results


def save_changes(results):
    with open(BASE_DIR / "services_in_area.json", "w+", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    services = get_services()
    print(f"Found {len(services)} services")
    save_changes(services)
