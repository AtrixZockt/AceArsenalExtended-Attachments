"""Write tools/mod.yml for a new compat by inspecting a Workshop item.

The tedious part of starting a compat is working out which of a mod's PBOs actually
hold arsenal items -- BWMod has 47 PBOs and only 12 qualify, and one that does NOT
is called `bwa3_weapons`. So this scans every PBO's real config rather than guessing
from names.

Everything is scanned -- weapons and gear alike -- and the per-pack report breaks the
counts down by arsenal tab, so a gear-only mod like Military Gear Pack reports "216
headgear, 164 vest" instead of finding nothing.

It dumps every PBO to a temp directory and loads the lot through modconfig.Config,
the same loader the generator uses. Scanning packs one at a time would not work: a
weapon's parent class often lives in a different PBO (NIArms weapons inherit through
hlc_core), so inheritance only resolves once everything is loaded together.

Writes mod.yml only. The remaining scaffold files are listed at the end.

Usage:
    python tools/init_mod.py <workshop_id> [--prefix aceaxfoo] [--model-prefix foo]
                                           [--author "You"] [--kinds weapons] [--force]
"""

from __future__ import annotations

import argparse
import collections
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import modinfo  # noqa: E402
import steam  # noqa: E402
from modconfig import Config  # noqa: E402

TOOLS = Path(__file__).resolve().parent
MOD_YML = TOOLS / "mod.yml"

# Scanning always looks for everything, so the report can say "this mod is 216
# helmets and no weapons at all" rather than silently finding nothing. Which of
# them the compat actually covers is the `kinds:` line it writes at the end.
SCAN_KINDS = modinfo.ALL_KINDS


def dump_everything(addons: Path, into: Path) -> list[str]:
    """Derapify every pbo's config.bin (and stringtable) into `into`, dump-style."""
    stems = []
    for pbo in sorted(addons.glob("*.pbo")):
        stem = pbo.stem
        raw = into / f"{stem}.bin"
        got = subprocess.run(
            ["hemtt", "utils", "pbo", "extract", str(pbo), "config.bin", str(raw)],
            capture_output=True,
        )
        if got.returncode != 0:
            continue
        done = subprocess.run(
            [
                "hemtt", "utils", "config", "derapify", "-f", "json",
                str(raw), str(into / f"{stem}.json"),
            ],
            capture_output=True,
        )
        raw.unlink(missing_ok=True)
        if done.returncode != 0:
            continue
        for member in ("stringtable.xml", "Stringtable.xml"):
            if subprocess.run(
                [
                    "hemtt", "utils", "pbo", "extract", str(pbo), member,
                    str(into / f"{stem}.stringtable.xml"),
                ],
                capture_output=True,
            ).returncode == 0:
                break
        stems.append(stem)
    return stems


def short_names(stems: list[str]) -> dict[str, str]:
    """pbo stem -> short pack name, by dropping namespace segments.

    Splits on "_" and repeatedly drops the leading segment while it is shared as a
    leading segment by more than one pbo, plus any "wp" segment. A plain shared
    prefix is not enough: NIArms mixes hlc_* and nia_*, so nothing is common to all
    of them, yet both hlc_wp_ak and nia_wp_C96 should shorten to ak and c96.

    Never drops the last remaining segment. Collisions keep the full stem.
    """
    parts = {stem: stem.lower().split("_") for stem in stems}

    while True:
        heads: dict[str, int] = collections.Counter(
            p[0] for p in parts.values() if len(p) > 1
        )
        changed = False
        for stem, segs in parts.items():
            if len(segs) > 1 and (heads.get(segs[0], 0) > 1 or segs[0] == "wp"):
                parts[stem] = segs[1:]
                changed = True
        if not changed:
            break

    out: dict[str, str] = {}
    used: set[str] = set()
    for stem in stems:
        name = "_".join(parts[stem]) or stem.lower()
        if name in used:
            name = stem.lower()
        used.add(name)
        out[stem] = name
    return out


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _kind_note(counts: collections.Counter) -> str:
    return ", ".join(f"{kind} {n}" for kind, n in sorted(counts.items()))


