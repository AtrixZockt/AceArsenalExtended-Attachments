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
    # Also a right-panel kind, and also aceaxatt-only. Covers ACE's four
    # ammunition tabs; grenades and explosives are separate tabs and are
    # deliberately excluded -- see _magazine_kind.
    "magazine": "CfgMagazines",
}

CONFIG_ROOTS = ("CfgWeapons", "CfgVehicles", "CfgGlasses", "CfgMagazines")

# Roots that cannot be classified without another root loaded alongside them.
# A magazine is told from a grenade by whether CfgWeapons >> Throw reaches it, so
# a magazines-only compat still has to read CfgWeapons -- otherwise every grenade
# in the mod silently classifies as a magazine.
ROOT_DEPENDENCIES = {"CfgMagazines": ("CfgWeapons",)}

# CfgMagazines >> type values ACE accepts into the arsenal's magazine tabs, from
# ace_arsenal_fnc_scanConfig:
#
#   TYPE_MAGAZINE_HANDGUN_AND_GL     16
#   TYPE_MAGAZINE_PRIMARY_AND_THROW  256
#   TYPE_MAGAZINE_SECONDARY_AND_PUT  512
#   TYPE_MAGAZINE_MISSILE            768
#                                   1536   hardcoded in ACE's list (Titan and kin)
#
# The filter matters more here than anywhere else in this file. `scope = 2` alone
# admits 613 of vanilla's 690 magazines, nearly all of it vehicle ammunition --
# 120mm tank rounds, minigun belts, ECM pods -- carrying wildly duplicated display
# names (23 classes all called "7.62 mm Minigun Belt"). Those would inflate every
# count and trip the generator's duplicate-combination refusal. With this table
# vanilla reports 185, which is what the arsenal actually shows.
MAGAZINE_TYPES = frozenset({16, 256, 512, 768, 1536})

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


# Last resort for an attachment that inherits from a VANILLA attachment
# (`hlc_optic_kobra : optic_aco_grn`). Its nearest ItemInfo then lives on a class
# that is never in the dump, so there is nothing to read the kind off. The vanilla
# class-name prefixes are a reliable convention, and this only ever runs on classes
# that already failed every other test.
#
# These also carry `scope = 2` in vanilla, which is what makes them usable to
# resolve visibility across the dump boundary -- see `_vanilla_attachment_kind`.
VANILLA_ATTACHMENT_PREFIXES = {
    "optic_": "optic",
    "acc_": "pointer",
    "muzzle_": "muzzle",
    "bipod_": "bipod",
}

# Vanilla bag base classes, for the same reason as the prefixes above: the flag
# that identifies a backpack lives outside the dump.
#
# `isBackpack = 1` is what separates a wearable bag from an ammo crate, and a gear
# mod is free to inherit it rather than restate it. Military Gear Pack sets it on
# every bag; VSM sets it on none, and inherits from B_Carryall_Base and friends --
# vanilla classes that are never dumped, so the chain walk ends before reaching the
# flag and all 44 of its backpacks resolve to no kind at all. Silently: an item with
# no kind is simply not an arsenal item.
#
# Checked against the whole chain rather than only the terminal parent, because a
# mod may put its own base class in between.
# Vanilla wearable base classes, by the tab they belong to. Third instance of the
# same problem as the two tables around this one: what decides the kind lives on a
# vanilla class the dump cannot see.
#
# Here it is worse than "not dumped" -- the class IS in the dump, as an empty
# forward declaration. A mod writes `class H_HelmetB;` to reference the vanilla
# helmet, and the dump faithfully records a class with no body. The ancestry walk
# then stops there instead of running out, and
#
#     class VSM_base_fast_helmet : H_HelmetB { class ItemInfo : ItemInfo {...} }
#
# means "inherit my class-parent's ItemInfo" -- from the stub. So HeadgearItem is
# never reached. VSM loses 13 helmets and 99 uniforms that way, with no warning:
# an item with no kind is simply not an arsenal item.
#
# The prefixes are Arma's own convention for CfgWeapons gear; the bare names are
# the generic bases everything else descends from.
VANILLA_GEAR_PREFIXES = {"h_": "headgear", "v_": "vest", "u_": "uniform"}
VANILLA_GEAR_BASES = {
    "headgearitem": "headgear",
    "vestitem": "vest",
    "uniformitem": "uniform",
    "uniform_base": "uniform",
    "vest_base": "vest",
    "vest_camo_base": "vest",
    "vest_nochemprot_base": "vest",
}

