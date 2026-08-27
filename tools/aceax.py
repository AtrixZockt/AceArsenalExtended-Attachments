"""Read the installed ACE3 Arsenal Extended, so its data need not be hand-copied.

`camo_values()` is what keeps `camo_values_from_aceax:` in overrides.yml honest, and
what lets init_overrides.py map colour words in display names onto real camo values.
Nothing here writes into the repo.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import steam  # noqa: E402

ACEAX_WORKSHOP_ID = "2522638637"


def gearinfo_pbo() -> Path | None:
    item = steam.find_workshop_item(ACEAX_WORKSHOP_ID)
    if item is None:
        return None
    pbo = item / "addons" / "aceax_gearinfo.pbo"
    return pbo if pbo.is_file() else None


@lru_cache(maxsize=1)
def _gearinfo_config() -> dict:
    pbo = gearinfo_pbo()
    if pbo is None:
        raise SystemExit(
            "ACE3 Arsenal Extended is not installed (Workshop "
            f"{ACEAX_WORKSHOP_ID}) -- subscribe to it, or pass the values by hand"
        )
    with tempfile.TemporaryDirectory() as tmp:
        raw, out = Path(tmp) / "config.bin", Path(tmp) / "config.json"
        subprocess.run(
            ["hemtt", "utils", "pbo", "extract", str(pbo), "config.bin", str(raw)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["hemtt", "utils", "config", "derapify", "-f", "json", str(raw), str(out)],
            check=True,
            capture_output=True,
        )
        return json.loads(out.read_text(encoding="utf-8"))


def camo_values() -> dict[str, str]:
    """Every XtdGearModels >> CamoBase value -> a best-effort English name.

    Labels in the built config are a mix: some are literals ("OD", "FDE"), some are
    stringtable keys ("$STR_aceax_gearinfo_Black") and the stringtable itself ships
    binarised. The key's own tail carries the English word, so it does just as well
    as a matching target -- which is what lets colour auto-mapping work off ACEAX's
    real data instead of a hardcoded synonym table.
    """
    camo_base = _gearinfo_config().get("XtdGearModels", {}).get("CamoBase", {})
    out: dict[str, str] = {}
    for value, meta in camo_base.items():
        if value.startswith("__") or not isinstance(meta, dict):
            continue
        label = meta.get("label") or ""
        if isinstance(label, str) and label.startswith("$"):
            label = re.sub(r"^\$STR_aceax_\w+?_", "", label).replace("_", " ")
        out[value] = str(label or value)
    return out


def camo_search_terms() -> dict[str, str]:
    """Lower-cased word -> camo value, for matching display-name tokens.

    The value name, its English label and its description all point at the same
    value, so "(Black)", "(BLK)" and "(Olive Drab)" all resolve.
    """
    camo_base = _gearinfo_config().get("XtdGearModels", {}).get("CamoBase", {})
    terms: dict[str, str] = {}
    for value, label in camo_values().items():
        description = camo_base.get(value, {}).get("description") or ""
        for term in (value, label, description):
            key = str(term).strip().lower()
            if key and not key.startswith("$"):
                terms.setdefault(key, value)
    return terms


if __name__ == "__main__":
    values = camo_values()
    print(f"{len(values)} CamoBase values in the installed ACEAX:")
    for value, label in sorted(values.items()):
        print(f"  {value:<12} {label}")
