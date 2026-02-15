#!/usr/bin/env python3

import json
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

dir = Path(__file__).resolve().parent

SERVICE_URL = "https://www.voiceability.org/support-and-help/services-in-your-area"


def get_areas(url=SERVICE_URL, timeout: int = 10):
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    results = {}

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "/services-by-location/" in href:
            name = a.get_text(strip=True)
            if not name:
                continue
            full = urljoin(url, href)
            # prefer first occurrence if duplicates appear
            if name not in results:
                results[name] = full

    return results


def save_changes(results):
    with open(dir / "served_areas.json", "w+", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    areas = get_areas()
    print(f"Found {len(areas)} areas")
    save_changes(areas)
