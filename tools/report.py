"""Print what the dump contains, grouped the way gen_aceax.py will group it.

Read-only analysis aid used while writing overrides.yml, and for auditing coverage
once it is written. Writes nothing.

Usage:
    python tools/report.py                 # per-pack summary, broken down by arsenal tab
    python tools/report.py <pack> [<pack>] # detail for named packs
    python tools/report.py --p3d <pack>    # group by p3d instead of listing flat
    python tools/report.py --bases         # group by displayName base
    python tools/report.py --coverage      # every item and the entry it sits behind
    python tools/report.py --coverage --csv  # just the class names, for diffing
    python tools/report.py --families      # propose bases: groupings -> _dump/families.yml
    python tools/report.py --families --write   # ... or straight into overrides.yml
    python tools/report.py --bases --out notes.txt   # any mode can go to a file

Only --families writes a file by default; on a large mod its output is hundreds of
lines, which is unreadable in a console and awkward to copy from.
"""

from __future__ import annotations

import argparse
import collections
import contextlib
import os
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gen_aceax  # noqa: E402
import modinfo  # noqa: E402
from modconfig import Config, Item, parse_display_name  # noqa: E402

# scope comes back as an int from a derapified config, but a hand-edited dump can
# carry it as a string. Cheap to be tolerant, and a miscounted scope would make
# --unclassified quietly wrong.
def _scope_of(config: Config, root: str, name: str) -> int:
    try:
        return int(config.resolve(root, name, "scope"))
    except (TypeError, ValueError):
        return 0


def p3d_name(w: Item) -> str:
    return w.model.rsplit("\\", 1)[-1] or "<none>"


def tex_tail(t: str) -> str:
    return t.rsplit("\\", 1)[-1]


def summary(items: list[Item], unnamed: list[Item]) -> None:
    """Per-pack counts, broken down by arsenal tab.

    The tab breakdown is what tells you whether `kinds:` in mod.yml is picking up
    what you expect -- a gear mod that reports nothing but headgear usually means
    a pack is missing, not that it ships no vests.
    """
    by_pack: dict[str, list[Item]] = collections.defaultdict(list)
    for w in items:
        by_pack[w.pack].append(w)
    print(f"{'pack':<20}{'items':>7}{'p3ds':>7}  kinds")
    for pack in sorted(by_pack):
        group = by_pack[pack]
        kinds = collections.Counter(w.kind for w in group)
        breakdown = ", ".join(f"{k} {n}" for k, n in sorted(kinds.items()))
        print(f"{pack:<20}{len(group):>7}{len({p3d_name(w) for w in group}):>7}  {breakdown}")
    total_kinds = collections.Counter(w.kind for w in items)
    print(
        f"{'TOTAL':<20}{len(items):>7}{len({p3d_name(w) for w in items}):>7}  "
        + ", ".join(f"{k} {n}" for k, n in sorted(total_kinds.items()))
    )
    if unnamed:
        print(
            f"\n{len(unnamed)} arsenal-visible item(s) skipped -- no display name to group on "
            "(usually vanilla classes the mod only patches)"
        )


def detail(items: list[Item], packs: list[str], by_p3d: bool) -> None:
    for pack in packs:
        group = [w for w in items if w.pack == pack]
        if not group:
            print(f"===== {pack}: nothing =====")
            continue
        print(f"===== {pack} ({len(group)} items) =====")
        if not by_p3d:
            for w in group:
                print(f"  {w.kind:<10} {w.name:<34} {w.display_name:<38} {p3d_name(w)}")
            print()
            continue

        buckets: dict[str, list[Weapon]] = collections.defaultdict(list)
        for w in group:
            buckets[p3d_name(w)].append(w)
        for p3d in sorted(buckets):
            members = buckets[p3d]
            print(f"  --- {p3d}  ({len(members)})")
            # which hiddenSelection slots actually differ inside this p3d bucket
            varying = set()
            for idx in range(max((len(w.textures) for w in members), default=0)):
                if len({w.textures[idx] if idx < len(w.textures) else "" for w in members}) > 1:
                    varying.add(idx)
            for w in members:
                diff = " | ".join(
                    f"{(w.selections[i] if i < len(w.selections) else i)}="
                    f"{tex_tail(w.textures[i]) if i < len(w.textures) else ''}"
                    for i in sorted(varying)
                )
                print(f"      {w.name:<34} {w.display_name:<38} {diff}")
        print()


