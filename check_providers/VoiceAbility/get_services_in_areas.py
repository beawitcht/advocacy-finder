import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent


def get_services(timeout=10):

    with open(BASE_DIR / "served_areas.json", "r", encoding="utf-8") as f:
        areas = json.load(f)
    results = {}
    headers = {"User-Agent": "Mozilla/5.0 (compatible; script/1.0)"}

    for area, url in areas.items():
        try:
            r = requests.get(url, timeout=timeout, headers=headers)
            r.raise_for_status()
        except Exception as e:
            results[area] = {"error": str(e)}
            continue

        soup = BeautifulSoup(r.text, "html.parser")

        elems = soup.select(".row__advocacyByServiceLocation")
        values = []
        for el in elems:
            spans = el.find_all("span")
            for span in spans:
                text = span.get_text(strip=True)
                if text:
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
