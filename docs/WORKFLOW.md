# Workflow

How to drive the tooling in `tools/`, in the right order — and how to stand up a compat for a
different mod.

## This repo at a glance

This is **not** a compat. It is the `@aceaxatt` runtime extension plus the toolchain, kept here so
anyone can build an attachment compat from one clone.

| | |
|---|---|
| what it ships | the addon that makes the arsenal's right panel collapse attachments |
| `prefix` | `aceaxatt` |
| `tools/` | the shared generator, attachment-capable; no `mod.yml` / `overrides.yml` |
| to build a compat | copy `tools/` elsewhere -- see [ATTACHMENT_COMPAT.md](ATTACHMENT_COMPAT.md) |

Because there is no `mod.yml` here, the commands below are for the compat repo you create, not for
this one. Everything from "Before you start" down is the shared toolchain reference — copy this file
into your compat alongside `tools/` if you want it to hand.

---

## Before you start

- **HEMTT 1.19+** on `PATH` — `hemtt --version`
- **Python 3.9+** with **PyYAML** — `python -c "import yaml"`
- The **source mod subscribed** in Steam, so its PBOs exist locally at the path in `tools/mod.yml`

`_dump/` is gitignored. A fresh clone has no dump, so nothing works until you run step 0.

## 1. The everyday loop

```
python tools/dump_configs.py               # 0. once; skips packs already dumped
python tools/report.py --bases             # 1. see how the mod's display names group
#      ... edit tools/overrides.yml ...    # 2.
python tools/gen_aceax.py --check --list   # 3. fast feedback, writes nothing
python tools/gen_aceax.py                  # 4. write addons/main/
hemtt build                                # 5.
python tools/verify.py                     # 6. validates the BUILT pbo
python tools/report.py --coverage          # 7. audit where every item went
hemtt launch arsenal                       # 8. then the in-game diag
```

**0. Dump.** Extracts each pack's `config.bin` and stringtable and derapifies them to
`_dump/*.json`. Slow the first time, instant afterwards — it skips packs that already have JSON.

**1. Look at the groups.** `--bases` shows how the mod's `displayName`s cluster, which is the raw
material for `overrides.yml`. `--p3d <pack>` and a bare `<pack>` give other views;
no arguments gives a per-pack summary broken down by arsenal tab.

**2. Edit `tools/overrides.yml`.** The only file you hand-write. Never edit anything under
`addons/main/XtdGearModels/` or `XtdGearInfos/` — they are regenerated and your changes will be
overwritten.

**3. Check.** `--check` runs every validation and writes nothing, so it is the one to iterate on.
`--list` adds a line per model showing its arsenal tab, pack, axes and values.

**4. Generate.** Writes `addons/main/`, and deletes generated files that no longer match a model.
The generator is **idempotent**: `0 changed file(s)` means there was nothing to do, not that it
failed.

**5. Build.** `hemtt build` rapifies the config into `.hemttout/build/`. A config error here means
the generated `.hpp` is malformed — report it, it is a generator bug.

**6. Verify.** Re-reads the **built PBO**, so `hemtt build` must have run first. It applies the same
rules as ACEAX's own `fnc_diag_detectErrors`, plus a cross-check that every mapped class is a real
arsenal-visible item in the dump, under the config root it was mapped under. Exit 0 with no
`error(s)` block is a pass; warnings are fine.

**7. Audit coverage.** Lists every item and the entry it sits behind, ending in a reconciliation
line — every item must appear exactly once, behind an entry or as a standalone row. Reads
`overrides.yml` live, so it needs no build.

That reconciliation balances only the items the classifier **found**. Anything it failed to classify
never becomes an arsenal item at all, so it cannot show up as missing — it is simply absent, with no
error anywhere. `--coverage` prints a one-line nudge when that has happened; the detail is:

```
python tools/report.py --unclassified
```

Classes with `scope = 2` and a display name that resolve to no arsenal kind, grouped by the class
their inheritance ends at, because that terminal names the cause:

| ends at | meaning | fix |
|---|---|---|
| a vanilla gear or bag base | the dump holds a body-less forward declaration — a mod writing `class H_HelmetB;` to reference the vanilla class | `modconfig`'s `VANILLA_*` tables should cover it; add the base if not |
| **another mod's class** | the chain leaves the dump entirely | dump that mod too: `init_mod.py --requires <id>`, which marks it `resolve_only` |
| a class in your own dump | the mod is doing something unusual | look by hand |