def bases(items: list[Item], packs: list[str]) -> None:
    """Group by the displayName base, which is how gen_aceax.py forms models."""
    groups: dict[tuple[str, str, str], list[tuple[Item, tuple[str, ...]]]] = (
        collections.defaultdict(list)
    )
    for w in items:
        if packs and w.pack not in packs:
            continue
        base, tokens = parse_display_name(w.display_name)
        groups[(w.kind, w.pack, base)].append((w, tokens))

    singles = 0
    dupes: list[str] = []
    for kind, pack, base in sorted(groups):
        members = groups[(kind, pack, base)]
        if len(members) == 1:
            singles += 1
            continue
        print(f"  [{kind}/{pack}] {base}   ({len(members)})")
        seen: dict[tuple[str, ...], str] = {}
        for w, tokens in sorted(members, key=lambda m: m[1]):
            clash = ""
            if tokens in seen:
                clash = f"   <== SAME TOKENS as {seen[tokens]}"
                dupes.append(f"{base}: {seen[tokens]} / {w.name} -> {tokens or '()'}")
            seen.setdefault(tokens, w.name)
            print(f"        {w.name:<34} {'+'.join(tokens) or '-':<28}{clash}")
    print(f"\n  {len(groups)} groups, {singles} of them single-weapon")
    if dupes:
        print(f"\n  {len(dupes)} token collision(s) needing an override:")
        for d in dupes:
            print(f"    {d}")


FAMILIES_HEADER = """\
# Candidate `bases:` groupings, proposed by `python tools/report.py --families`.
#
# Paste the blocks you agree with into `bases:` in tools/overrides.yml, then add the
# axes -- the "differs by" comment on each line tells you what actually varies.
#
# As written, a pasted block merges its bases into one arsenal entry with no
# distinguishing option. gen_aceax.py reports that as "no distinguishing option"
# and skips the group: that is the prompt to add axes, not an error.
#
# Suggestions are per-pack and err towards over-merging -- deleting a line you
# disagree with is quicker than noticing a family that was missed.

bases:
"""


def families(config: Config, packs: list[str], out: Path, inject: bool) -> int:
    """Propose `bases:` groupings by clustering base names on a shared stem.

    Purely a suggestion. Clustering is per-pack, which is what stops "SIG SG550"
    being pulled in with "SIG Stgw.57". Bases already handled in overrides.yml are
    skipped, which is also what makes re-running --write safe.

    Writes a paste-ready YAML file rather than printing the lot: on a big mod this
    is hundreds of lines, which is unreadable in a console and awkward to copy from.
    """
    ov = yaml.safe_load(gen_aceax.OVERRIDES.read_text(encoding="utf-8"))
    already = set(ov.get("bases") or {})

    # clustering is per (kind, pack): a helmet and a vest can never share an entry,
    # so proposing a family that spans them only wastes a review
    by_pack: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for w in config.arsenal_items():
        if packs and w.pack not in packs:
            continue
        base = parse_display_name(w.display_name)[0]
        if base not in already:
            by_pack[(w.kind, w.pack)].add(base)

    blocks: list[str] = []
    summary_lines: list[str] = []
    for kind, pack in sorted(by_pack):
        for cluster in _cluster(sorted(by_pack[(kind, pack)])):
            if len(cluster) < 2:
                continue
            stem = _stem(cluster)
            summary_lines.append(f'  [{kind}/{pack}]{len(cluster):>5} bases  "{stem}"')
            lines = [f'  # ---- [{kind}/{pack}] {len(cluster)} bases sharing {_q(stem)} ----']
            width = max(len(_q(b)) for b in cluster) + 2
            for base in cluster:
                tail = base[len(stem):].strip() or "(exact stem)"
                entry = f"{_q(base)}:"
                lines.append(f'  {entry:<{width}} {{as: {_q(stem)}}}   # differs by: {tail}')
            blocks.append("\n".join(lines))

    if not blocks:
        print("  no further groupings suggested")
        return 0

    for line in summary_lines[:8]:
        print(line)
    if len(summary_lines) > 8:
        print(f"  ... {len(summary_lines) - 8} more")
    print()

    body = "\n\n".join(blocks) + "\n"
    if inject:
        return _inject_bases(gen_aceax.OVERRIDES, body, len(blocks))

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(FAMILIES_HEADER + body, encoding="utf-8", newline="\n")
    print(f"  {len(blocks)} candidate family/families -> {out}")
    print("  paste what you want into bases:, or re-run with --write to insert them")
    return 0


