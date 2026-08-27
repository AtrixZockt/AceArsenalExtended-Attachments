"""Locate Steam Workshop items for Arma 3 across every installed Steam library.

Used by init_mod.py to find the source mod and by aceax.py to find ACEAX itself.
Nothing here writes files.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

ARMA3_APP_ID = "107410"

# Steam's own default, then the usual manual-install spots. Any further libraries
# come from libraryfolders.vdf inside one of these.
SEED_ROOTS = [
    Path(r"C:\Program Files (x86)\Steam"),
    Path(r"C:\Program Files\Steam"),
    Path(os.environ.get("ProgramFiles(x86)", "C:/")) / "Steam",
]


def steam_libraries() -> list[Path]:
    """Every Steam library root, seeds first."""
    found: list[Path] = []

    def add(path: Path) -> None:
        if path.is_dir() and path not in found:
            found.append(path)

    for seed in SEED_ROOTS:
        add(seed)

    # libraryfolders.vdf lists the other libraries as "path" "D:\\SteamLibrary"
    for seed in list(found):
        vdf = seed / "steamapps" / "libraryfolders.vdf"
        if not vdf.is_file():
            continue
        text = vdf.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r'"path"\s*"([^"]+)"', text):
            add(Path(match.group(1).replace("\\\\", "\\")))

    return found


def find_workshop_item(item_id: str | int, app_id: str = ARMA3_APP_ID) -> Path | None:
    """Path of a subscribed Workshop item, or None if it is not installed."""
    for library in steam_libraries():
        candidate = (
            library / "steamapps" / "workshop" / "content" / app_id / str(item_id)
        )
        if candidate.is_dir():
            return candidate
    return None


def read_mod_name(item: Path) -> str:
    """Best-effort display name of a Workshop item, from meta.cpp then mod.cpp."""
    for filename in ("meta.cpp", "mod.cpp"):
        path = item / filename
        if not path.is_file():
            continue
        match = re.search(
            r'^\s*name\s*=\s*"([^"]+)"', path.read_text(encoding="utf-8", errors="replace"), re.M
        )
        if match:
            return match.group(1).strip()
    return item.name
