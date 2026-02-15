import json
import os
from datetime import datetime
from pathlib import Path
import importlib.util
import traceback
from typing import Dict, Any

import requests


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = Path(__file__).resolve().parent.parent
from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / '.env')

def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_log(text: str):
    log_path = BASE_DIR / "changes.log"
    ts = datetime.utcnow().isoformat() + "Z"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {text}\n")


def _send_discord(content: str):
    webhook = os.getenv("DISCORD_WEBHOOK")
    if not webhook:
        return False
    try:
        requests.post(webhook, json={"content": content}, timeout=10)
        return True
    except Exception:
        return False


def _diff_areas(old: Dict[str, str], new: Dict[str, str]) -> Dict[str, Any]:
    old = old or {}
    new = new or {}
    added = [k for k in new.keys() if k not in old]
    removed = [k for k in old.keys() if k not in new]
    changed = [k for k in new.keys() if k in old and old.get(k) != new.get(k)]
    return {"added": added, "removed": removed, "changed": changed}


def _diff_services(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    old = old or {}
    new = new or {}
    result: Dict[str, Dict[str, Any]] = {}
    all_keys = set(old.keys()) | set(new.keys())
    for k in sorted(all_keys):
        old_vals = set(old.get(k, []))
        new_vals = set(new.get(k, []))
        added = sorted(new_vals - old_vals)
        removed = sorted(old_vals - new_vals)
        if added or removed:
            result[k] = {"added": added, "removed": removed}
    return result


def _build_readable_message(provider_name: str, area_diff: Dict[str, Any], services_diff: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"Changes Detected in {provider_name}:")
    lines.append("")
    # Areas section
    if area_diff and (area_diff.get("added") or area_diff.get("removed") or area_diff.get("changed")):
        lines.append("\tProvided Areas Have changed:")
        if area_diff.get("added"):
            lines.append("\t\tAdded:")
            for a in area_diff.get("added", []):
                lines.append(f"\t\t\t{a}")
        if area_diff.get("removed"):
            lines.append("\t\tRemoved:")
            for a in area_diff.get("removed", []):
                lines.append(f"\t\t\t{a}")
        if area_diff.get("changed"):
            lines.append("\t\tChanged URLs:")
            for a in area_diff.get("changed", []):
                lines.append(f"\t\t\t{a}")
        lines.append("")
    # Services section
    if services_diff:
        for area, changes in services_diff.items():
            lines.append(f"\tServices have changed in {area}:")
            if changes.get("added"):
                lines.append("\t\tAdded:")
                for s in changes.get("added", []):
                    lines.append(f"\t\t\t{s}")
            if changes.get("removed"):
                lines.append("\t\tRemoved:")
                for s in changes.get("removed", []):
                    lines.append(f"\t\t\t{s}")

    return "\n".join(lines)


def _import_module_from_path(path: Path):
    # import with a unique module name to avoid collisions when multiple providers
    mod_name = f"{path.stem}_{path.parent.name}"
    spec = importlib.util.spec_from_file_location(mod_name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def process_provider(provider_dir: Path, timeout: int = 10):
    """Run get_areas, compare & save changes, then run get_services_in_areas and compare/save.

    Returns tuple(changes_summary_str_or_empty, exception_message_or_empty)
    """
    try:
        ga_path = provider_dir / "get_areas.py"
        gs_path = provider_dir / "get_services_in_areas.py"
        summary_lines = []

        if ga_path.exists():
            ga_mod = _import_module_from_path(ga_path)
            print(f"Getting areas for {provider_dir.name}")
            new_areas = ga_mod.get_areas(timeout=timeout)
            old_areas = _load_json(provider_dir / "served_areas.json") or {}
            area_diff = _diff_areas(old_areas, new_areas)
            if area_diff.get("added") or area_diff.get("removed") or area_diff.get("changed"):
                summary_lines.append("get_areas")
                # save changes using module's save_changes
                if hasattr(ga_mod, "save_changes"):
                    ga_mod.save_changes(new_areas)
            # ensure file exists even if no changes
        else:
            summary_lines.append("get_areas.py not found")

        if gs_path.exists():
            gs_mod = _import_module_from_path(gs_path)
            # prefer `main`, fall back to `get_services` if present
            if hasattr(gs_mod, "main"):
                print(f"Getting services for {provider_dir.name}")
                new_services = gs_mod.main(timeout=timeout)
            elif hasattr(gs_mod, "get_services"):
                print(f"Getting services for {provider_dir.name}")
                new_services = gs_mod.get_services(timeout=timeout)
            else:
                new_services = None

            if new_services is not None:
                old_services = _load_json(provider_dir / "services_in_area.json") or {}
                services_diff = _diff_services(old_services, new_services)
                if services_diff:
                    summary_lines.append("get_services_in_areas")
                    # save services when module provides a saver
                    if hasattr(gs_mod, "save_changes"):
                        gs_mod.save_changes(new_services)
                    # save services if module provides a saver
                    if hasattr(gs_mod, "save_changes"):
                        gs_mod.save_changes(new_services)
        else:
            summary_lines.append("get_services_in_areas.py not found")

        # build a readable summary message if there are any changes
        if summary_lines:
            # summary_lines only indicates which sections changed; build full message
            summary_msg = _build_readable_message(provider_dir.name, locals().get('area_diff', {}), locals().get('services_diff', {}))
        else:
            summary_msg = ""
        return summary_msg, ""
    except Exception:
        return "", traceback.format_exc()


def main(timeout: int = 10):
    results = {}
    for child in sorted(BASE_DIR.iterdir()):
        if not child.is_dir():
            continue
        summary, err = process_provider(child, timeout=timeout)
        if err:
            msg = f"{child.name}: ERROR\n{err}"
            _write_log(msg)
            results[child.name] = {"error": True, "detail": err}
            continue
        if summary:
            msg = f"{child.name}: {summary}"
            _write_log(msg)
            results[child.name] = {"changed": True, "detail": summary}
            # send discord notification if webhook configured
            try:
                _send_discord(f"Changes detected for {child.name}: {summary}")
            except Exception:
                pass
        else:
            results[child.name] = {"changed": False}
    return results


if __name__ == "__main__":
    out = main()
