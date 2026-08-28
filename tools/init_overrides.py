"""Write a starter tools/overrides.yml from a dump, or refresh its camo list.

Run after dump_configs.py. It fills in the parts that are derivable -- every display
name token the mod uses, with colour words auto-mapped against ACEAX's own CamoBase
-- and leaves the parts that need judgement (`bases:`, labels) marked with TODO.

The generator raises KeyError on a missing section rather than defaulting, so every
required key is emitted even when empty.

Usage:
    python tools/init_overrides.py                # write a starter overrides.yml
    python tools/init_overrides.py --force        # overwrite an existing one
    python tools/init_overrides.py --refresh-camo # update only camo_values_from_aceax
"""

from __future__ import annotations

import argparse
import collections
import re
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import aceax  # noqa: E402
import modinfo  # noqa: E402
from modconfig import Config, parse_display_name  # noqa: E402

CAMO_BLOCK = re.compile(r"^camo_values_from_aceax:\s*\[[^\]]*\]", re.M)


def camo_list_block(values: list[str], width: int = 92) -> str:
    body = textwrap.fill(
        ", ".join(values), width=width - 2, initial_indent="  ", subsequent_indent="  "
    )
    return "camo_values_from_aceax: [\n" + body + "\n]"


def refresh_camo(path: Path) -> int:
    """Rewrite just the camo list, by text replacement so comments survive.

    A YAML round-trip would reformat the whole file and drop every hand-written
    comment, which is most of its value.
    """
    if not path.is_file():
        raise SystemExit(f"{path} does not exist -- run without --refresh-camo first")
    text = path.read_text(encoding="utf-8")
    if not CAMO_BLOCK.search(text):
        raise SystemExit("no 'camo_values_from_aceax: [...]' block found to refresh")

    values = sorted(aceax.camo_values())
    updated = CAMO_BLOCK.sub(lambda _: camo_list_block(values), text, count=1)
    if updated == text:
        print(f"camo list already current ({len(values)} values) -- no change")
        return 0
    path.write_text(updated, encoding="utf-8", newline="\n")
    print(f"refreshed camo list to {len(values)} values from the installed ACEAX")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite an existing file")
    parser.add_argument(
        "--refresh-camo", action="store_true", help="update only the camo list, keep the rest"
    )
    args = parser.parse_args()

    path = modinfo.OVERRIDES
    if args.refresh_camo:
        return refresh_camo(path)
    if path.exists() and not args.force:
        raise SystemExit(f"{path} already exists -- pass --force, or --refresh-camo")

    mod = modinfo.load()
    config = Config.load()
    items = config.arsenal_items()
    if not items:
        raise SystemExit(
            "no arsenal items in _dump/ -- run dump_configs.py first, and check that\n"
            f"`kinds:` in mod.yml ({', '.join(mod.kinds)}) matches what the mod ships"
        )

    # Counted exactly as written. Token matching is case-sensitive -- NIArms tells
    # "TAC" from "Tac" that way -- so a mod that spells one colour two ways gets a
    # line for each, and they are flagged below rather than silently merged.
    tokens: collections.Counter[str] = collections.Counter()
    for item in items:
        for token in parse_display_name(item.display_name)[1]:
            tokens[token] += 1

    camo_terms = aceax.camo_search_terms()
    mapped: dict[str, tuple[str, str]] = {}
    for token in tokens:
        value = camo_terms.get(token.strip().lower())
        mapped[token] = ("camo", value) if value else ("variant", _value_name(token))

    camo_tokens = {t: v for t, (a, v) in mapped.items() if a == "camo"}
    other_tokens = {t: v for t, (a, v) in mapped.items() if a != "camo"}

    out: list[str] = [
        "# Hand-written half of the config generation. gen_aceax.py derives everything else",
        f"# from the {mod.source_name} display names; this file supplies the judgement calls,",
        "# so re-running the generator after a mod update never destroys them.",
        "#",
        "# Started by init_overrides.py. Every TODO below needs a human.",
        "# Run `python tools/report.py --bases` and `--families` to see what to do next.",
        "",
        "# Tokens inside a (...) marker that should start a SEPARATE model rather than",
        "# become an option value -- typically an underbarrel grenade launcher.",
        "splitters: {}",
        "",
        "# displayName token -> [axis, value].",
        f"# {len(camo_tokens)} of {len(tokens)} auto-mapped against ACEAX's CamoBase.",
        "tokens:",
    ]

    if camo_tokens:
        out.append("  # -- recognised colours ---------------------------------------------")
        for token in sorted(camo_tokens, key=lambda t: -tokens[t]):
            out.append(f"  {_key(token) + ':':<22} [camo, {camo_tokens[token]}]"
                       f"   # {tokens[token]}x")
    if other_tokens:
        out.append("  # -- TODO: classify these. Common axes: barrel, mount, config,")
        out.append("  #    condition, caliber, variant. Delete any that are one-offs.")
        for token in sorted(other_tokens, key=lambda t: -tokens[t]):
            out.append(f"  {_key(token) + ':':<22} [variant, {other_tokens[token]}]"
                       f"   # {tokens[token]}x  TODO")

    variant_values = sorted(set(other_tokens.values()))
    out += [
        "",
        "# When a (...) marker holds several values they sometimes describe different",
        "# PARTS of one item rather than alternatives -- a uniform's top and its",
        "# trousers, \"(GREY+3CD)\". List the axes in order and the Nth token is put on",
        "# the Nth axis. Leave empty unless the mod does that.",
        "positional_axes: []",
        "",
        "# Which arsenal entry a parsed base name belongs to, and the option values that",
        "# place it there:   \"G36KA0\": {as: \"G36\", barrel: K, variant: A0}",
        "# TODO: run `python tools/report.py --families` for candidate groupings.",
        "bases: {}",
        "",
        "# Synthetic tokens taken from the class name rather than the display name.",
        "# Use these when the mod ships the same item several times over and only the",
        "# class name says which is which -- Tier One names every accessory",
        "# Tier1_<platform>_<accessory>, so the prefix is the only discriminator.",
        "class_prefixes: {}",
        "class_suffixes: {}",
        "",
        "# For mods that write an item AND everything bolted to it into one display",
        "# name -- \"Micro T-2/Leap/G33/LT 5/8\". Leave this out entirely unless the mod",
        "# does that; absent, names are parsed exactly as they were before it existed.",
        "#",
        "# Splitting on the separator does NOT work: component names contain it too",
        "# (\"LT 5/8\", \"AN/PVS-10\"). List the parts and they are matched longest-first,",
        "# anchored to the separator. See OPTIONS.md for the full shape.",
        "#",
        "# compose:",
        "#   separator: \"/\"",
        "#   parts:",
        "#     \"3X\": [magnifier, 3X]",
        "",
        "# Per-item corrections, applied last, keyed by class name. Add entries here",
        "# when the generator reports two items sharing the same option combination.",
        "weapons: {}",
        "",
        "# Every axis used above needs an entry. `camo` is deliberately without a `base`:",
        "# it is a conventional ACEAX option and inherits label, icon and swatches from",
        "# CamoBase.",
        "options:",
        "  camo:    {default: STD}",
    ]
    if variant_values:
        out.append(f"  variant: {{default: STD, base: {mod.model_prefix}_variant}}")
    out += [
        "",
        "# Dropdown order, most defining first.",
        "option_order: [" + ("variant, " if variant_values else "") + "camo]",
        "",
        "# Shared option classes emitted into XtdGearModels_Common.hpp. The",
        f"# {mod.model_prefix}_ prefix matters: Arma merges same-named config classes across",
        "# addons, so two ACEAX compats must not both define e.g. niarms_variant.",
        "option_bases:",
    ]
    if variant_values:
        out.append("  variant:")
        out.append(f"    class: {mod.model_prefix}_variant")
        out.append('    label: "Variant"')
        out.append("    values:")
        out.append('      STD: {label: "Standard"}')
        for value in variant_values:
            out.append(f'      {value + ":":<12} {{label: "{value}"}}   # TODO better label')
    else:
        out.append("  {}")

    out += [
        "",
        "# Camo values aceax_gearinfo already defines. Read from the installed ACEAX by",
        "# init_overrides.py -- refresh with `--refresh-camo` after an ACEAX update.",
        camo_list_block(sorted(aceax.camo_values())),
        "",
        "# Camo values needed on top of that shared palette. STD is the \"no marker\"",
        "# default every mod needs.",
        "camo_values:",
        '  STD: {label: "Standard"}',
    ]

    path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {path}")
    print(f"  {len(items)} items, {len(tokens)} distinct token(s)")
    print(f"  {len(camo_tokens)} auto-mapped to camo, {len(other_tokens)} left as TODO")

    # Tokens differing only in case are usually one thing spelled two ways, but
    # not always -- NIArms means different things by "TAC" and "Tac" -- so they
    # are pointed out rather than merged.
    folded: dict[str, list[str]] = collections.defaultdict(list)
    for token in tokens:
        folded[token.lower()].append(token)
    variants = {k: v for k, v in folded.items() if len(v) > 1}
    if variants:
        print(f"\n  {len(variants)} token(s) appear in more than one capitalisation:")
        for spellings in variants.values():
            print(f"    {' / '.join(sorted(spellings))}")
        print("  map them to the same value if they mean the same thing -- they are")
        print("  matched case-sensitively, so both spellings need a line")
    print("\nNext: python tools/report.py --bases   (and --families)")
    print("      then edit overrides.yml and run gen_aceax.py --check")
    return 0


def _key(token: str) -> str:
    """YAML-safe mapping key. Quote anything that is not a bare word."""
    return token if re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", token) else f'"{token}"'


def _value_name(token: str) -> str:
    """A config-class-safe value name derived from a token."""
    name = re.sub(r"[^A-Za-z0-9]+", "_", token).strip("_").upper() or "VAL"
    return f"V{name}" if name[0].isdigit() else name


if __name__ == "__main__":
    raise SystemExit(main())