VANILLA_BACKPACK_BASES = {
    "bag_base",
    "b_assaultpack_base",
    "b_carryall_base",
    "b_fieldpack_base",
    "b_kitbag_base",
    "b_tacticalpack_base",
    "b_bergen_base",
    "b_viperharness_base",
    "b_legstrapbag_base_f",
}

# Vanilla ammunition magazines that mods inherit from. Fourth instance of the same
# problem as the three tables above: what decides the item lives on a vanilla class
# the dump cannot see.
#
# Both facts a magazine is judged on come from there. BWmod writes
#
#     class BWA3_20Rnd_762x51_G28 : 20Rnd_762x51_Mag { displayName = ...; };
#
# and nothing else -- vanilla's parent carries `scope = 2` and CA_Magazine carries
# `type = 256`. Neither resolves offline, so all six of the G28's magazines look
# like they have no scope and no type, and drop out silently.
#
# Dumping vanilla alongside is NOT the fix here, however tempting. It resolves the
# magazines and destroys the weapons: BWmod's rifles inherit straight from
# Rifle_Base_F, so today the chain stops there and WEAPON_ROOTS matches "rifle",
# while with vanilla present it runs on to RifleCore and Default and matches
# nothing. Measured on BWmod: magazines 35 -> 41, primary 77 -> 0.
#
# Seeded with the CfgMagazines classes that descend directly from CA_Magazine with
# scope 2 and a carryable type, less the throwables (which are the grenade tab, not
# this one) and Laserbatteries (a misc item). Incomplete by nature, like the tables
# above it -- `report.py --unclassified` is how a missing entry shows itself.
VANILLA_MAGAZINE_BASES = {
    "ca_magazine",
    "10rnd_762x51_mag",
    "20rnd_762x51_mag",
    "30rnd_556x45_stanag",
    "30rnd_65x39_caseless_mag",
    "30rnd_9x21_mag",
    "100rnd_65x39_caseless_mag",
    "150rnd_762x51_box",
    "200rnd_65x39_cased_box",
    "11rnd_45acp_mag",
    "5rnd_127x108_mag",
    "7rnd_408_mag",
    "1rnd_he_grenade_shell",
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
        self._throw_put_cache: set[str] | None = None

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
        roots = [KIND_ROOT[k] for k in self.kinds]
        for root in list(roots):
            roots.extend(ROOT_DEPENDENCIES.get(root, ()))
        self.roots = tuple(dict.fromkeys(roots))

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
        if root == "CfgMagazines":
            return self._magazine_kind(root, name)
        if root == "CfgVehicles":
            # `isBackpack` is the canonical flag, and the only thing separating a
            # wearable bag from an ammo crate -- both descend from ReammoBox.
            if _as_int(self.resolve(root, name, "isBackpack")) == 1:
                return "backpack"
            # Not set anywhere in the dump. It may still be a bag that inherits the
            # flag from a vanilla base -- see VANILLA_BACKPACK_BASES.
            return "backpack" if self._inherits_vanilla_bag(root, name) else ""

        kind = self._iteminfo_kind(root, name)
        if kind:
            return kind

        # ItemInfo could not settle it. Before falling through to the weapon roots,
        # try the ancestry for a vanilla gear base -- see _vanilla_gear_kind.
        kind = self._vanilla_gear_kind(root, name)
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

    def _throw_put_magazines(self) -> set[str]:
        """Every magazine reachable from the virtual weapons Throw and Put.

        These are the arsenal's grenade and explosive tabs, which this toolchain
        does not cover: @aceaxatt collapses the four ammunition tabs only, so
        grouping data for a smoke grenade would sit inert while still inflating
        every count. Excluding them here is what keeps `magazine` meaning what
        the arsenal means by it.

        This is how ACE itself tells them apart -- ace_arsenal_fnc_scanConfig
        reads `Throw >> <muzzle> >> magazines[]` and the same for `Put`. Checked
        against vanilla it separates them exactly: 19 throwables and 13
        explosives, with no rifle magazine caught and no grenade missed.

        Every sub-class is scanned rather than only those named in `muzzles[]`.
        Arma replaces rather than merges an inherited array, so a DLC that adds a
        mine can leave `muzzles[]` naming fewer muzzles than the class actually
        has -- and a muzzle whose magazines are already listed is harmless to
        read twice.
        """
        if self._throw_put_cache is None:
            found: set[str] = set()
            weapons = self.classes.get("CfgWeapons", {})
            for holder in ("throw", "put"):
                body = weapons.get(holder)
                if not isinstance(body, dict):
                    continue
                pools = [body] + [v for v in body.values() if isinstance(v, dict)]
                for pool in pools:
                    for magazine in pool.get("magazines") or []:
                        if isinstance(magazine, str):
                            found.add(magazine.lower())
            self._throw_put_cache = found
        return self._throw_put_cache

    def _magazine_kind(self, root: str, name: str) -> str:
        """Whether a magazine is one the arsenal's ammunition tabs would list.

        Mirrors ace_arsenal_fnc_scanConfig, which is the only authority on what
        those tabs hold, and is worth mirroring exactly rather than approximating
        -- see MAGAZINE_TYPES for what `scope = 2` alone would let through.

        Order follows ACE's own switch: misc-item magazines (spare barrels,
        intel, photographs) go to the Misc tab, grenades and explosives to their
        own tabs, and only what is left is tested against the type allowlist.
        `ace_arsenal_hide = -1` is ACE's override for a magazine that should be
        listed whatever its type says.
        """
        if name in self._throw_put_magazines():
            return ""
        # ACE's isMiscItem, magazine branch: ACE_asItem > 0 or ACE_isUnique
        if _as_expr_int(self.resolve(root, name, "ACE_asItem")) > 0:
            return ""
        if _as_expr_int(self.resolve(root, name, "ACE_isUnique")) == 1:
            return ""
        if _as_expr_int(self.resolve(root, name, "ace_arsenal_hide")) == -1:
            return "magazine"
        if _as_expr_int(self.resolve(root, name, "type")) in MAGAZINE_TYPES:
            return "magazine"
        # `type` said nothing, which for a magazine usually means the chain left the
        # dump before reaching it. Only then is the ancestry consulted -- so a
        # magazine that states its own type is never second-guessed by this.
        if self.resolve(root, name, "type") is None and self._inherits_vanilla_magazine(
            root, name
        ):
            return "magazine"
        return ""

    def _inherits_vanilla_magazine(self, root: str, name: str) -> bool:
        """Whether a vanilla ammunition magazine sits anywhere in the ancestry.

        Whole chain plus the terminal's parent, like _vanilla_attachment_kind: a mod
        may put its own base class in between, and the vanilla class is usually the
        one the chain runs out on rather than one it contains.
        """
        if root != "CfgMagazines":
            return False
        for ancestor in self.chain(root, name) + [self.root_parent(root, name)]:
            if ancestor in VANILLA_MAGAZINE_BASES:
                return True
        return False

    def _vanilla_attachment_kind(self, root: str, name: str) -> str:
        """Kind from a vanilla attachment class anywhere in the ancestry.

        Scans the whole chain, not just `root_parent`. Testing only the terminal
        root fails as soon as a mod *redefines* a vanilla class, because the chain
        then stops inside the dump:

            hlc_optic_ATACR -> hlc_optic_atacr_offset -> hlc_optic_zf95base
                            -> optic_lrps          (NIArms patches it as `: ItemCore`)
            root_parent == "itemcore"

        `optic_lrps` is right there in the chain; the old check just never looked
        at it. Only `hlc_optic_HensoldtZO_Lo` classified correctly, and only because
        it happens to end at `optic_aco`, which NIArms does not redefine.
        """
        for ancestor in self.chain(root, name) + [self.root_parent(root, name)]:
            for prefix, kind in VANILLA_ATTACHMENT_PREFIXES.items():
                if ancestor.startswith(prefix):
                    return kind
        return ""

    def _vanilla_gear_kind(self, root: str, name: str) -> str:
        """Kind from a vanilla gear base anywhere in the ancestry.

        Only reached when ItemInfo has already failed, so an item that classifies
        properly can never be reclassified by this -- which is what makes it safe to
        add to compats that already work.

        CfgWeapons only: CfgGlasses and CfgVehicles are settled earlier by root, and
        letting a `v_`/`u_`/`h_` prefix loose on the weapon roots would misfile
        anything that happened to start with one.
        """
        if root != "CfgWeapons":
            return ""
        for ancestor in self.chain(root, name) + [self.root_parent(root, name)]:
            kind = VANILLA_GEAR_BASES.get(ancestor)
            if kind:
                return kind
            for prefix, kind in VANILLA_GEAR_PREFIXES.items():
                if ancestor.startswith(prefix):
                    return kind
        return ""

    def _inherits_vanilla_bag(self, root: str, name: str) -> bool:
        """Whether a vanilla backpack base sits anywhere in the ancestry.

        Only consulted when `isBackpack` is absent from the whole chain, so a mod
        that sets the flag itself never reaches here and cannot be reclassified by
        it. That is what keeps this safe for compats that already work.

        The whole chain is scanned rather than just `root_parent`, for the same
        reason as _vanilla_attachment_kind: a mod may insert its own base class
        between its items and the vanilla bag.
        """
        for ancestor in self.chain(root, name) + [self.root_parent(root, name)]:
            if ancestor in VANILLA_BACKPACK_BASES:
                return True
        return False

    def _effective_scope(self, root: str, name: str) -> int:
        """`scope`, supplying vanilla's value where the dump cannot reach it.

        Attachments routinely inherit scope from a vanilla optic instead of
        declaring their own:

            hlc_optic_VOMZ -> optic_lrps      scope resolves to nothing

        Vanilla `optic_LRPS` carries `scope = 2`, but it is not in the dump, so the
        chain runs out and the item looks hidden -- while the game lists it quite
        happily. Weapons never hit this: mods always declare `scope = 2` on their
        own weapon classes.

        So: no scope anywhere in the chain, but the chain reaches a known vanilla
        attachment class, means 2. That is filling in a value the dump is missing,
        not guessing -- every vanilla attachment is scope 2. A class that really is
        hidden says so explicitly with `scope = 1`, which is honoured as normal.

        Magazines inherit scope the same way and get the same treatment. BWmod's
        G28 magazines derive from vanilla 20Rnd_762x51_Mag and declare no scope of
        their own; the ten-round versions, which BWmod really does hide, say
        `scope = 1` outright and are still excluded by the check above.
        """
        raw = self.resolve(root, name, "scope")
        if raw is not None:
            return _as_int(raw, 0)
        if self._vanilla_attachment_kind(root, name):
            return 2
        if self._inherits_vanilla_magazine(root, name):
            return 2
        return 0

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
                        scope=self._effective_scope(root, key),
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
        return [
            i for i in self.items()
            if i.kind in wanted and i.is_arsenal_visible and i.display_name.strip()
        ]

    def unnamed_items(self) -> list[Item]:
        """Arsenal-visible items whose displayName does not resolve.

        Grouping is entirely display-name based, so these cannot be grouped and are
        left out of `arsenal_items`. They are almost always vanilla classes the mod
        merely *patches* -- `optic_LRPS`, `muzzle_snds_H` -- whose name lives on the
        vanilla class and so is not in the dump. Those belong to a vanilla compat,
        not this one, and mapping them would collapse unrelated items into a single
        entry labelled "".

        Exposed rather than silently dropped so the tools can report the count.
        """
        wanted = set(self.kinds)
        return [
            i for i in self.items()
            if i.kind in wanted and i.is_arsenal_visible and not i.display_name.strip()
        ]


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


def decompose_display_name(
    display_name: str, compose: dict | None = None
) -> tuple[str, tuple[str, ...], dict[str, str]]:
    """parse_display_name, plus a pass for names built by composition.

    Some mods write an item and everything bolted to it as one name. Tier One
    writes optics that way, and lasers with the host weapon on the front:

        Micro T-2/Leap/G33/LT 5/8       -> "Micro T-2"  mount LEAP, magnifier G33, riser LT58
        M4BII // LA-5B/M600V (Tan)/alt  -> "LA-5B"      light M600V, variant ALT, token Tan

    Without this every composition is its own base name and its own arsenal row --
    the Micro T-2 alone spans thirteen.

    Splitting on the separator cannot work, because component names contain it too:
    "LT 5/8", "UTG 3/50", "AN/PVS-10", "SpecterDR 1.5x/6x". Parts are matched
    against the declared vocabulary instead, longest first, and only where the
    separator immediately precedes them -- so a name that merely *contains*
    "UTG 3/50" keeps it whole.

    Returns (base, tokens, values).
    """
    base, tokens = parse_display_name(display_name)
    if not compose:
        return base, tokens, {}

    parts = compose.get("parts") or {}
    separator = str(compose.get("separator") or "/")
    # Longest first, so "LT 5/8" is preferred over a shorter part inside it.
    ordered = sorted(
        ((str(p), (str(av[0]), str(av[1]))) for p, av in parts.items()),
        key=lambda kv: -len(kv[0]),
    )

    # Literal trailing strings, for markers parse_display_name cannot see. It
    # matches "(...)" and "{...}" only, so Tier One's "[2D]" -- the non-PIP build
    # of a scope -- would otherwise pin sixteen SpecterDR variants to their own
    # rows AND block the parts below from ever reaching the end of the name.
    # Unlike the top-level `class_suffixes:`, these match the DISPLAY name.
    tails = sorted(
        ((str(s), (str(av[0]), str(av[1]))) for s, av in (compose.get("suffixes") or {}).items()),
        key=lambda kv: -len(kv[0]),
    )

    def consume(text: str) -> tuple[str, str, str] | None:
        """One part or literal tail sitting at the end of `text`."""
        for part, (axis, value) in ordered:
            tail = separator + part
            if text.endswith(tail) and len(text) > len(tail):
                return text[: -len(tail)].strip(), axis, value
        for suffix, (axis, value) in tails:
            if text.endswith(suffix) and len(text) > len(suffix):
                return text[: -len(suffix)].strip(), axis, value
        return None

    def strip(text: str) -> tuple[str, dict[str, str], list[str]]:
        """Strip composed parts off the end, right to left.

        Where a bracket marker blocks the way it is stepped over SPECULATIVELY and
        the step kept only if it exposes another part. That conditional is the whole
        safety argument. Tier One writes two markers on one item --

            LA-5B/M600V (Tan) (Laser)   -> "LA-5B"  light M600V, camo Tan, beam Laser

        -- so the colour has to come off before "/M600V" is reachable. But stripping
        brackets repeatedly and unconditionally would also turn

            HK416 D10 (SMR/CTR) (Desert)  -> "HK416 D10"   instead of "HK416 D10 (SMR/CTR)"

        and break every `bases:` table that relies on parse_display_name's single
        strip -- including Tier One's own weapon half, in the same overrides file.
        Speculation separates the two: "HK416 D10" matches no part, so the step is
        reverted and the base stands. A mod that declares no `compose:` table has no
        vocabulary to match, so nothing is ever kept and the result is unchanged.
        """
        values: dict[str, str] = {}
        toks: list[str] = []
        while True:
            hit = consume(text)
            if hit:
                text, axis, value = hit
                values[axis] = value
                continue
            inner, more = parse_display_name(text)
            if more and inner != text:
                sub_text, sub_values, sub_toks = strip(inner)
                if sub_values:  # the step paid for itself -- commit it
                    text = sub_text
                    values.update(sub_values)
                    toks[:0] = sub_toks + list(more)
                    continue
            return text, values, toks

    base, values, extra_toks = strip(base)
    toks = extra_toks + list(tokens)

    # "M4BII // LA-5B": the host weapon, which class_prefixes already reads off the
    # class name far more reliably. Dropping it merges the per-weapon copies.
    platform_separator = compose.get("platform_separator")
    if platform_separator and platform_separator in base:
        base, more_values, more_toks = strip(base.split(str(platform_separator), 1)[1].strip())
        values.update(more_values)
        toks = more_toks + toks

    return base, tuple(toks), values


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


def _as_expr_int(value, default=0):
    """_as_int, but tolerating the arithmetic a rapified config can carry.

    A config.bin stores a number either evaluated or as the expression that was
    written, and BI writes magazine types as products: SatchelCharge_Remote_Mag
    derapifies to `type = "2*\t\t256"`, not 512. Plain int() gives up on that and
    the magazine silently classifies as nothing.

    Deliberately limited to digits, * and +, evaluated only once the string has
    been proven to contain nothing else -- config values are untrusted input.
    """
    result = _as_int(value, None)
    if result is not None:
        return result
    if isinstance(value, str):
        packed = re.sub(r"\s+", "", value)
        if packed and re.fullmatch(r"\d+(?:[*+]\d+)*", packed):
            total = 0
            for term in packed.split("+"):
                product = 1
                for factor in term.split("*"):
                    product *= int(factor)
                total += product
            return total
    return default


def _norm_path(value) -> str:
    if not isinstance(value, str):
        return ""
    return value.replace("/", "\\").lstrip("\\").lower()


def _unescape(text: str) -> str:
    for entity, char in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")):
        text = text.replace(entity, char)
    return text