**Not a pass/fail check.** An attachments-only compat legitimately leaves the mod's weapons
unclassified — Tier One reports 81 for exactly that reason. Read it, do not gate on it.

`CfgVehicles` misses are counted but not listed, because only backpacks are arsenal items there and
soldier units belong in that bucket — except when the terminal looks like a bag, which is the one
`CfgVehicles` case that is a real miss.

**8. Test in game.** `hemtt launch arsenal` starts Arma with the required mods and drops you into
the ACE Arsenal VR mission. Then, in the debug console:

```sqf
diag_log ([] call aceax_gearinfo_fnc_diag_detectErrors);   // must print 0
```

### Order rules worth remembering

| | |
|---|---|
| `verify.py` needs a build | it reads the PBO, not the source files |
| `report.py` needs no build | it reads `overrides.yml` and `_dump/` |
| `gen_aceax.py --check` writes nothing | use it while iterating; drop `--check` when happy |
| `dump_configs.py` is not idempotent-sensitive | safe to re-run, skips finished packs |
| `init_mod.py` / `init_overrides.py` are one-shot | they refuse to overwrite without `--force` |
| `check_ingame.py` needs the game | see §5; everything else is offline |

## 2. After the source mod updates

```
python tools/dump_configs.py --force     # re-extract everything
python tools/gen_aceax.py --check        # what changed?
python tools/gen_aceax.py
hemtt build && python tools/verify.py
```

`--force` is required — without it the dump is considered up to date and nothing is re-read.

New or renamed variants show up as **unmapped displayName token(s)**; add them to `tokens:` (or to
`bases:` if the mod put the distinction in the base name rather than a `(marker)`). Then re-run and
read the file diff: it tells you exactly which arsenal entries changed.

## 3. Starting a compat for a new mod

> For a full walkthrough written for someone who has not used this toolchain before --
> including the scaffold files in full -- see **[NEW_COMPAT.md](NEW_COMPAT.md)**.
> This section is the condensed version.

Most of the first hour is now automated. The short version:

```
git clone https://github.com/AtrixZockt/AceArsenalExtended-Attachments
mkdir  AceArsenalExtended_Foo && cd $_
cp -r  ../AceArsenalExtended-Attachments/tools .  # the .py files are mod-agnostic

python tools/init_mod.py <workshop_id> --prefix aceaxfoo --model-prefix foo
#      ... create the six scaffold files it lists ...
python tools/dump_configs.py
python tools/init_overrides.py
python tools/report.py --families                # candidate bases: groupings
#      ... edit tools/overrides.yml ...
python tools/gen_aceax.py --check
```

### 3.1 `init_mod.py` — the pack list

```
python tools/init_mod.py 1234567890 --prefix aceaxfoo --model-prefix foo --author "You"
```

Derapifies every PBO in the Workshop item and reports which ones hold arsenal-visible items,
broken down by arsenal tab:

```
  bwa3_carlgustav       1 item(s)  [launcher 1]
  bwa3_common              - base classes / stringtable
  bwa3_g36             33 item(s)  [primary 33]
  bwa3_p8               1 item(s)  [handgun 1]
                          (29 other pbo(s) skipped)

  detected kinds: handgun 1, launcher 1, primary 33
```

Trust that over the PBO names — it is what reveals that BWMod's `bwa3_weapons` holds vehicle
armament, not personal weapons.

The tab breakdown is how you decide `kinds:`. It is written into `mod.yml` as whatever was found;
narrow it with `--kinds`, which takes tab names or the aliases `weapons` and `gear`:

```
python tools/init_mod.py 1234567890 --kinds weapons          # no gear
python tools/init_mod.py 1234567890 --kinds primary,handgun  # and no launchers either
```

It writes `tools/mod.yml` and prints the scaffold files you still need. Check the short pack names
it derived; they come from the PBO stems and you may prefer something shorter.

### 3.2 Files you still write by hand

```
.hemtt/project.toml        prefix = "<yourprefix>", mainprefix = "z", template = "cba"
.hemtt/launch.toml         CBA 450814997, ACE 463939057, ACEAX 2522638637, + the source mod
.gitignore                 copy from this repo (.hemttout/, _dump/, __pycache__/, ...)
mod.cpp                    name, dir = "@<yourprefix>", author
LICENSE
addons/main/$PBOPREFIX$    z\<yourprefix>\addons\main
```

