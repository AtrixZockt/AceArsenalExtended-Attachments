"""Load the derapified source-mod configs from _dump/ and expose the arsenal-visible items.

Mod-agnostic: the only thing it knows about the target mod comes from tools/mod.yml
via modinfo. Shared by gen_aceax.py, report.py and verify.py. Nothing here writes files.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import modinfo  # noqa: E402

REPO = modinfo.REPO
DUMP = modinfo.DUMP

# hemtt's derapify output nests classes as dicts and records inheritance as "__parent".
# Each class holds only its OWN properties, so anything inherited has to be walked.
PARENT = "__parent"


# ---------------------------------------------------------------------------
# what the arsenal holds
# ---------------------------------------------------------------------------
#
# ACEAX drives ten arsenal tabs from three config roots -- see its
# addons/arsenal/XEH_preInit.sqf. The tab is what matters for grouping (a model is
# collapsed within one panel), the root is what matters for emitting (XtdGearModels
# and XtdGearInfos are keyed by it), and the two do not line up: headgear, uniforms
# and vests all live in CfgWeapons but sit on three different tabs.
#
# `kind` below is the tab. modinfo.KINDS names the same set for mod.yml.

KIND_ROOT = {
    "primary": "CfgWeapons",
    "handgun": "CfgWeapons",
    "launcher": "CfgWeapons",
    "headgear": "CfgWeapons",
    "uniform": "CfgWeapons",
    "vest": "CfgWeapons",
    "nvg": "CfgWeapons",
    "binocular": "CfgWeapons",
    "backpack": "CfgVehicles",
    "goggles": "CfgGlasses",
    # Attachments are right-panel items. Stock ACEAX ignores them entirely; the
    # aceaxatt extension is what makes this data do anything in game. Emitting it
    # without the extension is harmless -- nothing reads it.
    "optic": "CfgWeapons",
    "pointer": "CfgWeapons",
    "muzzle": "CfgWeapons",
    "bipod": "CfgWeapons",
}

CONFIG_ROOTS = ("CfgWeapons", "CfgVehicles", "CfgGlasses")

# Every CfgWeapons class bottoms out at one of the vanilla A3 base classes.
# "rifle"/"pistol" are the actual weapons; "itemcore" and the "optic_*" family are
# either attachments (optics, suppressors, swap barrels, grips) or gear, and gear is
# told apart by ItemInfo instead -- see below.
WEAPON_ROOTS = {
    "rifle": "primary",
    "pistol": "handgun",
    "launcher": "launcher",
    "binocular": "binocular",
    "nvgoggles": "nvg",
}

# Wearable CfgWeapons items are recognised by what their ItemInfo inherits from.
#
# Not by `ItemInfo >> type`, which is how the game itself does it: `type` is declared
# on the vanilla HeadgearItem/VestItem/UniformItem classes, which are never in the
# dump, so offline every gear item reports no type at all. The ItemInfo parent is
# right there in the mod's own config and is universal Arma convention.
ITEMINFO_KINDS = {
    "headgearitem": "headgear",
    "vestitem": "vest",
    "uniformitem": "uniform",
    "nvgoggles": "nvg",
    "nvgogglesitem": "nvg",
    "binocularitem": "binocular",
    # attachments
    "inventoryopticsitem_base_f": "optic",
    "inventoryflashlightitem_base_f": "pointer",
    "inventorymuzzleitem_base_f": "muzzle",
    "inventoryunderitem_base_f": "bipod",
}

# Last resort for an attachment that inherits straight from a VANILLA attachment
# (`hlc_optic_kobra : optic_aco_grn`). Its nearest ItemInfo then lives on a class
# that is never in the dump, so there is nothing to read the kind off. The vanilla
# class-name prefixes are a reliable convention, and this only ever runs on classes
# that already failed every other test.
VANILLA_ATTACHMENT_PREFIXES = {
    "optic_": "optic",
    "acc_": "pointer",
    "muzzle_": "muzzle",
    "bipod_": "bipod",
}


@dataclass
class Item:
    """One arsenal-visible thing: a weapon, a helmet, a vest, a backpack, goggles."""

    name: str
    pack: str
    config_root: str
    props: dict

    # resolved through the inheritance chain
    kind: str = ""
    scope: int = 0
    scope_arsenal: int | None = None
    display_name: str = ""
    model: str = ""
    picture: str = ""
    textures: tuple[str, ...] = ()
    selections: tuple[str, ...] = ()
    base_weapon: str = ""
    has_linked_items: bool = False
    parents: tuple[str, ...] = field(default_factory=tuple)
    root: str = ""
    type: int | None = None

    @property
    def is_arsenal_visible(self) -> bool:
        """Mirror of aceax's CLASS_FILTER + fnc_filterConfigEntries.

        CLASS_FILTER: scope == 2 and scopeArsenal (if present) == 2. It applies to
        every root.

        On top of that, and ONLY for CfgWeapons, fnc_filterConfigEntries runs
        fnc_isValidCfgWeapon: a weapon carrying LinkedItems is a pre-attached-optic
        duplicate unless it declares itself as its own baseWeapon. CfgVehicles and
        CfgGlasses get no such check.
        """
        if self.scope != 2:
            return False
        if self.scope_arsenal is not None and self.scope_arsenal != 2:
            return False
        if self.config_root == "CfgWeapons" and self.has_linked_items:
            return bool(self.base_weapon) and self.base_weapon.lower() == self.name.lower()
        return True


class Config:
    """Merged CfgWeapons/CfgVehicles/CfgGlasses across every dumped pack.

    Class names, property names and config root names are all matched
    case-insensitively. Arma does not care about any of them, and mods take
    advantage: Military Gear Pack writes `class cfgWeapons` and `displayname`, and
    is not even consistent with itself (`CfgVehicles` in one pbo, `cfgVehicles` in
    the next). Reading it case-sensitively finds nothing at all.
    """

    def __init__(self) -> None:
        # root -> lower name -> props (property keys lower-cased, recursively)
        self.classes: dict[str, dict[str, dict]] = {r: {} for r in CONFIG_ROOTS}
        self.origin: dict[str, dict[str, str]] = {r: {} for r in CONFIG_ROOTS}
        self.real_name: dict[str, dict[str, str]] = {r: {} for r in CONFIG_ROOTS}
        self.strings: dict[str, str] = {}  # lower $STR key -> english text
        self.base_packs: set[str] = set()  # packs that only contribute base classes
        self.kinds: tuple[str, ...] = ()  # arsenal tabs this compat covers
        self.roots: tuple[str, ...] = CONFIG_ROOTS  # roots actually read

    # ---------- loading ----------

    @classmethod
    def load(
        cls,
        dump: Path = DUMP,
        base_packs: tuple[str, ...] | None = None,
        kinds: tuple[str, ...] | None = None,
    ) -> "Config":
        self = cls()
        if base_packs is None or kinds is None:
            mod = modinfo.load()
            if base_packs is None:
                base_packs = mod.base_packs
            if kinds is None:
                kinds = mod.kinds
        self.base_packs = set(base_packs)
        self.kinds = tuple(kinds)
        self.roots = tuple(dict.fromkeys(KIND_ROOT[k] for k in self.kinds))

        # base packs first, so weapon packs win on any duplicate base class
        paths = sorted(dump.glob("*.json"), key=lambda p: (p.stem not in self.base_packs, p.stem))
        for path in paths:
            pack = path.stem
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            for key, value in data.items():
                root = _canonical_root(key)
                if root is None or root not in self.roots or not isinstance(value, dict):
                    continue
                self._load_root(root, pack, value)
            self._load_strings(dump / f"{pack}.stringtable.xml")
        return self

    def _load_root(self, root: str, pack: str, entries: dict) -> None:
        classes, origin, real = self.classes[root], self.origin[root], self.real_name[root]
        for name, props in entries.items():
            if not isinstance(props, dict):
                continue
            key = name.lower()
            props = _lower_keys(props)
            if key in classes:
                classes[key] = {**classes[key], **props}
            else:
                classes[key] = props
                real[key] = name
                origin[key] = pack

    def _load_strings(self, path: Path) -> None:
        if not path.is_file():
            return
        text = path.read_text(encoding="utf-8", errors="replace")
        # Mod stringtables are hand-edited and not always well-formed
        # (stray & and unescaped quotes), so parse them with a regex instead of ElementTree.
        for match in re.finditer(
            r'<Key\s+ID="([^"]+)"(.*?)</Key>', text, re.DOTALL | re.IGNORECASE
        ):
            key, body = match.group(1), match.group(2)
            value = re.search(
                r"<(?:English|Original)>(.*?)</(?:English|Original)>", body, re.DOTALL | re.IGNORECASE
            )
            if value:
                self.strings.setdefault(key.lower(), _unescape(value.group(1)).strip())

    # ---------- inheritance ----------

    def chain(self, root: str, name: str) -> list[str]:
        """Class name plus its ancestors, nearest first. Cycle-safe.

        Inheritance never crosses a config root, which is also how Arma resolves it.
        """
        classes = self.classes[root]
        out: list[str] = []
        seen: set[str] = set()
        key = name.lower()
        while key and key in classes and key not in seen:
            seen.add(key)
            out.append(key)
            parent = classes[key].get(PARENT)
            key = parent.lower() if isinstance(parent, str) else ""
        return out

    def resolve(self, root: str, name: str, prop: str, default=None):
        prop = prop.lower()
        classes = self.classes[root]
        for key in self.chain(root, name):
            props = classes[key]
            if prop in props:
                return props[prop]
        return default

    def text(self, value) -> str:
        """Resolve a $STR_ reference to English, else return the literal."""
        if not isinstance(value, str):
            return ""
        if value.startswith("$"):
            return self.strings.get(value[1:].lower(), value)
        return value

    # ---------- items ----------

    def root_parent(self, root: str, name: str) -> str:
        """The first ancestor that is not itself defined in the dump.

        That is always a vanilla A3 class, and it is what separates weapons
        ("rifle"/"pistol") from everything else ("itemcore"/"optic_*").
        """
        chain = self.chain(root, name)
        if not chain:
            return ""
        parent = self.classes[root][chain[-1]].get(PARENT)
        return parent.lower() if isinstance(parent, str) else ""

    def detect_kind(self, root: str, name: str) -> str:
        """Which arsenal tab this class would appear on, or "" for none.

        Order matters: the config root settles goggles and backpacks outright, then
        a wearable is recognised by its ItemInfo parent, and only what is left is
        tested against the weapon roots.
        """
        if root == "CfgGlasses":
            return "goggles"
        if root == "CfgVehicles":
            # `isBackpack` is the canonical flag, and the only thing separating a
            # wearable bag from an ammo crate -- both descend from ReammoBox.
            return "backpack" if _as_int(self.resolve(root, name, "isBackpack")) == 1 else ""

        kind = self._iteminfo_kind(root, name)
        if kind:
            return kind

        kind = WEAPON_ROOTS.get(self.root_parent(root, name))
        if kind is None:
            return self._vanilla_attachment_kind(root, name)
        # a weapon may override which tab it lands on: NIArms' MP5K is rifle-rooted
        # but declares type 2, so it sits with the pistols
        item_type = _as_int(self.resolve(root, name, "type"), None)
        if item_type == 2:
            return "handgun"
        if item_type == 4096:
            return "binocular"
        return kind

    def _iteminfo_kind(self, root: str, name: str) -> str:
        """Kind from the class its ItemInfo inherits, walking the class chain.

        `resolve()` alone is not enough. Mods routinely write

            class hlc_optic_x : hlc_optic_base { class ItemInfo : ItemInfo {}; };

        where `ItemInfo : ItemInfo` means "inherit my class-parent's ItemInfo".
        The nearest declaration then names no real base and the chain has to be
        followed. Skipping this misclassifies 11 of NIArms' 29 attachments.

        Stops at the first ItemInfo naming a base that is not `ItemInfo`, so an
        unrecognised base means "not one of ours" rather than "keep looking".
        """
        classes = self.classes[root]
        for key in self.chain(root, name):
            info = classes[key].get("iteminfo")
            if not isinstance(info, dict):
                continue
            parent = info.get(PARENT)
            if not isinstance(parent, str):
                continue
            kind = ITEMINFO_KINDS.get(parent.lower())
            if kind:
                return kind
            if parent.lower() != "iteminfo":
                return ""
        return ""

    def _vanilla_attachment_kind(self, root: str, name: str) -> str:
        rooted = self.root_parent(root, name)
        for prefix, kind in VANILLA_ATTACHMENT_PREFIXES.items():
            if rooted.startswith(prefix):
                return kind
        return ""

    def items(self) -> list[Item]:
        out: list[Item] = []
        for root in self.roots:
            for key, props in self.classes[root].items():
                pack = self.origin[root].get(key, "")
                if not pack or pack in self.base_packs:
                    # base packs define only shared base classes; nothing arsenal-visible
                    continue
                scope_arsenal = self.resolve(root, key, "scopeArsenal")
                slots = self.resolve(root, key, "WeaponSlotsInfo")
                linked = self.resolve(root, key, "LinkedItems")
                out.append(
                    Item(
                        name=self.real_name[root][key],
                        pack=pack,
                        config_root=root,
                        props=props,
                        kind=self.detect_kind(root, key),
                        scope=_as_int(self.resolve(root, key, "scope", 0)),
                        scope_arsenal=None if scope_arsenal is None else _as_int(scope_arsenal),
                        display_name=self.text(self.resolve(root, key, "displayName", "")),
                        model=_norm_path(self.resolve(root, key, "model", "")),
                        picture=_norm_path(self.resolve(root, key, "picture", "")),
                        textures=tuple(
                            _norm_path(t)
                            for t in (self.resolve(root, key, "hiddenSelectionsTextures") or [])
                        ),
                        selections=tuple(
                            str(s).lower()
                            for s in (self.resolve(root, key, "hiddenSelections") or [])
                        ),
                        base_weapon=str(self.resolve(root, key, "baseWeapon", "") or ""),
                        has_linked_items=bool(
                            isinstance(slots, dict) and isinstance(linked, dict) and linked
                        ),
                        parents=tuple(self.chain(root, key)[1:]),
                        root=self.root_parent(root, key),
                        type=_as_int(self.resolve(root, key, "type"), None),
                    )
                )
        out.sort(key=lambda i: (i.pack, i.name.lower()))
        return out

    def arsenal_items(self) -> list[Item]:
        wanted = set(self.kinds)
        return [i for i in self.items() if i.kind in wanted and i.is_arsenal_visible]


# ---------- displayName convention ----------
#
# Mods overwhelmingly name their variants "<Base> (<tok>[\<tok>...])":
#   BWmod   "G36A1 (Tan)", "G27 AG40-2 (Tan)"
#   NIArms  "Steyr AUGA1 (Tan)", "Steyr AUGA3 (GL\Green)"
#   MilGP   "Airframe 01 + Goggles (KHK)", "G3 Field Set (GREY+3CD)"
# so the base name gives the arsenal entry and each token becomes an option value.
#
# Grouping by p3d or hiddenSelectionsTextures instead does NOT work: most weapon
# variants are separate p3ds, a single p3d is sometimes shared by genuinely different
# weapons, and gear goes the other way -- Military Gear Pack drives all 42 of its
# facewear items from one p3d. The display name is the reliable signal.

# The space before the opening bracket is required: it separates a variant marker
# ("G36A1 (Tan)") from a bracket that is part of the item's own name ("G36C-MLI(C)").
#
# Brackets are matched loosely because mods ship malformed names that would otherwise
# orphan their items out of the group they belong to -- NIArms alone has three:
#   "Remington ACR-E (Compact/Green"        (no closing bracket)
#   "M1903A1 {Sniper)"                      (mismatched brackets)
_PAREN = re.compile(r"^(.*?\S)\s+[({]([^(){}]*)[)}]?$")

# "+" is in here for gear: Military Gear Pack writes a uniform's top and trouser
# camo as one marker, "(GREY+3CD)". See `positional_axes` in overrides.yml for how
# the two halves are told apart. No NIArms or BWmod marker contains a "+".
_TOKEN_SEP = re.compile("[" + re.escape("\\/,+") + "]")


def parse_display_name(display_name: str) -> tuple[str, tuple[str, ...]]:
    """Split "G27 AG40-2 (Tan)" into ("G27 AG40-2", ("Tan",))."""
    match = _PAREN.match(display_name.strip())
    if not match:
        return display_name.strip(), ()
    base = match.group(1).strip()
    tokens = tuple(t.strip() for t in _TOKEN_SEP.split(match.group(2)) if t.strip())
    return base, tokens


# ---------- arsenal reachability ----------
#
# A model is only useful if every item behind it can actually be picked. ACEAX
# resolves a dropdown click in fnc_changeCurrentConfig: take the current item's
# option tuple, replace one entry, then
#
#   fnc_findConfig        exact hit on that tuple -> that item, guaranteed;
#   fnc_findConfigByValue no exact hit -> the FIRST variation holding that one value.
#
# The fallback iterates a HashMap, and Arma does not guarantee HashMap iteration
# order, so which item it returns cannot be known offline. That rules out simply
# walking the graph with an assumed order -- the answer would depend on a guess.
#
# What CAN be established offline is a sound lower bound: the moves that work no
# matter what the fallback returns.
#
#   exact move   the candidate tuple exists, so findConfig hits and the fallback
#                never runs. Undirected: the reverse move is exact too.
#   anchor       an item that is the sole holder of value V on axis i. Clicking V
#                lands on it whether findConfig hits or the fallback picks -- there
#                is nothing else it could return.
#
# From any starting item the user therefore reaches its own exact-move component
# plus every anchor and their components. So every variant is provably reachable iff
# the exact-move graph is a single component, or every component contains an anchor.
#
# Anything else is not necessarily broken -- it usually works, because the ordering
# happens to cooperate -- but it cannot be proven from the config alone, so it is
# reported as a warning rather than an error. (An "unreachable under every possible
# ordering" tier was tried and dropped: across 200k randomised models it never once
# fired, because the fallback edges make the permissive graph effectively always
# connected. A check that cannot fail is worse than no check.)


def unproven_variants(
    variations: dict[tuple[str, ...], str],
    values_per_option: list[list[str]],
) -> list[str]:
    """Variants of one model whose selectability depends on HashMap ordering.

    `variations` maps an option-value tuple to an item class name;
    `values_per_option` is the model's declared values[] per option, index-aligned
    with those tuples.

    An empty result means every variant is reachable whatever order the weak-match
    fallback resolves in.
    """
    names = set(variations.values())
    if len(names) < 2:
        return []

    holders: dict[tuple[int, str], set[str]] = {}
    for tup, name in variations.items():
        for i, value in enumerate(tup):
            holders.setdefault((i, value), set()).add(name)
    anchors = {next(iter(h)) for h in holders.values() if len(h) == 1}

    exact: dict[str, set[str]] = {n: set() for n in names}
    for tup, name in variations.items():
        for i, values in enumerate(values_per_option):
            for value in values:
                if i >= len(tup) or value == tup[i]:
                    continue
                target = variations.get(tup[:i] + (value,) + tup[i + 1:])
                if target is not None:
                    exact[name].add(target)
                    exact[target].add(name)

    components: list[set[str]] = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        component, stack = {name}, [name]
        while stack:
            for nxt in exact[stack.pop()]:
                if nxt not in component:
                    component.add(nxt)
                    stack.append(nxt)
        seen |= component
        components.append(component)

    if len(components) == 1:
        return []
    return sorted({n for c in components if not (c & anchors) for n in c})


# ---------- helpers ----------


def _canonical_root(key: str) -> str | None:
    """"cfgweapons" / "CfgWeapons" / "CFGWEAPONS" -> "CfgWeapons"."""
    lowered = key.lower()
    for root in CONFIG_ROOTS:
        if root.lower() == lowered:
            return root
    return None


def _lower_keys(props: dict) -> dict:
    """Lower-case every property name, recursively.

    Nested dicts matter as much as the top level: the gear kind is read off
    `ItemInfo >> __parent`, and a mod writing `iteminfo` would otherwise be missed.
    """
    return {
        k.lower(): (_lower_keys(v) if isinstance(v, dict) else v) for k, v in props.items()
    }


def _as_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _norm_path(value) -> str:
    if not isinstance(value, str):
        return ""
    return value.replace("/", "\\").lstrip("\\").lower()


def _unescape(text: str) -> str:
    for entity, char in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")):
        text = text.replace(entity, char)
    return text
