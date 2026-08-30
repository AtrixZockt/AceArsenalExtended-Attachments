"""Load tools/mod.yml -- the one place this toolchain knows which mod it targets.

Every other .py file in this directory is mod-agnostic and reads its identity from
here, so starting a compat for a new mod means copying tools/ and writing a new
mod.yml plus overrides.yml.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parent
DUMP = REPO / "_dump"
ADDON = REPO / "addons" / "main"
MOD_YML = TOOLS / "mod.yml"
OVERRIDES = TOOLS / "overrides.yml"

# Which arsenal tabs a compat covers. These are ACEAX's own tab names -- see
# modconfig.KIND_ROOT for the config root each one is emitted under.
WEAPON_KINDS = ("primary", "handgun", "launcher")
GEAR_KINDS = ("headgear", "uniform", "vest", "backpack", "goggles")
OTHER_KINDS = ("nvg", "binocular")
# Right-panel items. These only do anything in game with the aceaxatt extension
# loaded; without it the generated entries are inert. See ATTACHMENT_COMPAT.md.
ATTACHMENT_KINDS = ("optic", "pointer", "muzzle", "bipod")
# Also right-panel, also aceaxatt-only. One kind rather than several because ACE
# spreads magazines over four tabs -- compatible, secondary muzzle, all, and the
# current weapon's -- that all draw on the same CfgMagazines classes. Grenades
# and explosives are genuinely separate tabs and are not covered; modconfig's
# _magazine_kind excludes them.
MAGAZINE_KINDS = ("magazine",)
ALL_KINDS = WEAPON_KINDS + GEAR_KINDS + OTHER_KINDS + ATTACHMENT_KINDS + MAGAZINE_KINDS

# Convenience names accepted in mod.yml in place of listing the tabs out.
KIND_ALIASES = {
    "weapons": WEAPON_KINDS,
    "gear": GEAR_KINDS,
    "attachment": ATTACHMENT_KINDS,
    "attachments": ATTACHMENT_KINDS,
    "magazines": MAGAZINE_KINDS,
    "all": ALL_KINDS,
}


def pbo_member(spec: str) -> tuple[str, str]:
    """Split a `packs:` key into a pbo stem and the config inside it.

    A plain stem means the config.bin at the pbo root, which is the only one every
    Workshop mod has. The base game instead ships one config.bin per sub-addon --
    weapons_f.pbo has 29 of them, and every optic is in acc\\config.bin while the
    root config holds only CfgPatches and forward declarations. A key may
    therefore name the member: `weapons_f/acc` or `weapons_f/Rifles/MX`.

    Each member becomes its own pack, which needs no merging: Config.load already
    resolves inheritance across packs, since that is how a weapon whose parent
    lives in another pbo resolves today.
    """
    stem, _, inner = spec.partition("/")
    if not inner:
        return stem, "config.bin"
    return stem, inner.replace("/", "\\") + "\\config.bin"


@dataclass(frozen=True)
class Source:
    """One mod whose PBOs get dumped.

    `resolve_only` marks a mod that is dumped purely so inheritance and `scope`
    resolve, and is never searched for weapons -- needed when the mod you are
    patching extends another one. BWA3 Add's weapons inherit from BWMod's, so
    without BWMod dumped alongside, none of them resolve to a weapon at all.

    `addon_dirs` is where the PBOs live relative to `path`. Every Workshop mod
    keeps them in a single `addons/`, which is the default; the base game does
    not, splitting its content over `Addons/` plus one directory per DLC. A stem
    is looked up in each listed directory in turn.
    """

    name: str
    workshop_id: str
    path: Path
    packs: dict[str, str]  # pbo stem (or stem/sub-config) -> short pack name
    base_packs: tuple[str, ...]  # short names contributing no weapons of their own
    resolve_only: bool = False
    addon_dirs: tuple[str, ...] = ("addons",)

    @property
    def addon_paths(self) -> tuple[Path, ...]:
        return tuple(self.path / d for d in self.addon_dirs)

    def find_pbo(self, stem: str) -> Path | None:
        for folder in self.addon_paths:
            pbo = folder / f"{stem}.pbo"
            if pbo.is_file():
                return pbo
        return None


@dataclass(frozen=True)
class ModInfo:
    prefix: str
    name: str
    author: str
    version: str
    model_prefix: str
    sources: tuple[Source, ...]
    kinds: tuple[str, ...]

    @property
    def config_roots(self) -> tuple[str, ...]:
        """The config roots these kinds live in, in a stable order.

        Imported lazily: modconfig imports this module, so it cannot be imported
        at the top of it.
        """
        import modconfig

        order = {root: i for i, root in enumerate(modconfig.CONFIG_ROOTS)}
        roots = {modconfig.KIND_ROOT[k] for k in self.kinds}
        return tuple(sorted(roots, key=lambda r: order[r]))

    @property
    def patch_class(self) -> str:
        return f"{self.prefix}_main"

    @property
    def pbo_name(self) -> str:
        return f"{self.prefix}_main.pbo"

    @property
    def built_pbo(self) -> Path:
        return REPO / ".hemttout" / "build" / "addons" / self.pbo_name

    @property
    def source_name(self) -> str:
        """The mod this compat is for -- the first source it actually covers."""
        for source in self.sources:
            if not source.resolve_only:
                return source.name
        return self.sources[0].name if self.sources else self.name

    @property
    def source_names(self) -> str:
        """All covered mods, for messages: "BWMod + BWA3 Add"."""
        covered = [s.name for s in self.sources if not s.resolve_only]
        return " + ".join(covered) if covered else self.source_name

    @property
    def base_packs(self) -> tuple[str, ...]:
        """Packs never searched for weapons, across every source.

        A resolve-only source contributes all of its packs, which is the whole
        point of the flag.
        """
        out: list[str] = []
        for source in self.sources:
            out.extend(
                source.packs.values() if source.resolve_only else source.base_packs
            )
        return tuple(dict.fromkeys(out))

    @property
    def pack_order(self) -> dict[str, int]:
        """Short pack name -> source index, for breaking ties deterministically."""
        return {
            pack: i for i, s in enumerate(self.sources) for pack in s.packs.values()
        }


@lru_cache(maxsize=1)
def load() -> ModInfo:
    data = yaml.safe_load(MOD_YML.read_text(encoding="utf-8"))

    # `sources:` is a list; the older single `source:` mapping is still accepted
    raw = data.get("sources") or ([data["source"]] if "source" in data else [])
    if not raw:
        raise SystemExit(f"{MOD_YML} has neither `sources:` nor `source:`")

    sources: list[Source] = []
    seen: dict[str, str] = {}
    for entry in raw:
        packs = dict(entry.get("packs") or {})
        for stem, short in packs.items():
            if short in seen:
                raise SystemExit(
                    f"{MOD_YML}: pack name {short!r} is used twice "
                    f"({seen[short]} and {stem}). Short names become _dump/ filenames, "
                    "so they must be unique across every source."
                )
            seen[short] = stem
        sources.append(
            Source(
                name=entry.get("name", data["name"]),
                workshop_id=str(entry.get("workshop_id", "")),
                path=Path(entry["path"]),
                packs=packs,
                base_packs=tuple(entry.get("base_packs") or ()),
                resolve_only=bool(entry.get("resolve_only")),
                addon_dirs=tuple(entry.get("addon_dirs") or ("addons",)),
            )
        )

    return ModInfo(
        prefix=data["prefix"],
        name=data["name"],
        author=data["author"],
        version=str(data.get("version", "1.0.0")),
        model_prefix=data["model_prefix"],
        sources=tuple(sources),
        kinds=_kinds(data.get("kinds")),
    )


def _kinds(raw) -> tuple[str, ...]:
    """Expand and validate `kinds:`.

    Absent means weapons only, which is what every compat written before gear
    support existed meant. Copying these tools into one of those repos therefore
    changes nothing until its mod.yml opts in.
    """
    if raw is None:
        return WEAPON_KINDS
    if isinstance(raw, str):
        raw = [raw]

    out: list[str] = []
    for entry in raw:
        name = str(entry).strip().lower()
        if name in KIND_ALIASES:
            out.extend(KIND_ALIASES[name])
        elif name in ALL_KINDS:
            out.append(name)
        else:
            raise SystemExit(
                f"{MOD_YML}: unknown kind {entry!r}. "
                f"Use one of {', '.join(ALL_KINDS)}, or the aliases "
                f"{', '.join(KIND_ALIASES)}."
            )
    if not out:
        raise SystemExit(f"{MOD_YML}: `kinds:` is empty -- remove it, or list some tabs")
    # keep ALL_KINDS order so messages and reports read consistently
    return tuple(k for k in ALL_KINDS if k in set(out))