`addons/main/config.cpp` and both `XtdGear` trees are **generated** — do not create them by hand.

> Write `$PBOPREFIX$` with an editor, not with shell `printf`/`echo -e`. `\a` is the BEL escape, so
> `printf 'z\\aceaxfoo\\addons\\main'` silently produces `z<BEL>ceaxfoo<BEL>ddons\main` and
> `hemtt build` fails with a baffling `failed to create directory` error.

### 3.3 Choose names that cannot collide

Arma merges same-named config classes across addons. If two loaded compats both define
`XtdGearModels >> niarms_barrel` with different values, they blend unpredictably. So pick a unique:

- `prefix` — becomes the PBO name, `$PBOPREFIX$` and the `CfgPatches` class
- `model_prefix` — prefixes every generated model class
- option-base class names in `overrides.yml` (`<prefix>_barrel`, `<prefix>_mount`, …)

`XtdGearModels >> CamoBase` is the deliberate exception: every compat is *meant* to merge extra
swatches into that shared palette.

### 3.4 `init_overrides.py` — the starter config

Run it after `dump_configs.py`. It writes every section the generator requires (it raises
`KeyError` on a missing one, so none can be left out) and pre-fills what is derivable:

- **`tokens:`** — every `(marker)` the mod uses. Colour words are matched against ACEAX's own
  `CamoBase` and mapped automatically; everything else is parked on a `variant` axis and tagged
  `TODO` for you to classify. On BWMod that mapped 2 of 2 tokens; on NIArms, 6 of 48; on Military
  Gear Pack, 8 of 21.
