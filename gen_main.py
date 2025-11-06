import csv
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from htmlmin import minify as htmlminify

BASE_DIR = os.path.dirname(__file__)
TEMPLATE_NAME = "index-template.html"
OUTPUT_NAME = "index.html"
PROVIDERS_CSV = os.path.join(BASE_DIR, "providers.csv")
AREAS_CSV = os.path.join(BASE_DIR, "area_provider_services.csv")


def load_providers(path):
    providers = {}
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            name = (r.get("provider") or "").strip()
            if not name:
                continue
            providers[name] = {
                "website": (r.get("website") or "").strip(),
                "email": (r.get("email") or "").strip(),
                "phone": (r.get("phone") or "").strip(),
            }
    return providers


def services_to_tags(s):
    if not s:
        return []
    # split on hyphen, strip whitespace, ignore empty tokens
    return [t.strip() for t in s.split("-") if t.strip()]


def load_areas(path, providers_map):
    areas = []
    provider_columns = [
        ("provider", "services offered"),
        ("provider2", "services2"),
        ("provider3", "services3"),
    ]
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            area_name = (row.get("area") or "").strip()
            if not area_name:
                continue
            area_providers = []
            for prov_col, serv_col in provider_columns:
                prov_name = (row.get(prov_col) or "").strip()
                if not prov_name:
                    continue
                serv_field = row.get(serv_col) or ""
                tags = services_to_tags(serv_field)
                # match provider info from providers.csv (exact match on trimmed name)
                info = providers_map.get(prov_name, {})
                area_providers.append(
                    {
                        "name": prov_name,
                        "website": info.get("website") or "",
                        "email": info.get("email") or "",
                        "phone": info.get("phone") or "",
                        "services": tags,
                    }
                )
            areas.append({"area": area_name, "providers": area_providers})
    return areas


def render(areas):
    env = Environment(
        loader=FileSystemLoader(BASE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tmpl = env.get_template(TEMPLATE_NAME)
    return tmpl.render(areas=areas)


def minify_html(html_str):
    return htmlminify(
        html_str,
        remove_comments=True,
        reduce_empty_attributes=True,
        remove_optional_attribute_quotes=False,
    )


def main():
    providers_map = load_providers(PROVIDERS_CSV)
    areas = load_areas(AREAS_CSV, providers_map)
    html = render(areas)
    html = minify_html(html)
    out_path = os.path.join(BASE_DIR, OUTPUT_NAME)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"Wrote {out_path} ({len(areas)} areas)")


if __name__ == "__main__":
    main()
