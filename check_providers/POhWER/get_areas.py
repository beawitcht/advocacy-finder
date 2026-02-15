#!/usr/bin/env python3

import json
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

dir = Path(__file__).resolve().parent

SERVICE_URL = "https://www.pohwer.net/Pages/Category/in-your-area"
BASE_URL = "https://www.pohwer.net"
EXCLUDED_URLS = ["contact", "e-hill-neighbourhood-network-scheme-nns", "cdn-cgi"]


def get_areas(url=SERVICE_URL, timeout: int = 10):
    results = {}

    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
    except Exception:
        return results

    # parse index page
    try:
        soup = BeautifulSoup(resp.content, "lxml")
    except Exception:
        soup = BeautifulSoup(
            resp.content.decode(resp.encoding or "utf-8", errors="replace"),
            "html.parser",
        )

    # find the specific div containing the section list
    idx_container = soup.find("div", class_="content listContent")
    if not idx_container:
        return results

    section_links = []
    area_cat = idx_container.find_all("div", class_="listedPostText")
    for item in area_cat:
        endpoint = item.find("a", href=True)
        link = urljoin(BASE_URL, endpoint["href"])
        if link not in section_links:
            section_links.append(link)

    for sec in section_links:
        try:
            r = requests.get(sec, timeout=timeout)
            r.raise_for_status()
        except Exception:
            continue

        sp = BeautifulSoup(
            r.content.decode(r.encoding or "utf-8", errors="replace"), "html.parser"
        )

        cont = sp.find("div", class_="content postContent pageContent")
        if not cont:
            continue
        for a in cont.find_all("a", href=True):
            href = a["href"].strip()
            if not href:
                continue

            if any(val in href for val in EXCLUDED_URLS):
                continue

            full = urljoin(sec, href)
            name = a.get_text(strip=True).capitalize()
            path = urlparse(full, BASE_URL).path

            if not full.startswith(BASE_URL):
                continue

            if not name:
                raw_name = path.strip("/")
                name = raw_name.replace("-", " ").capitalize()
                results[name] = full
            else:
                results[name] = full

    return results


def save_changes(results):
    with open(dir / "served_areas.json", "w+", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    areas = get_areas()
    print(f"Found {len(areas)} areas")
    save_changes(areas)