- **`camo_values_from_aceax:`** — read live from the installed ACEAX, not hand-copied
- **`options:` / `option_order:` / `option_bases:`** — skeletons for the axes the tokens produced
- **`bases:` / `weapons:` / `positional_axes:`** — left empty; those are the judgement calls
- **`compose:`** — written out as a commented example, not a live section. Add it only for a mod
  that writes an item *and its whole accessory stack* into one display name
  (`Micro T-2/Leap/G33/LT 5/8`). Absent, names parse exactly as they did before the feature existed,
  which is why it is safe to leave alone. See [OPTIONS.md](OPTIONS.md#compose)

It also flags tokens that appear in more than one capitalisation. Matching is case-**sensitive** and
that is deliberate: NIArms means a rail kit by `TAC` and a receiver configuration by `Tac`. A mod
that is merely inconsistent with itself — Military Gear Pack writes both `MC ARID` and `MC Arid` —
needs a `tokens:` line for each spelling, both pointing at the same value.

The result already generates a valid config, just an under-grouped one. That is a fine starting
point: build it up, re-running `gen_aceax.py --check` as you go.

### 3.5 `report.py --families` — candidate groupings

Base names alone will not spot that `G36KA0` belongs with `G36A3`. This clusters the base names in
each pack by shared stem. On a big mod that is hundreds of lines, so it writes a file and prints
only a summary:

```
python tools/report.py --families
```

```
  [primary/aug]   12 bases  "Steyr AUG"
  [primary/c96]    4 bases  "Mauser C96"
  ... 22 more

  30 candidate family/families -> _dump/families.yml
```

`_dump/families.yml` is valid YAML you can paste from wholesale:

```yaml
bases:
  # ---- [primary/aug] 12 bases sharing "Steyr AUG" ----
  "Steyr AUGA1":         {as: "Steyr AUG"}   # differs by: A1
  "Steyr AUGA1 Carbine": {as: "Steyr AUG"}   # differs by: A1 Carbine
  "Steyr AUG-SR HBAR":   {as: "Steyr AUG"}   # differs by: -SR HBAR
```

The **"differs by"** comment is the useful part — it tells you what the axes should be. Pasted as
written, a block merges its bases into one entry with no distinguishing option, which the generator
reports as `no distinguishing option` and skips: that is the prompt to add axes, not an error.

To skip the copying entirely:

```
python tools/report.py --families --write
```

inserts the proposals into the `bases:` block of `overrides.yml` directly, preserving your comments.
Either way, bases already in `bases:` are skipped, so re-running never duplicates and a second
`--write` is a no-op.

Suggestions are per arsenal tab and pack, and err towards over-merging, on the grounds that
deleting a line you disagree with is quicker than spotting a family that was missed.

> `--out <file>` works on the other modes too, if `--bases` or `--coverage` is more than you want
> to scroll through.

### 3.6 Then follow §1 from step 0.

## 3a. Keeping the camo list current

`camo_values_from_aceax:` mirrors ACEAX's shared palette and exists so the generator can catch a
camo value that would render as its raw name. It is not hand-maintained:

```
python tools/init_overrides.py --refresh-camo
```

Re-reads it from the installed `aceax_gearinfo.pbo`, rewriting only that block so your comments
survive. Worth running after an ACEAX update.

## 3b. Covering an add-on mod as well

Some mods extend another mod rather than standing alone. BWA3 Add is snow retextures of BWMod's
rifles, and its weapons inherit straight across:

```
BWAdd_G36A1   parent='BWA3_G36A1'   scope=None
```

Scanned on its own, `init_mod.py` reports **"no pbo contained an arsenal-visible item"** — the
parent class and the `scope` both live in the other mod, so nothing resolves. That is the symptom to
recognise.

`mod.yml` takes a **list** of sources for this:

```yaml
sources:
  - name: "BWMod"
    workshop_id: 1200127537
    path: '...'
    packs: {bwa3_g36: g36, ...}

  - name: "BWA3 Add"
    workshop_id: 1326881314
    path: '...'
    packs: {bw_snow_rifles: add_snow}
```

Short pack names must be unique across every source — they become `_dump/` filenames.

**Items from different sources that share a display-name base land in the same arsenal entry.**
That is the point: BWMod's `G36A1` and BWA3 Add's `G36A1 (White)` share the base `G36A1`, so White
becomes another camo value on the existing G36 row rather than a parallel set of rows. The generator
lists what it merged:

```
10 entr(y/ies) merged across sources:
  G36        add_snow+g36  -> bwa3_g36_g36
```

Read that list — it is also what would catch two unrelated mods accidentally sharing a name. If a
merge is wrong, give one side a different entry with `as:` in `bases:`, or force its pack with
`pack:`.

Two ways to set this up:

```
python tools/init_mod.py <addon id> --requires <id of the mod it extends>
```

creates a `mod.yml` covering the add-on, with the parent mod marked `resolve_only: true` — dumped so
inheritance resolves, never searched for items. That is the **standalone add-on compat** shape.

```
python tools/init_mod.py <addon id> --add
```

scans the add-on against the sources already in `mod.yml` and prints a `sources:` entry to paste.
That is the **fold it into an existing compat** shape, and usually the better one: only one addon can
usefully map a given class, and sharing entries across mods only works from inside a single addon.

Players do not need the add-on installed. `XtdGearInfos` entries for absent classes are inert, and
`fnc_getModelOptions` filters option values down to the items actually in the arsenal, so the extra
camo simply does not appear.

## 3c. Gear compats

A compat can cover uniforms, vests, headgear, backpacks and facewear as well as — or instead of —
weapons. This repo is the gear-only case: Military Gear Pack ships 511 items and not one weapon.

### `kinds:` and the three config roots

ACEAX drives **ten arsenal tabs** out of **three config roots** (its
`addons/arsenal/XEH_preInit.sqf`):

| tab (`kind`) | config root |
|---|---|
| `primary`, `handgun`, `launcher` | `CfgWeapons` |
| `headgear`, `uniform`, `vest` | `CfgWeapons` |
| `nvg`, `binocular` | `CfgWeapons` |
| `backpack` | `CfgVehicles` |
| `goggles` | `CfgGlasses` |
| `optic`, `pointer`, `muzzle`, `bipod` | `CfgWeapons` |

`kinds:` in `mod.yml` picks which of those the compat covers, and that decides which roots get
dumped, grouped and emitted:

```yaml
kinds: [headgear, uniform, vest, backpack, goggles]   # or just: [gear]
kinds: [optic, pointer, muzzle, bipod]                # or just: [attachment]
```

**Omitting `kinds:` means weapons only.** That is what every compat written before gear support
meant, so the older repos keep working with these tools untouched.

The four attachment kinds are the odd ones out: stock ACEAX ignores the right panel entirely, so
they need the `@aceaxatt` extension to do anything in game. The data is inert without it rather
than broken — see [ATTACHMENT_COMPAT.md](ATTACHMENT_COMPAT.md).

The generated config grows a block per root:

```
class XtdGearModels
{
    #include "XtdGearModels_Common.hpp"
    class CfgGlasses  { ... };
    class CfgVehicles { ... };
    class CfgWeapons  { ... };
};
```

A model belongs to exactly one root, so grouping is keyed on `(root, label)`. Two items in
different roots that happen to share a display name stay separate entries, and may safely share a
generated class name — they are different config paths.

### How an item's tab is worked out

Not from `ItemInfo >> type`, which is how the game does it: `type` is declared on the vanilla
`HeadgearItem` / `VestItem` / `UniformItem` classes, which are never in the dump, so offline every
gear item reports no type at all. Instead, in order:

1. root `CfgGlasses` → `goggles`
2. root `CfgVehicles` with `isBackpack = 1` → `backpack` (the flag is what separates a wearable bag
   from an ammo crate — both descend from `ReammoBox`). Failing that, a **vanilla bag base anywhere
   in the ancestry** — `B_Carryall_Base`, `B_Kitbag_Base`, `B_AssaultPack_Base` and friends. A mod
   may inherit `isBackpack` rather than restate it, and the vanilla class holding it is never in the
   dump, so the chain walk cannot reach it: VSM's 44 backpacks were invisible until this fallback
   existed, with no error to say so. A mod that sets the flag itself never reaches the fallback.
3. `ItemInfo`'s **parent class** → `HeadgearItem` / `VestItem` / `UniformItem` / `NVGoggles`
3a. failing that, a **vanilla gear base anywhere in the ancestry** — the `H_` / `V_` / `U_` prefixes
   Arma uses for its own gear, plus the generic `Uniform_Base` / `Vest_Base` / `Vest_Camo_Base`.
   Needed because a mod that writes `class H_HelmetB;` to reference the vanilla helmet leaves a
   body-less stub in the dump, and `class ItemInfo : ItemInfo` then inherits from *that* rather than
   from the vanilla class — so `HeadgearItem` is never reached. VSM lost 13 helmets and 99 uniforms
   this way. Reached only when step 3 fails, so an item that already classifies cannot be changed
4. otherwise the inheritance root — `rifle` / `pistol` / `launcher` — with a weapon's own
   `type = 2` (handgun) or `4096` (binocular) overriding it

Headgear, uniforms and vests are all `CfgWeapons`, so the tab check in `gen_aceax.py` is doing real
work there: a careless `bases:` line that merged a helmet with a plate carrier is caught as
`spans arsenal tabs`.

### `positional_axes:` — two camos on one item

Some gear encodes more than one colour in a single marker. Military Gear Pack names a uniform
`Fleece + G3 Field Pants (GREY+3CD)`: grey fleece, three-colour-desert trousers. `+` is a token
separator, and

```yaml
positional_axes: [camo, pantscamo]
```

puts the first token on `camo` and the second on `pantscamo`, whatever axis the token table gave
them. `pantscamo` is a conventional ACEAX option exactly like `camo` — see `XtdGearModels >>
Conventional` — so it inherits the same labels and swatches from `CamoBase` and needs no option
base of its own. List both in `camo_axes:` so the generator checks their values resolve:

```yaml
camo_axes: [camo, pantscamo]
```

Leave `positional_axes:` empty unless the mod actually does this. Where a mod collapses `(KHK+KHK)`
to `(KHK)`, fix those items in `weapons:`.

### Case, and lower-cased config roots

Class names, property names **and config root names** are all read case-insensitively. This is not
a nicety: Military Gear Pack writes `class cfgWeapons` and `displayname`, and is not consistent
with itself — `CfgVehicles` in one PBO, `cfgVehicles` in the next. Read case-sensitively the mod
looks empty.

The same fix has a real effect on weapon compats. NIArms writes `scopearsenal` all-lowercase on 15
classes; twelve of those are belt variants with `scopearsenal = 0`, which the game hides from the
arsenal and the old case-sensitive loader did not. Expect a weapon count to *drop* when these tools
land in an older repo, and check the diff — that is the loader agreeing with the game, not losing
weapons.

### Accessories: option value or its own entry?

The weapon compats give a mounted grenade launcher its own entry, on the grounds that it changes
what the weapon *is*. Gear generally goes the other way: a helmet with goggles pushed up is the
same helmet, so `goggles` and `belt` are dropdown values here. Both calls are made in `bases:`;
neither is forced by the tooling.

## 4. What each message means

| message | meaning | what to do |
|---|---|---|
| `N unmapped displayName token(s)` | a `(marker)` the token table does not cover | add it to `tokens:`, or ignore it if the group is a single item |
| `skipped N group(s) with no distinguishing option` | two items share a base name and every option value | give one of them a distinguishing value in `weapons:` |
| `X and Y both map to A+B` | two items resolve to the same combination, so one is unreachable | **blocks generation** — add an axis or a `weapons:` override |
| `spans arsenal tabs ['headgear', 'vest']` | a model mixes two tabs | **blocks generation** — ACEAX groups within one tab; split the model in `bases:` |
| `camo value 'X' has no CamoBase entry` | a camo value with no label or swatch anywhere | **blocks generation** — add it to `camo_values:` |
| `N model(s) depend on weak-match ordering` | reachable in practice, but not provable from the config | warning only; treat those groupings as the riskier ones to edit |
| `name clashes with the X entry of the same name` | one display name in two config roots — VSM's Peltor is both headgear and facewear | nothing; the second is emitted with a root suffix so Arma does not see one class twice |
| `MISSING: N item(s)` in coverage | an item is in neither an entry nor the standalone list | a generator bug — report it |
| `is a CfgVehicles class, mapped under CfgWeapons` | a model was emitted under the wrong root | a generator bug — report it |
| `no arsenal items in _dump/` | the dump is empty, or `kinds:` excludes everything the mod has | run `dump_configs.py`; check `kinds:` against `report.py` |
| `no built pbo at ...` | `verify.py` ran before `hemtt build` | build first |

### About the weak-match warning

ACEAX resolves a dropdown click by replacing one value in the current item's option tuple and
looking for an exact match. If there is none it falls back to `fnc_findConfigByValue`, which returns
the *first* variation holding that value — from a HashMap, whose iteration order Arma does not
guarantee. The check therefore counts only moves that hold regardless of ordering: exact matches,
plus values held by exactly one item.

**The count is what tells you which kind of warning it is**, and the difference matters:

- **A handful of variants** usually means a *sparse grid* — the mod simply does not ship every
  combination, as with the Mk 48, which has no Para furniture in every finish. Those work in
  practice; they just cannot be *proven* from the config alone. Treat them as the riskier groupings
  to edit and move on.
- **A large fraction of the entry** means two axes are **coupled**: one only takes a value when the
  other does, so no single click can cross between the two halves. That is a genuine bug, not an
  unprovable one. Tier One's LA-5B reported 177 of 177 because its colour marker describes the
  weaponlight, not the laser — so `camo` only exists once `light` does. Clicking "M600V" on a bare
  LA-5B fell through to the fallback and returned another weapon platform's class.

The fix for the second kind is to **split the entry**, not to merge harder. Look for an axis whose
values never co-occur with another's; `[OPTIONS.md](OPTIONS.md)` has the worked example.

## 5. Cross-checking against the running game

Everything above validates against `_dump/`, which is only an approximation of what Arma loads: the
PBOs are merged here in a guessed order, the arsenal-visibility rules are reimplemented in Python,
and stringtables are parsed with a regex because some mods ship malformed XML. This is the check
that closes that gap.

```
python tools/check_ingame.py --sqf
```

Prints a snippet with the right class-name prefixes and config roots baked in. Paste it into the
debug console with the source mod loaded — it walks each fully-merged root, filters with ACEAX's own
`aceax_gearinfo_fnc_filterConfigEntries` rather than a copy of it, and writes the results to the
RPT. Then:

```
python tools/check_ingame.py
```

reads the newest RPT and reports three things:

| finding | meaning |
|---|---|
| in game, not in the dump | a pack missing from `packs:` in `mod.yml`, or a `kinds:` that is too narrow |
| in the dump, not in game | stale dump, or the source mod updated — re-dump with `--force` |
| displayName mismatch | the game resolved a stringtable key differently than the dump did |

`OK -- the dump matches the game exactly.` means the offline pipeline and reality agree.

Also still available, for a quick class-list-only comparison without the SQF step:

```sqf
["milgp_"] call aceax_gearinfo_fnc_diag_fullReportExport;   // copies to clipboard
```

Note that export only walks `CfgWeapons` and `CfgGlasses`, so a gear compat's backpacks are missing
from it. `check_ingame.py` covers all three roots.

```
cut -d';' -f2 pasted.txt | sort > ingame.txt
python tools/report.py --coverage --csv | sort > dumped.txt
diff ingame.txt dumped.txt
```
