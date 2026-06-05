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
        values = []
        serv = None
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if "/services/" in href:
                serv = href.split("/services/", 1)[1].strip("/")
            if not serv:
                continue
            mapped = service_name_map.get(serv, serv)
            if mapped not in values:
                values.append(mapped)

        results[area] = values

    return results


service_name_map = {
    "nhs-complaints-advocacy": "IHCA",
    "mental-health-advocacy": "IMHA",
    "care%2C-support-and-safeguarding-(care-act)-advocacy": "ICAA",
    "advocacy-for-people-who-lack-capacity": "IMCA",
    "social-care-complaints-advocacy": "Social Care Complaints",
    "community-peer-and-citizen's-advocacy": "Community",
    "litigation-friend": "Litigation Friend",
    "children-and-young-person's-advocacy": "CYP"

}

def save_changes(results):
    with open(BASE_DIR / "services_in_area.json", "w+", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    services = get_services()
    print(f"Found {len(services)} services")
    save_changes(services)