def _q(text: str) -> str:
    """Quote a base name for YAML.

    Weapon names carry double quotes often enough to matter -- 'Lithgow SLR "Chopmod"',
    'M249 "Squantoon Special"' -- and wrapping those in double quotes produces a file
    that will not parse. Prefer single quotes when the name contains a double quote,
    which is what the hand-written overrides.yml files already do.
    """
    if '"' in text and "'" not in text:
        return "'" + text + "'"
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _inject_bases(overrides: Path, body: str, count: int) -> int:
    """Append proposals to the `bases:` block by text edit, keeping comments.

    A YAML round-trip would reformat the file and drop every hand-written comment,
    which is most of overrides.yml's value -- the same reason --refresh-camo works
    this way.
    """
    text = overrides.read_text(encoding="utf-8")

    empty = re.search(r"^bases:[ \t]*\{\s*\}[ \t]*$", text, re.M)
    if empty:
        updated = text[: empty.start()] + "bases:\n" + body + text[empty.end():].lstrip("\n")
    else:
        start = re.search(r"^bases:[ \t]*$", text, re.M)
        if not start:
            raise SystemExit(
                "no `bases:` key in overrides.yml -- add one (even `bases: {}`) first"
            )
        # the block runs until the next top-level key
        following = re.search(r"^[A-Za-z_][\w]*:", text[start.end():], re.M)
        cut = start.end() + (following.start() if following else len(text) - start.end())
        head, tail = text[:cut].rstrip("\n"), text[cut:]
        updated = head + "\n\n" + body + "\n" + tail

    overrides.write_text(updated, encoding="utf-8", newline="\n")
    print(f"  inserted {count} candidate family/families into {overrides}")
    print("  now add the axes -- each line's comment says what varies")
    return 0


def _stem(cluster: list[str]) -> str:
    """Shared prefix, backed off so it does not cut inside an identifier.

    The raw common prefix of G36A1/G36A2/G36A3 is "G36A", which would suggest an
    entry called "G36A" with values "1", "2", "3". Backing off while any tail starts
    with a digit gives "G36" and values "A1", "A2", "A3", which is what you want.
    """
    stem = os.path.commonprefix(cluster).rstrip()
    while stem and any(name[len(stem):][:1].isdigit() for name in cluster):
        stem = stem[:-1]
    return stem.rstrip()


def _cluster(names: list[str]) -> list[list[str]]:
    """Group sorted names by shared leading characters.

    Starts a new group when a name's common prefix with the previous one falls below
    60% of the shorter name, or under 3 characters.
    """
    groups: list[list[str]] = []
    for name in names:
        if groups:
            previous = groups[-1][-1]
            shared = len(os.path.commonprefix([previous, name]))
            if shared >= 3 and shared >= 0.6 * min(len(previous), len(name)):
                groups[-1].append(name)
                continue
        groups.append([name])
    return groups


def _unclassified(config: Config) -> dict[tuple[str, str], list[str]]:
    """Classes that look like arsenal items but resolve to no kind.

    `scope = 2` and a display name of their own, yet `detect_kind` returns "" --
    so they are silently not arsenal items. No error, nothing in --coverage,
    nothing in verify.py. That is the whole point of looking: VSM shipped with 156
    items invisible this way and it took a bug report about one helmet to notice.

    Keyed on (config root, the class the ancestry ends at), because that terminal
    is what names the cause -- see the table in `unclassified` below.
    """
    found: dict[tuple[str, str], list[str]] = {}
    for root, classes in config.classes.items():
        for name in classes:
            if not config.resolve(root, name, "displayName"):
                continue
            if _scope_of(config, root, name) != 2:
                continue
            if config.detect_kind(root, name):
                continue
            chain = config.chain(root, name)
            terminal = chain[-1] if chain else config.root_parent(root, name)
            found.setdefault((root, terminal), []).append(name)
    return found


