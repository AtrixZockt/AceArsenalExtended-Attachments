# Starting a new ACEAX compat

A complete walkthrough for building an ACE3 Arsenal Extended compatibility patch for a mod that
does not have one yet — weapons, gear, or both. No prior knowledge of this toolchain assumed.

Budget roughly an hour, most of it spent on step 8 deciding how things should be grouped. The
mechanical parts are automated.

Throughout, the example is a made-up mod: **FooMod**, Workshop id `1234567890`. Substitute your own.

---

## Before you start

| | |
|---|---|
| [HEMTT](https://github.com/BrettMayson/HEMTT) 1.19 or newer, on `PATH` | check with `hemtt --version` |
| Python 3.9+ with PyYAML | check with `python -c "import yaml"`; install with `pip install pyyaml` |
| Subscribed in Steam | CBA_A3, ACE3, ACE3 Arsenal Extended, **and the mod you are patching** |

**Finding the Workshop id:** open the mod's Workshop page and read the number after `?id=` in the
address bar. For `steamcommunity.com/sharedfiles/filedetails/?id=1234567890` the id is `1234567890`.

The mod must be *installed*, not just favourited — the tooling reads its PBOs off disk.

---

## Step 1 — Create the folder and copy the tools

The generator lives in the ACEAX Attachments repo. Clone it, then copy `tools/` into a new folder
beside it — one folder per compat:

```
git clone https://github.com/AtrixZockt/AceArsenalExtended-Attachments
mkdir AceArsenalExtended_Foo
cd    AceArsenalExtended_Foo
cp -r ../AceArsenalExtended-Attachments/tools .
```

That repo is the addon, not a compat, so its `tools/` holds only the `.py` files — nothing to clean
up. An existing compat is an equally good source if you already have one, since the `.py` files are
meant to be byte-identical between them and carry no mod identity; in that case also
`rm tools/mod.yml tools/overrides.yml`, because those two are the per-mod half. Either way you are
about to generate your own.

---

## Step 2 — Choose your two names

You need to decide these now because everything else is built from them.

**`prefix`** identifies your addon. It becomes the PBO filename (`aceaxfoo_main.pbo`), the
`CfgPatches` class (`class aceaxfoo_main`), the internal path (`z\aceaxfoo\addons\main`) and the mod
folder (`@aceaxfoo`). The convention is `aceax` plus a short tag for the mod: `aceaxnia`, `aceaxbw`,
`aceaxmgp`, so FooMod gives `aceaxfoo`.

**`model_prefix`** namespaces the config classes the generator writes — `foo_ak_kalashnikov`,
`foo_barrel`, and so on.

Both must be **unique across every compat a player might load at once**. Arma merges same-named
config classes across addons, so two patches sharing a name would silently blend into each other.
Lowercase, letters and digits, no spaces.

> Do not use bare `aceax` as your prefix — that would produce `aceax_main`, which is what ACEAX's
> own core addon is called.

Known prefixes so far: `aceax` (core), `aceaxatt` (the attachments extension), `aceaxnia`, `aceaxbw`, `aceaxmgp`.

---

## Step 3 — Generate `tools/mod.yml`

```
python tools/init_mod.py 1234567890 --prefix aceaxfoo --model-prefix foo --author "You"
```

This derapifies every PBO in the mod and reports which ones actually contain arsenal items, broken
down by which arsenal tab they land on:

```
FooMod  (47 pbos) -- derapifying, this takes a minute

  foo_carlgustav        1 item(s)  [launcher 1]
  foo_common               - base classes / stringtable
  foo_g36              33 item(s)  [primary 33]
  foo_helmets          40 item(s)  [headgear 40]
  foo_p8                1 item(s)  [handgun 1]
                           (29 other pbo(s) skipped)

  detected kinds: handgun 1, headgear 40, launcher 1, primary 33

wrote tools/mod.yml
  kinds: primary, handgun, launcher, headgear
```

**Read that list before moving on.** Three things to check:

- **`kinds:`.** Whatever was found goes into `mod.yml`. Narrow it with `--kinds`, which accepts tab
  names or the aliases `weapons` (primary/handgun/launcher), `gear` (headgear/uniform/vest/
  backpack/goggles) and `attachment` (optic/pointer/muzzle/bipod):

  ```
  python tools/init_mod.py 1234567890 --kinds weapons          # skip the helmets
  python tools/init_mod.py 1234567890 --kinds primary,handgun  # and the launchers too
  ```

  You can always widen it later by editing `mod.yml` and re-running from step 5.
- **The short pack names.** They are derived from the PBO names (`foo_wp_ak` → `ak`). Rename any
  you find unclear — they only affect folder names inside your repo.
- **Which PBOs got skipped.** Do not trust PBO names over this scan. In BWMod, the PBO called
  `bwa3_weapons` holds *vehicle* armament and correctly gets skipped.

---

## Step 3a — If it says "no arsenal-visible item"

Three things cause this. Work through them in order.

**1. The mod extends another mod.** Its items inherit across the boundary:

```
BWAdd_G36A1   parent='BWA3_G36A1'   scope=None
```

Both the parent class and the `scope` live in the *other* mod, so scanned alone nothing resolves.
Re-run naming the mod it extends:

```
python tools/init_mod.py 1234567890 --requires 1200127537 --prefix aceaxfoo --model-prefix foo
```

That mod gets dumped so inheritance resolves, and is marked `resolve_only: true` in `mod.yml` so its
own items are never treated as yours.

**If you already have a compat for the parent mod, fold the add-on into it instead** — run
`python tools/init_mod.py <addon id> --add` in that repo and paste the block it prints. Items
sharing a display-name base merge into one entry, so an add-on's retextures become an extra camo
value rather than a duplicate set of rows. Two separate addons cannot do that: only one can usefully
map a given class. See WORKFLOW.md §3b.

**2. Everything the mod ships is hidden from the arsenal.** `scope = 0`, or `scopeArsenal` set to
something other than 2. Nothing to do; the mod is not arsenal content.

**3. Neither of the above.** Config root names are read case-insensitively, so a mod writing
`class cfgWeapons` is handled — but if a mod does something stranger still, dump it by hand and
look:

```
python tools/dump_configs.py
python -c "import json,glob; [print(f, list(json.load(open(f)))) for f in glob.glob('_dump/*.json')]"
```

You should see `CfgWeapons`, `CfgVehicles` or `CfgGlasses` in some spelling. If you see none of
them, there is no arsenal content in that PBO.

---

## Step 4 — Create the scaffold files

`init_mod.py` writes only `mod.yml`. These six you create yourself — the repo you cloned in Step 1
has one of each to copy, and the values to change are marked below.

**`.hemtt/project.toml`**

```toml
name = "ACEAX FooMod Compat"
prefix = "aceaxfoo"
author = "You"
template = "cba"
mainprefix = "z"
sig_version = 3

[version]
major = 1
minor = 0
patch = 0
git_hash = 0

[files]
include = ["mod.cpp"]
exclude = ["*.psd", "*.png", "*.tga"]
```

**`.hemtt/launch.toml`** — lets `hemtt launch` start Arma with the right mods:

```toml
[default]
workshop = [
    "450814997",   # CBA_A3
    "463939057",   # ACE3
    "2522638637",  # ACE3 Arsenal Extended
    "1234567890"   # FooMod
]
parameters = ["-skipIntro", "-noSplash", "-showScriptErrors", "-filePatching", "-noPause"]

[arsenal]
extends = "default"
parameters = [
    "-init=playMission['','\\z\\ace\\addons\\arsenal\\missions\\Arsenal.VR']"
]
```

**`mod.cpp`**

```cpp
name = "ACEAX FooMod Compat";
dir = "@aceaxfoo";
author = "You";
description = "ACE3 Arsenal Extended compatibility for FooMod";
```

**`addons/main/$PBOPREFIX$`** — one line, no extension, and the `$` are part of the filename:

```
z\aceaxfoo\addons\main
```

> Create that one with a text editor. `\a` is the BEL escape character, so writing it from the
> shell with `printf 'z\\aceaxfoo\\addons\\main'` silently produces `z<BEL>ceaxfoo<BEL>ddons\main`
> and `hemtt build` then fails with a confusing `failed to create directory` error.

**`.gitignore`** and **`LICENSE`** — copy both unchanged out of the repo you cloned in Step 1.

> `addons/main/config.cpp` and everything under `addons/main/XtdGearModels/` and `XtdGearInfos/`
> are **generated**. Never create or edit those by hand; they get overwritten.

---

## Step 5 — Dump the mod's configs

```
python tools/dump_configs.py
```

Extracts and decodes each pack listed in `mod.yml` into `_dump/`. Slow the first time, instant
afterwards — it skips packs already done. `_dump/` is gitignored; it is a cache, not source.

---

## Step 6 — See what you are working with

```
python tools/report.py
```

```
pack                  items   p3ds  kinds
g36                      33     11  primary 33
helmets                  40      2  headgear 40
p8                        1      1  handgun 1
TOTAL                    74     14  handgun 1, headgear 40, primary 33
```

Check the `kinds` column against what you expect. A gear mod reporting nothing but headgear usually
means a pack is missing from `mod.yml`, not that it ships no vests.

Then look at how the mod names its variants — this is the thing everything else depends on:

```
python tools/report.py --bases
```

```
  [primary/g36] G36A1   (3)
        FOO_G36A1                          -
        FOO_G36A1_green                    Green
        FOO_G36A1_tan                      Tan
```

The right-hand column is the `(marker)` from each item's in-game name. Most mods write variants as
`<Base> (<Colour>)`, and that convention is what the grouping is built on.

If this output shows no markers at all and every item has a unique base name, the mod does not
follow the convention and this toolchain will not help much — worth finding out now.

---

## Step 7 — Generate a starter `tools/overrides.yml`

```
python tools/init_overrides.py
```

```
wrote tools/overrides.yml
  74 items, 12 distinct token(s)
  4 auto-mapped to camo, 8 left as TODO
```

`overrides.yml` is the file you actually author — it holds every judgement call. The starter version
fills in what can be derived:

- **`tokens:`** — every marker the mod uses. Colour words are matched against ACEAX's own palette
  and mapped for you; the rest are parked on a `variant` axis and tagged `TODO`.
- **`camo_values_from_aceax:`** — read live from your installed ACEAX, not hand-copied.
- **`bases:`, `weapons:`, `positional_axes:`** — left empty. Those are steps 8 to 10.

It may also warn that some tokens appear in more than one capitalisation. Token matching is
case-**sensitive** on purpose — NIArms means a rail kit by `TAC` and a receiver configuration by
`Tac` — so if a mod is just inconsistent with itself, give each spelling its own line pointing at
the same value.

It already produces a valid config, just an under-grouped one. That is a fine place to start.

---

## Step 8 — Group the families

This is the part that needs you. Base names alone will not know that `G36KA0` and `G36A3` are the
same rifle, or that `Airframe 01` and `Airframe 01 + Goggles` are the same helmet.

```
python tools/report.py --families
```

It prints a summary and writes the detail to `_dump/families.yml`, because on a large mod this runs
to hundreds of lines:

```
  [primary/g36]    6 bases  "G36"
  [headgear/helmets]  12 bases  "Airframe"
  ... 4 more

  6 candidate family/families -> _dump/families.yml
```

Open that file. It is valid YAML, ready to paste from:

```yaml
bases:
  # ---- [primary/g36] 6 bases sharing "G36" ----
  "G36A1":  {as: "G36"}   # differs by: A1
  "G36A2":  {as: "G36"}   # differs by: A2
  "G36KA0": {as: "G36"}   # differs by: KA0
```

The **"differs by"** comment tells you what the dropdowns should be. Here the difference is barrel
length (plain vs K) and generation (A0–A4), so copy the block into `bases:` in `overrides.yml` and
add those axes:

```yaml
bases:
  "G36A1":  {as: "G36", barrel: RIFLE, variant: A1}
  "G36A2":  {as: "G36", barrel: RIFLE, variant: A2}
  "G36KA0": {as: "G36", barrel: K,     variant: A0}
```

Every base name mapped to `as: "G36"` collapses into one arsenal row, with `barrel` and `variant`
as its dropdowns.

If you would rather not copy by hand, `python tools/report.py --families --write` inserts the
proposals into `overrides.yml` for you, keeping your comments intact — then you just add the axes.

Pasted without axes, a block merges its bases into one entry with nothing to tell them apart. The
generator reports that as `no distinguishing option` and skips the group; it is a prompt, not an
error.

Suggestions err towards over-merging — deleting a line you disagree with is quicker than noticing a
family that was missed. Re-run it as you go; bases you have already handled are skipped, so a second
run never duplicates anything. Clustering is per arsenal tab, so a helmet is never proposed as
family with a vest.

**Grenade launchers:** give them their own entry rather than a dropdown value. A rifle and the same
rifle with a launcher underneath are not the same weapon. If the mod puts `GL` in the marker, list
it under `splitters:`; if it is part of the base name, point it at a separate entry with
`{as: "G36 (GL)"}`.

**Gear accessories go the other way.** A helmet with goggles pushed up, or a plate carrier with a
battle belt, is still the same item — so make those dropdown values:

```yaml
bases:
  "Airframe 01":           {as: "Airframe", variant: V01, goggles: PLAIN}
  "Airframe 01 + Goggles": {as: "Airframe", variant: V01, goggles: GOGGLES}
```

Neither call is forced by the tooling. Pick whichever makes the arsenal easier to use.

### When the distinction is not in a `(marker)` at all

`bases:` can express anything, but if a mod is *systematically* awkward you will be writing a line
per item. Four tables cover the usual shapes — one line each covers a whole family. Full syntax and
worked examples are in [OPTIONS.md](OPTIONS.md); this is the map of which to reach for:

| the mod writes… | example | use |
|---|---|---|
| the distinction on the **front of the display name** | `[Mod] AOR1 LBT6094 (Gunner)` | [`name_prefixes:`](OPTIONS.md#name_prefixes) |
| nothing distinguishing at all — only the **class name** differs | 13 classes all called `LA-5B` | [`class_prefixes:`](OPTIONS.md#class_prefixes-and-class_suffixes) / `class_suffixes:` |
| the item **and everything bolted to it** in one name | `Micro T-2/Leap/G33/LT 5/8` | [`compose:`](OPTIONS.md#compose) |
| a marker the parser cannot see — `[...]`, or no space before `(` | `Helmet Lite [OD]` | `compose.suffixes:` |

The second is the one that *blocks* generation rather than merely looking untidy: identical names
land on the same option combination, and `--check` refuses, reporting pairs that *"both map to"* the
same values. That is deliberate — ACEAX keys a HashMap on the tuple, so duplicates overwrite each
other and a dropdown click could hand the player an item they cannot use.

Gear mods hit the first row constantly, with camo: one vest written across fifteen camo patterns is
fifteen rows until the prefix is cut out.

---

## Step 9 — Classify the leftover tokens

Every `TODO` in `tokens:` needs an axis. The ones already in use across the existing compats:

| axis | for |
|---|---|
| `camo` | finish and colour — needs no label, ACEAX supplies them |
| `pantscamo` | a second colour on the same item, for a uniform's trousers — also label-free |
| `barrel` | barrel length |
| `mount` | rails and optic mounts |
| `variant` | generation, sub-model, or a helmet's model number |
| `receiver` | a second orthogonal model axis |
| `condition` | worn / clean |
| `caliber` | chambering |
| `role` | a vest's loadout |
| `belt`, `goggles`, `accessory`, `panel` | attached gear |
| `mount`, `beam`, `magnification`, `reticle`, `length` | attachments — see [OPTIONS.md](OPTIONS.md) |

Any axis other than `camo` and `pantscamo` also needs an entry under `options:`, a place in
`option_order:`, and a shared class under `option_bases:` giving each value a label. The starter
file shows the shape.

> Value names become config class names, so they must start with a letter — `V01`, not `01`. And
> avoid `YES`/`NO`/`ON`/`OFF` as YAML keys; those parse as booleans. `PLAIN`/`FITTED` reads better
> anyway.

**Two colours in one marker.** If the mod writes something like
`Fleece + G3 Field Pants (GREY+3CD)` — one colour for the top, another for the trousers — `+`
splits the marker and

```yaml
positional_axes: [camo, pantscamo]
camo_axes: [camo, pantscamo]
```

puts the first token on `camo` and the second on `pantscamo`, whatever axis the token table gave
them. `camo_axes:` is what makes the generator check both resolve to a real swatch. Leave both at
their defaults unless the mod actually does this.

---

## Step 10 — Generate, and fix what it reports

```
python tools/gen_aceax.py --check --list
```

`--check` writes nothing, so run it as often as you like. It prints every model with its arsenal
tab and dropdowns, and refuses to proceed on three problems:

| message | fix |
|---|---|
| `X and Y both map to A+B` | two items landed on the same combination — add an axis, or a `weapons:` override |
| `spans arsenal tabs` | a model mixes two tabs — a pistol with a rifle, or a helmet with a vest. Split it in `bases:` |
| `camo value 'X' has no CamoBase entry` | add it under `camo_values:` |

Full list in [WORKFLOW.md](WORKFLOW.md) §4. Loop between editing `overrides.yml` and re-running this
until it is clean and the model list looks right.

---

## Step 11 — Build and verify

```
python tools/gen_aceax.py     # write the config for real
hemtt build                   # -> .hemttout/build
python tools/verify.py        # validate the built pbo
```

`verify.py` reads the **built** PBO, so it must run after `hemtt build`. It applies the same rules
ACEAX applies at runtime, per config root, plus checks every mapped class is a real arsenal item.

Then confirm nothing was lost:

```
python tools/report.py --coverage
```

```
TOTAL  74 items = 65 behind 8 entries + 9 standalone
```

Every item must appear exactly once. "Standalone" means it had no sibling to group with, which is
normal and not a failure.

### The one warning that is not cosmetic

`verify.py` may report **"N variants reachable only via the weak-match fallback"**. The count tells
you which kind it is:

- **A handful** usually means the mod simply does not ship every combination — a sparse grid. Those
  work in practice; they just cannot be *proven* from the config. Move on.
- **A large fraction of an entry** means two axes are **coupled**: one only takes a value when the
  other does. ACEAX changes one option per click, so nothing can cross between the two halves, and
  clicking a dropdown falls through to a HashMap lookup whose order Arma does not guarantee — the
  player gets an item you did not pick for them.

The fix for the second is to **split the entry**, not to merge harder. Look for an axis whose values
never co-occur with another's; [OPTIONS.md](OPTIONS.md) has the worked example.

Before merging two things into one entry, it is worth asking whether every combination of the axes
actually exists in the mod. If the answer is "no, and the missing ones are systematic", that is the
same coupling seen from the other side.

---

## Step 12 — Test it in the game

```
hemtt launch arsenal
```

In the debug console:

```sqf
diag_log ([] call aceax_gearinfo_fnc_diag_detectErrors);
```

Must print `0`. Then open the arsenal and click through a grouped entry on each tab you cover, to
check the dropdowns actually reach every variant.

Optionally confirm your offline dump matches what Arma really loaded:

```
python tools/check_ingame.py --sqf     # paste the output into the debug console
python tools/check_ingame.py           # then compare
```

---

## Step 13 — Publish

Write a `WorkshopDesc.md` (the one in the cloned repo shows the shape), then publish
`.hemttout/build` with the Arma 3 Launcher's *Publish* tool. Set CBA, ACE3, ACE3 Arsenal Extended
and the source mod as required items.

---

## The whole thing, in order

```
git clone https://github.com/AtrixZockt/AceArsenalExtended-Attachments
mkdir AceArsenalExtended_Foo && cd AceArsenalExtended_Foo
cp -r ../AceArsenalExtended-Attachments/tools .

python tools/init_mod.py 1234567890 --prefix aceaxfoo --model-prefix foo --author "You"
#      ... create the scaffold files from step 4 ...
python tools/dump_configs.py
python tools/report.py --bases
python tools/init_overrides.py
python tools/report.py --families
#      ... edit tools/overrides.yml -- steps 8 and 9 ...
python tools/gen_aceax.py --check --list     # repeat until clean
python tools/gen_aceax.py
hemtt build
python tools/verify.py
python tools/report.py --coverage
hemtt launch arsenal
```

---

## Afterwards

[WORKFLOW.md](WORKFLOW.md) covers the day-to-day: the edit loop, what to do when the source mod
updates, and what every warning means. **§3c** is the reference for gear compats — `kinds:`, the
three config roots, and how an item's arsenal tab is determined.
