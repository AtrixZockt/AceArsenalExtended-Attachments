"""Cross-check _dump/ against the config the running game actually loaded.

Everything else in this toolchain validates against _dump/, which is only an
approximation: the PBOs are merged here in a guessed load order, the arsenal
visibility rules are reimplemented in Python, and stringtables are parsed with a
regex because some mods ship malformed XML. None of that is true in game.

So: export the real thing from the debug console, then diff it against the dump.

    python tools/check_ingame.py --sqf     # print the snippet to paste in game
    python tools/check_ingame.py           # read the newest RPT and compare

The snippet is generated rather than kept as a .sqf so the class-name prefixes come
from the dump, and so this file stays identical between compat repos.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import modinfo  # noqa: E402
from modconfig import Config  # noqa: E402

START, END, ROW = "<<<ACEAX-EXPORT>>>", "<<<ACEAX-EXPORT-END>>>", "ACEAX-ROW;"

SQF = """// Paste into the Arma 3 debug console with {mod} loaded, then run
// `python tools/check_ingame.py`. Output goes to the RPT, not the clipboard,
// because there is too much of it for copyToClipboard to be reliable.
private _prefixes = {prefixes};
private _filter = "(getNumber (_x >> 'scope')) == 2 && (!isNumber (_x >> 'scopeArsenal') || getNumber (_x >> 'scopeArsenal') == 2)";
diag_log "{start}";
{{
    private _root = _x;
    private _entries = _filter configClasses (configFile >> _root);
    // ACEAX's own filter, rather than a copy of it. It applies the extra
    // LinkedItems/baseWeapon rule to CfgWeapons only, which is what we want.
    if (!isNil "aceax_gearinfo_fnc_filterConfigEntries") then {{
        _entries = [_root, _entries] call aceax_gearinfo_fnc_filterConfigEntries;
    }};
    {{
        private _c = _x;
        private _n = configName _c;
        private _l = toLower _n;
        if (_prefixes findIf {{ _l select [0, count _x] == _x }} != -1) then {{
            diag_log format ["{row}%1;%2;%3;%4", _root, _n, getText (_c >> "displayName"), getText (_c >> "model")];
        }};
    }} forEach _entries;
}} forEach {roots};
diag_log "{end}";
"""


def class_prefixes(config: Config) -> list[str]:
    """Leading `foo_` token of every dumped class name, lower-cased.

    NIArms needs two of these (hlc_ and nia_); most mods need one.
    """
    found = set()
    for item in config.arsenal_items():
        head = item.name.lower().split("_", 1)
        if len(head) == 2 and head[0]:
            found.add(head[0] + "_")
    return sorted(found)


def newest_rpt() -> Path | None:
    root = Path(os.environ.get("LOCALAPPDATA", "")) / "Arma 3"
    rpts = sorted(root.glob("*.rpt"), key=lambda p: p.stat().st_mtime, reverse=True)
    return rpts[0] if rpts else None


def read_export(rpt: Path) -> dict[str, tuple[str, str, str]]:
    """Parse the last export block: class name -> (config root, displayName, model)."""
    text = rpt.read_text(encoding="utf-8", errors="replace")
    if START not in text:
        return {}
    block = text.rsplit(START, 1)[1]
    block = block.split(END, 1)[0]

    rows: dict[str, tuple[str, str, str]] = {}
    for line in block.splitlines():
        # RPT prefixes every line with a timestamp
        idx = line.find(ROW)
        if idx == -1:
            continue
        parts = line[idx + len(ROW):].split(";")
        if len(parts) >= 4:
            rows[parts[1]] = (parts[0].strip(), parts[2].strip(), parts[3].strip())
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqf", action="store_true", help="print the in-game snippet")
    parser.add_argument("--rpt", type=Path, help="use this RPT instead of the newest")
    args = parser.parse_args()

    mod = modinfo.load()
    config = Config.load()

    if args.sqf:
        prefixes = class_prefixes(config)
        print(
            SQF.format(
                mod=mod.source_name,
                prefixes="[" + ", ".join(f'"{p}"' for p in prefixes) + "]",
                roots="[" + ", ".join(f'"{r}"' for r in config.roots) + "]",
                start=START,
                end=END,
                row=ROW,
            )
        )
        return 0

    rpt = args.rpt or newest_rpt()
    if rpt is None or not rpt.is_file():
        raise SystemExit("no RPT found under %LOCALAPPDATA%\\Arma 3")
    ingame = read_export(rpt)
    if not ingame:
        raise SystemExit(
            f"no export block in {rpt.name}\n"
            "run `python tools/check_ingame.py --sqf`, paste that in the debug "
            "console, then try again"
        )

    dumped = {w.name: (w.config_root, w.display_name, w.model) for w in config.arsenal_items()}
    lower_dumped = {k.lower(): k for k in dumped}

    print(f"{rpt.name}: {len(ingame)} items in game, {len(dumped)} in the dump\n")

    missing = [n for n in ingame if n.lower() not in lower_dumped]
    stale = [n for n in dumped if n.lower() not in {k.lower() for k in ingame}]
    renamed: list[str] = []
    for name, (_root, display, _model) in ingame.items():
        key = lower_dumped.get(name.lower())
        if key is None:
            continue
        if display and display != dumped[key][1]:
            renamed.append(f"{key}: game {display!r} != dump {dumped[key][1]!r}")

    if missing:
        print(f"{len(missing)} in game but NOT in the dump -- a pack missing from mod.yml:")
        for n in sorted(missing)[:20]:
            print(f"    {ingame[n][0]:<13} {n}  ({ingame[n][1]})")
        if len(missing) > 20:
            print(f"    ... and {len(missing) - 20} more")
        print()
    if stale:
        print(f"{len(stale)} in the dump but NOT in game -- stale dump, or the mod updated:")
        for n in sorted(stale)[:20]:
            print(f"    {n}")
        if len(stale) > 20:
            print(f"    ... and {len(stale) - 20} more")
        print()
    if renamed:
        print(f"{len(renamed)} displayName mismatch(es) -- stringtable resolution differs:")
        for r in sorted(renamed)[:20]:
            print(f"    {r}")
        print()

    if not (missing or stale or renamed):
        print("OK -- the dump matches the game exactly.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