def unclassified(config: Config) -> int:
    """Report those classes, grouped by what the chain ends at.

    Deliberately NOT a pass/fail gate. Measured across the existing compats the
    count runs 0, 0, 0, 4 and 81 -- and the 81 are Tier One's rifles inheriting
    from RHS, which an attachments-only compat has no reason to dump. Correct
    there, a real warning for anyone covering that mod's weapons. A human reads it.
    """
    found = _unclassified(config)

    # Only backpacks are arsenal items under CfgVehicles, so soldier units and
    # vehicles landing here is right. Counted, not listed -- crying wolf about 330
    # correctly-excluded units would make the whole report ignorable.
    #
    # Except when the terminal looks like a bag. That is the one CfgVehicles case
    # that IS a miss, and quieting it wholesale would have hidden VSM's 44 invisible
    # backpacks in with its 330 units -- checked by re-running this with the
    # VANILLA_* tables emptied.
    def looks_like_a_bag(terminal: str) -> bool:
        return any(w in terminal for w in ("bag", "pack", "carryall", "bergen", "harness"))

    gear = {
        k: v for k, v in found.items()
        if k[0] != "CfgVehicles" or looks_like_a_bag(k[1])
    }
    units = sum(
        len(v) for k, v in found.items()
        if k[0] == "CfgVehicles" and not looks_like_a_bag(k[1])
    )

    total = sum(len(v) for v in gear.values())
    if not total:
        print("No unclassified arsenal-looking classes.")
    else:
        print(
            f"{total} class(es) have scope 2 and a display name but resolve to no "
            f"arsenal kind,\nso they are silently absent from the arsenal:\n"
        )
        for (root, terminal), names in sorted(gear.items(), key=lambda kv: -len(kv[1])):
            print(f"  {len(names):>4}  [{root}] inheritance ends at '{terminal}'")
            for n in sorted(names)[:3]:
                print(f"          {n}")
            if len(names) > 3:
                print(f"          ... and {len(names) - 3} more")
        print(
            "\nWhat the terminal tells you:\n"
            "  a vanilla gear or bag base   the dump holds a body-less forward declaration;\n"
            "                               modconfig's VANILLA_* tables should cover it -- if not,\n"
            "                               add the base there\n"
            "  another mod's class          the chain leaves the dump. Add that mod as a\n"
            "                               resolve-only source: init_mod.py --requires <id>\n"
            "  a class in your own dump     the mod is doing something unusual; look by hand"
        )
    if units:
        print(
            f"\n({units} CfgVehicles class(es) also resolve to no kind. Expected: only "
            "backpacks\n are arsenal items there, so soldier units and vehicles belong in "
            "this bucket.)"
        )
    return 0


