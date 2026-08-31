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

    The old file is removed first, and success is judged by whether a file actually
    appeared rather than by the exit code. Both are load-bearing: `hemtt utils pbo
    extract` REFUSES to write over an existing file, and reports that refusal as
    "ERROR Output file already exists" on stdout while still exiting 0. Left alone
    that makes --force a silent no-op for stringtables -- configs get re-read from
    the updated mod while every display name stays at whatever the previous source
    said. NIArms hit exactly this moving to the V14 Workshop item: 23 of 27 packs
    kept the older item's names, and 67 magazines resolved to a raw $STR_ key.

    The config.bin path never had the problem only because out_bin is unlinked
    after each pack, so it is never there to collide with.
    """
    out_xml.unlink(missing_ok=True)
    for name in ("stringtable.xml", "Stringtable.xml"):
        run(["hemtt", "utils", "pbo", "extract", str(pbo), name, str(out_xml)], check=False)
        if out_xml.is_file():
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
        if not any(folder.is_dir() for folder in source.addon_paths):
            raise SystemExit(
                f"no addon directory under {source.path} "
                f"(looked in {', '.join(source.addon_dirs)})"
            )

        note = "  (resolve-only)" if source.resolve_only else ""
        print(f"{source.name}{note}")

        for spec, pack in sorted(source.packs.items()):
            pbo_stem, member = modinfo.pbo_member(spec)
            pbo = source.find_pbo(pbo_stem)
            if pbo is None:
                missing.append(f"{source.name}/{pbo_stem}")
                continue

            out_json = modinfo.DUMP / f"{pack}.json"
            out_xml = modinfo.DUMP / f"{pack}.stringtable.xml"
            # a sub-config pack never produces a stringtable, so requiring one
            # here would re-dump it on every run
            fresh = out_json.is_file() and (
                out_xml.is_file() or member != "config.bin"
            )
            if fresh and not args.force:
                print(f"  {pack:<16} up to date")
                continue

            out_bin = modinfo.DUMP / f"{pack}.bin"
            label = pbo.name if member == "config.bin" else f"{pbo.name}::{member}"
            print(f"  {pack:<16} <- {label}")
            # a sub-config never carries a stringtable of its own; the pbo's (if
            # any) belongs to whichever pack took its root config
            if member == "config.bin":
                dump_stringtable(pbo, out_xml)
            run(["hemtt", "utils", "pbo", "extract", str(pbo), member, str(out_bin)])
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