def _select_kinds(requested: str | None, found: collections.Counter) -> list[str]:
    """The `kinds:` line to write.

    Defaults to whatever the scan actually found, which is the useful answer for
    both a weapons mod and a gear mod without having to know in advance which one
    you are looking at. `--kinds` overrides it, and warns about anything asked for
    that the mod does not have -- usually a sign the wrong pack list was picked up.
    """
    if requested:
        chosen = modinfo._kinds([k.strip() for k in requested.split(",") if k.strip()])
        empty = [k for k in chosen if not found.get(k)]
        if empty:
            print(f"\n  note: no items found for kind(s) {', '.join(empty)}")
        return list(chosen)

    chosen = [k for k in modinfo.ALL_KINDS if found.get(k)]
    print(f"\n  detected kinds: {_kind_note(found)}")
    return chosen


def find_base_packs(
    config: Config, item_packs: set[str], stems: list[str], dump: Path
) -> set[str]:
    """Packs with no items of their own that the item packs still need.

    Two ways to earn a place: another pack's item inherits through a class you
    define, or you own a stringtable key an item points at. The second is what
    finds bwa3_common, which declares no CfgWeapons at all but owns the
    $STR_BWA3_Author key every BWMod weapon uses for its `author`.
    """
    needed_classes: set[tuple[str, str]] = set()  # (config root, lower class name)
    needed_strings: set[str] = set()
    for item in config.arsenal_items():
        root = item.config_root
        needed_classes.update((root, c) for c in config.chain(root, item.name)[1:])
        for prop in ("displayName", "author", "descriptionShort"):
            value = config.resolve(root, item.name, prop)
            if isinstance(value, str) and value.startswith("$"):
                needed_strings.add(value[1:].lower())

    # iterate the dumped stems, not config.origin: a pack that declares no classes
    # at all never appears in origin, and bwa3_common is exactly that
    base: set[str] = set()
    for pack in set(stems) - item_packs:
        if any(config.origin[r].get(c) == pack for r, c in needed_classes):
            base.add(pack)
            continue
        table = dump / f"{pack}.stringtable.xml"
        if table.is_file():
            keys = {
                m.lower()
                for m in re.findall(
                    r'<Key\s+ID="([^"]+)"',
                    table.read_text(encoding="utf-8", errors="replace"),
                    re.I,
                )
            }
            if keys & needed_strings:
                base.add(pack)
    return base


def scan(ids: list[str], tmp: Path) -> tuple[Config, dict[str, Path], list[str]]:
    """Dump every listed Workshop item into one place and load them together.

    Several ids matter because an add-on's items often inherit from the mod it
    extends: BWA3 Add's rifles carry no scope of their own and their parents live
    in BWMod, so scanned alone none of them resolve to a weapon at all.
    """
    items: dict[str, Path] = {}
    stems: list[str] = []
    for item_id in ids:
        item = steam.find_workshop_item(item_id)
        if item is None:
            raise SystemExit(f"Workshop item {item_id} is not installed")
        addons = item / "addons"
        if not addons.is_dir():
            raise SystemExit(f"no addons directory under {item}")
        items[item_id] = item
        name = steam.read_mod_name(item)
        print(f"{name}  ({len(list(addons.glob('*.pbo')))} pbos) -- derapifying")
        stems += dump_everything(addons, tmp)
    return Config.load(tmp, base_packs=(), kinds=SCAN_KINDS), items, stems


def source_block(
    item_id: str,
    item: Path,
    packs: dict[str, str],
    base: set[str],
    resolve_only: bool = False,
) -> list[str]:
    """One `sources:` list entry, ready to write or paste."""
    lines = [
        f'  - name: "{steam.read_mod_name(item)}"',
        f"    workshop_id: {item_id}",
        f"    path: '{item}'",
    ]
    if resolve_only:
        lines.append("    resolve_only: true   # dumped so the rest resolves; not searched")
    if base:
        lines.append(f"    base_packs: [{', '.join(sorted(base))}]")
    lines.append("    packs:")
    for stem in sorted(packs, key=lambda s: packs[s]):
        note = "  # base classes / stringtable only" if stem in base else ""
        lines.append(f"      {stem}: {packs[stem]}{note}")
    return lines


