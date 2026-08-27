"""Extract and derapify the source mod's config.bin files into _dump/ as JSON.

The JSON produced here is the input for gen_aceax.py. Which mods, which PBOs and
where they live all come from tools/mod.yml. Requires `hemtt` on PATH (1.19+, for
`utils pbo extract` and `utils config derapify -f json`).

Several sources are dumped into one _dump/, which is what lets a compat cover a mod
plus its add-ons -- and what makes an add-on resolvable at all, since its weapons
often inherit from the mod they extend.

Usage:
    python tools/dump_configs.py [--force]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import modinfo  # noqa: E402


def run(cmd: list[str], check: bool = True) -> bool:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        if not check:
            return False
        raise SystemExit(
            f"command failed ({result.returncode}): {' '.join(cmd)}\n{result.stderr.strip()}"
        )
    return True


def dump_stringtable(pbo: Path, out_xml: Path) -> None:
    """displayName is usually a $STR_ key, so the stringtables are needed too.

    Filename casing is not consistent between mods or even between packs of one mod.
    """
    for name in ("stringtable.xml", "Stringtable.xml"):
        if run(["hemtt", "utils", "pbo", "extract", str(pbo), name, str(out_xml)], check=False):
            return
    print(f"    (no stringtable in {pbo.name})", file=sys.stderr)


def main() -> int:
    mod = modinfo.load()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true", help="re-dump packs that already have JSON"
    )
    args = parser.parse_args()

    if shutil.which("hemtt") is None:
        raise SystemExit("hemtt not found on PATH")

    modinfo.DUMP.mkdir(exist_ok=True)
    missing: list[str] = []

    for source in mod.sources:
        addons = source.path / "addons"
        if not addons.is_dir():
            raise SystemExit(f"no addons directory under {source.path}")

        note = "  (resolve-only)" if source.resolve_only else ""
        print(f"{source.name}{note}")

        for pbo_stem, pack in sorted(source.packs.items()):
            pbo = addons / f"{pbo_stem}.pbo"
            if not pbo.is_file():
                missing.append(f"{source.name}/{pbo_stem}")
                continue

            out_json = modinfo.DUMP / f"{pack}.json"
            out_xml = modinfo.DUMP / f"{pack}.stringtable.xml"
            if out_json.is_file() and out_xml.is_file() and not args.force:
                print(f"  {pack:<16} up to date")
                continue

            out_bin = modinfo.DUMP / f"{pack}.bin"
            print(f"  {pack:<16} <- {pbo.name}")
            dump_stringtable(pbo, out_xml)
            run(["hemtt", "utils", "pbo", "extract", str(pbo), "config.bin", str(out_bin)])
            run(
                [
                    "hemtt",
                    "utils",
                    "config",
                    "derapify",
                    "-f",
                    "json",
                    str(out_bin),
                    str(out_json),
                ]
            )
            out_bin.unlink()

    if missing:
        print(f"\nwarning: {len(missing)} pbo(s) not found: {', '.join(missing)}", file=sys.stderr)

    print(f"\ndumped {len(list(modinfo.DUMP.glob('*.json')))} pack(s) to {modinfo.DUMP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
