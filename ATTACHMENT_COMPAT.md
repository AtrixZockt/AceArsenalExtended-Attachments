# Building an attachment compat

How to make a weapon mod's attachments collapse into dropdowns. Assumes no prior knowledge of this
toolchain.

The example throughout is **Tier One Weapons** (Workshop `2268351256`), which ships 541
arsenal-visible attachments that fold into 186 rows.

---

## What you are building

Two separate things, and it matters that they stay separate:

| | what it is | who needs it |
|---|---|---|
| **this addon** (`@aceaxatt`) | the runtime — teaches the arsenal's right panel to collapse | everyone who wants attachment merging |
| **your compat** | config data saying which attachments are variants of which | anyone using the mod you patched |

Your compat does **not** depend on this addon. Its data is inert without it — nothing in ACEAX
reads attachment `XtdGearInfos` — so players without the extension see the arsenal exactly as they
do today, and nothing errors.

That means your `CfgPatches` keeps only:

```cpp
requiredAddons[] = {"aceax_gearinfo"};
```

Do **not** add `aceaxatt_main` there. If you did, and a player did not have this addon, Arma would
throw *"Addon 'yourcompat_main' requires addon 'aceaxatt_main'"* at startup. Instead list this mod as
a Workshop **required item**, which is launcher-level: it auto-subscribes users without ever
hard-failing the game.

---

## Before you start

| | |
|---|---|
| [HEMTT](https://github.com/BrettMayson/HEMTT) 1.19+ on `PATH` | `hemtt --version` |
| Python 3.9+ with PyYAML | `python -c "import yaml"` |
| Subscribed in Steam | CBA_A3, ACE3, ACE3 Arsenal Extended, and the weapon mod |

---

## Step 1 — Copy the toolchain

```
mkdir E:/GitHub/AceArsenalExtended_Tier1Att
cd    E:/GitHub/AceArsenalExtended_Tier1Att
cp -r ../AceArsenalExtended_Attachments/tools .
```

The `.py` files carry no mod identity. Everything specific to your mod lives in the two YAML files
you are about to generate.

## Step 2 — Scan the mod

```
python tools/init_mod.py 2268351256 --prefix aceaxt1a --model-prefix t1a --author "You" --kinds attachment
```

```
Tier One Weapons  (4 pbos) -- derapifying, this takes a minute

  Tier1_Weapons_cfg    659 item(s)  [bipod 21, muzzle 34, optic 178, pointer 308, primary 118]
                           (3 other pbo(s) skipped)

wrote tools/mod.yml
  kinds: optic, pointer, muzzle, bipod
```

`--kinds attachment` is what restricts the compat to the four right-panel slots. Drop it and you get
the weapons too — see *Covering weapons as well* below.

**Pick a `prefix` and `model_prefix` nobody else uses.** They become your PBO name, `CfgPatches`
class and every generated model class. Two compats sharing one would blend into each other.

## Step 3 — The scaffold

`init_mod.py` writes only `mod.yml`; it prints the rest. Copy them from any existing compat and
change the marked values: `.hemtt/project.toml`, `.hemtt/launch.toml`, `mod.cpp`, `.gitignore`,
`LICENSE`, and `addons/main/$PBOPREFIX$` containing `z\<yourprefix>\addons\main`.

> Write `$PBOPREFIX$` with a text editor. `\a` is the BEL escape, so
> `printf 'z\\aceaxt1a\\addons\\main'` silently writes `z<BEL>ceaxt1a<BEL>ddons\main` and `hemtt
> build` then fails with a baffling *failed to create directory* error.

## Step 4 — Dump and look

```
python tools/dump_configs.py
python tools/report.py
python tools/report.py --bases
```

`--bases` is the important one. It shows how the mod's display names cluster, which is the entire
basis of the grouping:

```
  [pointer/weapons_cfg] LA-5B/M600V (Tan)   (22)
        Tier1_10_LA5_M600V                Laser
        Tier1_10_LA5_M600V_FL             Light
        ...
```

If every attachment has a unique base name and no `(marker)`, the mod does not follow the
convention and this toolchain will not help much. Better to find that out now.

## Step 5 — Starter overrides

```
python tools/init_overrides.py
```

Fills in what is derivable: every marker the mod uses, with colour words auto-matched against
ACEAX's palette and everything else parked on a `variant` axis marked `TODO`.

## Step 6 — Group

```
python tools/report.py --families
```

Clusters base names by shared stem and writes candidates to `_dump/families.yml`, with a
*"differs by"* comment on each line telling you what the dropdown should be. Paste the blocks you
agree with into `bases:` and add the axes, or use `--families --write` to insert them for you.

**Read [OPTIONS.md](OPTIONS.md) before naming your axes.** Attachment compats will be written by
different people against different mods; using the same names for the same concepts is what stops
the arsenal feeling like a patchwork.

## Step 7 — Generate, build, verify

```
python tools/gen_aceax.py --check --list   # iterate until clean
python tools/gen_aceax.py
hemtt build
python tools/verify.py
python tools/report.py --coverage
```

`--check` blocks on three things: two attachments landing on the same option combination, a model
spanning two arsenal tabs, or a camo value with no swatch. [WORKFLOW.md](WORKFLOW.md) §4 lists every
message.

`--coverage` ends in a reconciliation line — every attachment must appear exactly once, behind an
entry or as a standalone row.

## Step 8 — Test it

```
hemtt launch arsenal
```

In the debug console:

```sqf
diag_log ([] call aceax_gearinfo_fnc_diag_detectErrors);   // must print 0
```

Then open the arsenal, select a weapon, open the optic tab, and check that a family shows one row
with working dropdowns. [TESTING.md](TESTING.md) has the full checklist, including the cases that
are easy to get wrong.

Worth checking explicitly: **select a weapon that only takes some of a family's variants.** The
dropdown should offer only those, and the family should still appear. That falls out of the design
rather than needing anything from you, but it is the behaviour most worth confirming.

---

## Covering weapons as well

Nothing stops one compat doing both — drop `--kinds attachment` and it covers whatever the scan
finds:

```yaml
kinds: [primary, handgun, launcher, optic, pointer, muzzle, bipod]
```

The weapon half works with plain ACEAX; the attachment half needs this extension. Both live in one
addon and degrade independently.

**But check whether a weapons compat already exists for that mod.** ACEAX ships official compats for
RHS, CUP, USP, AMF, ACE-BI and Tier One in its `optionals/` folder, and there are community ones
too. If one does:

- an **attachments-only** compat layers on top of it cleanly — the two map disjoint sets of classes
  and never meet;
- an **all-in-one** compat conflicts with it — both would define
  `XtdGearInfos >> CfgWeapons >> <the same weapon>`, Arma merges same-named config classes, and the
  result can take its `model` from one and its option values from the other.

So an all-in-one build has to be documented as *mutually exclusive* with the existing compat. The
attachments-only build has no such caveat, which is usually reason enough to prefer it.

Check for a collision offline before ever launching the game:

```
# their mapped classes
hemtt utils pbo extract <their.pbo> config.bin their.bin
hemtt utils config derapify -f json their.bin their.json
# yours
python tools/report.py --coverage --csv
# the two class lists must not intersect
```

---

## Keeping up with the source mod

```
python tools/dump_configs.py --force
python tools/gen_aceax.py --check
```

New variants surface as `unmapped displayName token(s)`. Add them to `tokens:`, re-run, and read the
file diff — it tells you exactly which entries changed.