def coverage(config: Config, packs: list[str], as_csv: bool) -> int:
    """Show where every arsenal item ended up: behind which entry, or standalone.

    Reads the current overrides.yml through gen_aceax.collect, so it always matches
    what the generator would write. The TOTAL line is a reconciliation -- every
    arsenal-visible item must appear exactly once.
    """
    items = config.arsenal_items()
    ov = yaml.safe_load(gen_aceax.OVERRIDES.read_text(encoding="utf-8"))
    models, _, _ = gen_aceax.collect(config, ov)

    if as_csv:
        # bare class names, for diffing against what the running game reports via
        # aceax_gearinfo_fnc_diag_fullReportExport
        for w in sorted(items, key=lambda x: x.name.lower()):
            if not packs or w.pack in packs:
                print(w.name)
        return 0

    # an item is attributed to its MODEL's pack, not its source pack: an entry
    # merged across sources lives in one pack, and the totals have to balance
    covered: dict[str, str] = {}  # item name -> model name
    pack_of: dict[str, str] = {}  # item name -> the pack it is counted under
    for m in models:
        for member in m.members:
            covered[member.item.name] = m.name
            pack_of[member.item.name] = m.pack

    models_by_pack: dict[str, list] = collections.defaultdict(list)
    for m in models:
        models_by_pack[m.pack].append(m)

    def counted_pack(w: Item) -> str:
        return pack_of.get(w.name, w.pack)

    total_covered = total_standalone = 0
    for pack in sorted({counted_pack(w) for w in items}):
        if packs and pack not in packs:
            continue
        in_pack = [w for w in items if counted_pack(w) == pack]
        entries = models_by_pack.get(pack, [])
        standalone = [w for w in in_pack if w.name not in covered]
        total_covered += len(in_pack) - len(standalone)
        total_standalone += len(standalone)

        print(
            f"=== {pack}   {len(in_pack)} item{'' if len(in_pack) == 1 else 's'} -> "
            f"{len(entries)} entr{'y' if len(entries) == 1 else 'ies'}, "
            f"{len(standalone)} standalone ==="
        )
        for m in entries:
            print(f"  {m.label}  [{m.name}]  {m.config_root}")
            for member in m.members:
                opts = "  ".join(f"{a}={member.values[a]}" for a in m.axes)
                print(f"      {member.item.name:<40} {opts}")
        if standalone:
            print("  (standalone)")
            for w in standalone:
                print(f"      {w.name:<40} {w.display_name}")
        print()

    shown = [w for w in items if not packs or counted_pack(w) in packs]
    print(
        f"TOTAL  {len(shown)} items = {total_covered} behind "
        f"{sum(len(models_by_pack.get(p, [])) for p in {counted_pack(w) for w in shown})} entries "
        f"+ {total_standalone} standalone"
    )

    # The reconciliation above only balances items the classifier FOUND. Anything it
    # failed to classify never reaches arsenal_items() at all, so it cannot show up
    # as missing -- it is simply absent, silently. Nudge toward the one report that
    # looks for that, since --coverage is the step people actually run.
    blind = sum(
        len(v) for k, v in _unclassified(config).items() if k[0] != "CfgVehicles"
    )
    if blind:
        print(
            f"\nNote: {blind} class(es) look like arsenal items but resolve to no kind, "
            "so they\nare not counted above at all. Run `report.py --unclassified`."
        )

    # an item in neither bucket would mean collect() lost it
    missing = len(shown) - total_covered - total_standalone
    if missing:
        print(f"\nMISSING: {missing} item(s) in neither an entry nor the standalone list")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packs", nargs="*", help="packs to detail; omit for a summary")
    parser.add_argument("--p3d", action="store_true", help="group detail by p3d model")
    parser.add_argument("--bases", action="store_true", help="group by displayName base")
    parser.add_argument(
        "--coverage", action="store_true", help="every weapon and the entry it sits behind"
    )
    parser.add_argument("--csv", action="store_true", help="with --coverage: class names only")
    parser.add_argument(
        "--unclassified",
        action="store_true",
        help="classes that look like arsenal items but resolve to no kind",
    )
    parser.add_argument(
        "--families", action="store_true", help="propose bases: groupings"
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="with --families: insert the proposals into overrides.yml",
    )
    parser.add_argument(
        "--out", type=Path, help="write the detailed output to this file instead of stdout"
    )
    args = parser.parse_args()

    config = Config.load()
    if args.families:
        return families(
            config, args.packs, args.out or (modinfo.DUMP / "families.yml"), args.write
        )

    # every other mode just prints; sending that to a file is a redirect
    with contextlib.ExitStack() as stack:
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            handle = stack.enter_context(args.out.open("w", encoding="utf-8", newline="\n"))
            stack.enter_context(contextlib.redirect_stdout(handle))

        if args.unclassified:
            result = unclassified(config)
        elif args.coverage:
            result = coverage(config, args.packs, args.csv)
        else:
            items = config.arsenal_items()
            if args.bases:
                bases(items, args.packs)
            elif args.packs:
                detail(items, args.packs, args.p3d)
            else:
                summary(items, config.unnamed_items())
            result = 0

    if args.out:
        print(f"wrote {args.out}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