def add_source(item_id: str) -> int:
    """Scan another mod and print a sources: entry for an existing mod.yml.

    Used to cover an add-on alongside the mod it extends. The already-listed
    sources are dumped too, otherwise the add-on's weapons will not resolve.
    """
    if not MOD_YML.exists():
        raise SystemExit(f"{MOD_YML} does not exist -- run init_mod.py without --add first")

    mod = modinfo.load()
    if any(s.workshop_id == str(item_id) for s in mod.sources):
        raise SystemExit(f"Workshop item {item_id} is already a source in {MOD_YML}")
    taken = {short for s in mod.sources for short in s.packs.values()}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        existing = [s.workshop_id for s in mod.sources if s.workshop_id]
        config, items, _ = scan(existing + [str(item_id)], tmp)
        item = items[str(item_id)]

        new_stems = {p.stem for p in (item / "addons").glob("*.pbo")}
        by_pack: dict[str, int] = collections.Counter()
        kinds: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
        for entry in config.arsenal_items():
            if entry.pack in new_stems and entry.kind in mod.kinds:
                by_pack[entry.pack] += 1
                kinds[entry.pack][entry.kind] += 1

        if not by_pack:
            raise SystemExit(
                f"\n{steam.read_mod_name(item)} contributed no arsenal-visible items "
                f"of kind {', '.join(mod.kinds)}, even with the existing sources "
                "dumped alongside it"
            )

        print()
        for pack in sorted(by_pack):
            print(f"  {pack:<28} {by_pack[pack]:>4} item(s)  [{_kind_note(kinds[pack])}]")

        packs = short_names(sorted(by_pack))
        clashes = {p for p in packs.values() if p in taken}
        if clashes:
            tag = slug(steam.read_mod_name(item))[:6] or "add"
            packs = {s: (f"{tag}_{n}" if n in clashes else n) for s, n in packs.items()}
            print(f"\n  renamed {len(clashes)} colliding pack name(s) with the '{tag}_' prefix")

    print("\nAppend this to `sources:` in tools/mod.yml:\n")
    print("\n".join(source_block(str(item_id), item, packs, set())))
    print("\nThen: python tools/dump_configs.py && python tools/gen_aceax.py --check")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workshop_id")
    parser.add_argument("--prefix", help="pbo/CfgPatches prefix, e.g. aceaxfoo")
    parser.add_argument("--model-prefix", help="prefix for generated model classes")
    parser.add_argument("--author", default="", help="your name, for CfgPatches")
    parser.add_argument("--force", action="store_true", help="overwrite an existing mod.yml")
    parser.add_argument(
        "--kinds",
        metavar="LIST",
        help="comma-separated arsenal tabs to cover, e.g. 'weapons' or "
        "'headgear,vest,goggles'. Defaults to everything the scan finds.",
    )
    parser.add_argument(
        "--requires",
        action="append",
        default=[],
        metavar="ID",
        help="another Workshop id this mod inherits from; dumped so it resolves, "
        "never searched for weapons. Repeatable.",
    )
    parser.add_argument(
        "--add",
        action="store_true",
        help="print a sources: block to append to an existing mod.yml instead of "
        "creating one -- for covering an add-on alongside the mod it extends",
    )
    args = parser.parse_args()

    if args.add:
        return add_source(args.workshop_id)

    if MOD_YML.exists() and not args.force:
        raise SystemExit(f"{MOD_YML} already exists -- pass --force, or --add")

    item = steam.find_workshop_item(args.workshop_id)
    if item is None:
        raise SystemExit(f"Workshop item {args.workshop_id} is not installed")
    addons = item / "addons"
    if not addons.is_dir():
        raise SystemExit(f"no addons directory under {item}")

    mod_name = steam.read_mod_name(item)
    total_pbos = len(list(addons.glob("*.pbo")))
    print(f"{mod_name}  ({total_pbos} pbos) -- derapifying, this takes a minute\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        stems = dump_everything(addons, tmp)
        required: dict[str, Path] = {}
        for req in args.requires:
            req_item = steam.find_workshop_item(req)
            if req_item is None:
                raise SystemExit(f"Workshop item {req} is not installed")
            print(f"  + {steam.read_mod_name(req_item)} (resolve-only)")
            required[req] = req_item
            # keep their stems: find_base_packs searches this list for the packs
            # our weapons actually lean on
            stems += dump_everything(req_item / "addons", tmp)
        config = Config.load(tmp, base_packs=(), kinds=SCAN_KINDS)

        # packs from a --requires mod exist only so this one resolves; their own
        # weapons are not ours to cover
        req_stems = {
            p.stem for r in required.values() for p in (r / "addons").glob("*.pbo")
        }
        by_pack: dict[str, int] = collections.Counter()
        kinds: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
        found_kinds: collections.Counter = collections.Counter()
        for entry in config.arsenal_items():
            if entry.pack in req_stems:
                continue
            by_pack[entry.pack] += 1
            kinds[entry.pack][entry.kind] += 1
            found_kinds[entry.kind] += 1
        item_packs = set(by_pack)
        # everything the covered items lean on, whichever mod it lives in
        needed = find_base_packs(config, item_packs, stems, tmp)
        base_packs = needed - req_stems
        resolve_packs = needed & req_stems

        for pack in sorted(item_packs | base_packs | resolve_packs):
            if pack in resolve_packs:
                print(f"  {pack:<28}    - from a required mod, for resolution")
            elif pack in base_packs:
                print(f"  {pack:<28}    - base classes / stringtable")
            else:
                # the tab breakdown matters: launchers are weapons too, and a mod
                # can be all gear, so this is what `kinds:` gets decided from
                print(
                    f"  {pack:<28} {by_pack[pack]:>4} item(s)"
                    f"  [{_kind_note(kinds[pack])}]"
                )
        others = len(stems) - len(item_packs | base_packs | resolve_packs)
        print(f"  {'':<28}      ({others} other pbo(s) skipped)")

        if not item_packs:
            hint = (
                ""
                if args.requires
                else (
                    "\n\nIf this mod extends another one, its items inherit scope and"
                    "\ntheir parent classes from it and cannot resolve alone. Re-run with"
                    "\n  --requires <workshop id of the mod it extends>"
                )
            )
            raise SystemExit(
                f"\nno pbo contained an arsenal-visible item -- nothing to do{hint}"
            )

        selected = _select_kinds(args.kinds, found_kinds)

        # which packs came from where, so each source lists only its own
        owner: dict[str, str] = {}
        for item_id, req_item in [(args.workshop_id, item)] + list(required.items()):
            for pbo in (req_item / "addons").glob("*.pbo"):
                owner[pbo.stem] = item_id

    packs = short_names(sorted(item_packs | base_packs | resolve_packs))
    prefix = args.prefix or f"aceax{slug(mod_name)[:8]}"
    model_prefix = args.model_prefix or slug(mod_name)[:8]

    lines = [
        "# Identity and sources of this compat. Everything mod-specific lives here, so",
        "# the .py files in this directory carry no mod identity and can be copied",
        "# verbatim -- pair them with a new mod.yml and overrides.yml.",
        "#",
        f"# Generated by init_mod.py from Workshop item {args.workshop_id}.",
        "# Check prefix and model_prefix before building -- they must be unique across every",
        "# compat a player might load at once.",
        f"prefix: {prefix}",
        f'name: "ACEAX {mod_name} Compat"',
        f'author: "{args.author}"',
        'version: "1.0.0"',
        "",
        f"model_prefix: {model_prefix}",
        "",
        "# Which arsenal tabs this compat covers. Detected from what the scan found;",
        "# trim it to narrow the scope. `weapons` is short for primary/handgun/launcher,",
        "# `gear` for headgear/uniform/vest/backpack/goggles.",
        f"kinds: [{', '.join(selected)}]",
        "",
        "# Short pack names must stay unique across every source: they become _dump/",
        "# filenames. Items from different sources sharing a display-name base land in",
        "# the same arsenal entry.",
        "sources:",
        "",
    ]

    main_packs = {s: packs[s] for s in packs if owner.get(s) == args.workshop_id}
    main_base = {s for s in base_packs if owner.get(s) == args.workshop_id}
    lines += source_block(args.workshop_id, item, main_packs, main_base)

    for req_id, req_item in required.items():
        req_packs = {
            s: packs[s] for s in packs
            if owner.get(s) == req_id and s in resolve_packs
        }
        lines.append("")
        lines += source_block(req_id, req_item, req_packs, set(), resolve_only=True)

    MOD_YML.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    skipped = total_pbos - len(item_packs) - len(base_packs)
    print(f"\nwrote {MOD_YML}")
    print(f"  {len(item_packs)} item pack(s), {len(base_packs)} base pack(s), {skipped} skipped")
    print(f"  kinds: {', '.join(selected)}")
    print(
        "\nStill to create by hand (see WORKFLOW.md):\n"
        f'  .hemtt/project.toml        prefix = "{prefix}"\n'
        "  .hemtt/launch.toml         CBA 450814997, ACE 463939057, ACEAX 2522638637,\n"
        f"                             + {args.workshop_id}\n"
        "  .gitignore  mod.cpp  LICENSE\n"
        f"  addons/main/$PBOPREFIX$    z\\{prefix}\\addons\\main\n"
        "\nThen: python tools/dump_configs.py && python tools/init_overrides.py"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
