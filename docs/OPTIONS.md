# Option vocabulary for attachment compats

The interop contract. Independently-written compats that follow it produce arsenals that read
consistently; ignoring it costs correctness nothing but makes every mod feel different.

## What actually has to be unique, and what does not

Two things are easy to confuse:

| | scope | must be unique? |
|---|---|---|
| **option name** — `camo`, `mount`, `beam` | the key in `options[]` and in `XtdGearInfos` | **No.** Values live per model, so two compats both using `mount` never collide. |
| **option base class** — `niarms_mount` | a class under `XtdGearModels` | **Yes.** Arma merges same-named config classes across addons, so two compats defining `mount` differently would blend. |
| **model class** — `t1a_optic_la5` | a class under `XtdGearModels >> CfgWeapons` | **Yes.** Prefix it with your `model_prefix`. |

So: **share the option names, namespace the classes.** In `overrides.yml` that means the key on the
left is from the list below, and `class:` on the right carries your prefix:

```yaml
option_bases:
  mount:
    class: t1a_mount        # <- your model_prefix, not "mount"
    label: "Mount"
    values:
      SIDE: {label: "Side rail"}
      TOP:  {label: "Top rail"}
```

## The vocabulary

### Conventional — do not define these

`camo` and `pantscamo` are ACEAX conventions. They resolve through
`XtdGearModels >> Conventional >> camo` → `CamoBase` and inherit their label, icon and swatches, so
they need **no** `base:` and no `option_bases:` entry. Only `pantscamo` is gear-specific;
`camo` applies to attachments as much as anything else.

```yaml
options:
  camo: {default: STD}
```

Extra colours go in `camo_values:` and merge into the shared palette. Check
`camo_values_from_aceax:` first — ACEAX ships around 52.

### Recommended names

| option | for | typical values |
|---|---|---|
| `camo` | colour or finish | `BLK`, `FDE`, `TAN`, `RGR` (conventional) |
| `variant` | generation or sub-model where nothing more specific fits | `A1`, `V01`, `GEN2` |
| `mount` | how it attaches | `SIDE`, `TOP`, `OFFSET`, `LOWMOUNT`, `RISER` |
| `beam` | laser / illuminator mode | `IR`, `VIS`, `IRCOMBO`, `WHITE` |
| `magnification` | fixed or variable power | `X1`, `X4`, `X1_6`, `X3_12` |
| `reticle` | reticle pattern | `MILDOT`, `HORUS`, `CIRCLEDOT` |
| `display` | how the scope is drawn | `PIP`, `FLAT` |
| `length` | suppressor / barrel length | `SHORT`, `LONG` |
| `cover` | lens caps, killflash | `NONE`, `KILLFLASH`, `CAPPED` |
| `platform` | which weapon the copy is cut for | `P10`, `P416`, `PMCX` |
| `magnifier` | magnifier stacked behind a red dot | `NONE`, `3X`, `G33` |
| `riser` | riser the optic or magnifier sits on | `NONE`, `LT58`, `UTG350` |
| `piggyback` | second optic mounted on the first | `NONE`, `DOCTER`, `MICROT2` |
| `light` | weaponlight bolted to a laser unit | `NONE`, `M300C`, `M600V` |
| `grip` | foregrip bundled with the item | `NONE`, `RVG`, `KACVFG` |
| `ard` | anti-reflection device | `NONE`, `ARD` |

The last six all describe **something bolted onto the item**, and they exist because mods that ship
accessory stacks write the whole stack into one display name. They belong to
[`compose:`](#compose) below, and they all default to `NONE` — an unadorned Micro T-2 is genuinely a
Micro T-2 with no magnifier and nothing piggybacked, so the plain class is a real point in the grid
rather than a placeholder for one.

`display` covers a common case: mods routinely ship a picture-in-picture build and a cheaper flat
build of the same magnified optic. NIArms marks the flat one `(2D)` and leaves the PiP one
unmarked, which makes `PIP` the natural default.

`mount` does double duty and that is intended. On a weapon it means the rail kit fitted to it; on an
optic it means which rail the optic is cut *for* — NIArms ships the Kern AARAU 4x24 three times over
for the Stgw.57, FN30-11 and SG550. Values live per model, so the two uses never meet.

### `platform` — for mods that ship one accessory per weapon

Some mods duplicate every accessory once per weapon it can go on, with **identical display names**.
Tier One Weapons has 23 separate classes all called "LA-5B":

```
Tier1_10_LA5_Side   Tier1_145_LA5_Side   Tier1_416_LA5_Side   Tier1_MCX_LA5_Side   ...
```

Left alone that is not merely untidy — those classes land on the same option tuple, and
`getVariations` keys a HashMap on that tuple, so duplicates overwrite each other and clicking a
value can hand you an accessory the selected weapon cannot take. Across Tier One it produces **188**
such collisions.

Only the class name says which is which, so `platform` is derived with
[`class_prefixes:`](#class_prefixes) rather than from the display name.

**You will never see the dropdown.** Only one platform is ever compatible with the weapon in your
hands, so the arsenal narrows the axis to a single value and the extension hides options that cannot
be changed. `platform` exists purely to keep the config unambiguous.

## `class_prefixes:` and `class_suffixes:`

When the display name does not carry the distinction, take it from the class name. Both tables map a
fragment to `[axis, value]`; prefixes are anchored at the start, suffixes at the end, and both are
matched case-insensitively.

```yaml
class_prefixes:
  "Tier1_10_":    [platform, P10]
  "Tier1_416_":   [platform, P416]
class_suffixes:
  "_BlackDesert": [camo, BLKDSRT]
```

They are applied after display-name tokens and before per-item `weapons:` overrides, so a class-name
rule beats a marker and a hand-written override beats everything.

The suffix table also has a second common use: **two-tone finishes**. A name like `(Black/Desert)`
splits on `/` into two tokens that both land on `camo`, and the last one wins — quietly making the
item a duplicate of its single-colour sibling. The class name (`..._BlackDesert`) is unambiguous
where the display name is not, and one suffix line fixes the whole family.

## `compose:`

For mods that write an item **and everything bolted to it** into one display name. Tier One does
this throughout:

```
Micro T-2/Leap/G33/LT 5/8        optic + mount + magnifier + riser
M4BII // LA-5B/M600V (Tan)/alt   platform + laser + weaponlight + colour + variant
```

Without it every combination is its own arsenal row. Tier One's Micro T-2 alone spans thirteen, and
148 of its 186 base names contain a `/`.

**Splitting on the separator does not work**, which is the whole reason this is a vocabulary and not
a `split()`. Component names contain the separator themselves — `LT 5/8`, `UTG 3/50`, `AN/PVS-10`,
`SpecterDR 1.5x/6x`. Parts are matched longest-first and only where the separator immediately
precedes them, so those survive intact.

```yaml
compose:
  separator: "/"
  platform_separator: " // "     # drop a "HOST // item" prefix; optional
  suffixes:
    "[2D]": [display, FLAT]      # markers parse_display_name cannot see; optional
  parts:
    "3X":        [magnifier, 3X]
    "LT 5/8":    [riser, LT58]
    "Low Mount": [mount, LOWMOUNT]
```

`suffixes:` matches a literal string at the end of the name, for bracket styles the parser does not
recognise — it handles `(...)` and `{...}`, not `[...]`. These are worth checking for early: a
trailing `[2D]` does not just strand those variants on their own rows, it sits at the end of the name
and blocks every part behind it from ever being reached.

`platform_separator:` drops the prefix rather than mapping it, on the assumption that
[`class_prefixes:`](#class_prefixes) supplies the same fact from the class name — where it is present
for *every* item, not only the ones that spell it out. Confirm that 1:1 mapping before relying on it.

### Where it stops, deliberately

A bracket marker standing between the base and a part is stepped over **speculatively**: the step is
kept only if it exposes another part. `LA-5B/M600V (Tan) (Laser)` needs the colour off before
`/M600V` is reachable, so the step pays for itself and is kept. `HK416 D10 (SMR/CTR) (Desert)` has
nothing composed after it, so the step is reverted and the base stays `HK416 D10 (SMR/CTR)`.

That conditional is what lets a weapon half and an attachment half share one overrides file. The
consequence to know about is that **a marker with nothing composed after it stays put**, so the same
item can arrive under two spellings — `Romeo4T (BCD)` and `Romeo4T (BCD)/G33`. Map the bare spelling
in [`bases:`](#bases):

```yaml
bases:
  "Romeo4T (BCD)": {as: "Romeo4T", reticle: BCD}
```

Parts are anchored to the *end* of the name, so anything written on the front — a foregrip in
`RVG/Harris Bipod` — also belongs in `bases:`.

### When a part should be a separate row instead

Watch for an axis that only means anything when another axis is set. Tier One's colour marker
describes the *weaponlight*, not the laser, so a bare LA-5B carries no marker at all:

```
light=NONE   camo=STD          31 classes
light=M600V  camo=TAN | BLK   146 classes
```

The two are perfectly coupled, and ACEAX changes **one option per click**, so nothing can cross that
gap: clicking "M600V" on a bare LA-5B finds no exact tuple, falls through to `findConfigByValue`,
and returns the first match in HashMap order — very likely another platform's class. `verify.py`
catches this as *"N variants reachable only via the weak-match fallback"*, and a large count there is
the signal to split rather than to merge harder. Tier One splits into `LA-5B` and `LA-5B + Light`,
which is also the truer description.

`beam` is the one worth being careful with. Mods name laser modes wildly differently — MCC writes
`IR-Laser`, `IR-Combo Close`, `IR-Combo Far`; Tier One writes `Laser` and `Light` — but they mean
much the same things, and mapping them onto one option name is what stops every compat inventing
its own.

Value **names** are config class names, so they must start with a letter and contain no spaces:
`X1_6`, not `1.6x`. The human-readable form goes in `label`.

### Prefer an option over a separate entry

The weapon compats give a mounted grenade launcher its own arsenal row, because it changes what the
weapon *is*. Attachments almost never warrant that: an optic with a killflash is the same optic. Fold
it into a dropdown unless the variants genuinely behave differently.

The one real exception is a **combination** item — an LA-5 with an M600V light attached is arguably
not the same accessory as a bare LA-5. Tier One's naming already separates them
(`LA-5B` vs `LA-5B/M600V (Tan)`), so following the display names gets this right for free.

### Do not group across slots

`find_mixed_kinds` blocks it, and it would be wrong anyway: an optic and a muzzle device appear on
different right-panel tabs, so a model spanning both would hide half its members where they cannot
be reached. If a mod's naming pushes you that way, split with `as:` in `bases:`.

## Magazines

Deliberately out of scope. They use the same right-panel machinery and would be easy to add, but
different ammunition is a functional difference rather than a cosmetic one — hiding tracer, subsonic
or AP loads behind a dropdown would misrepresent what the player is picking.

## If you need a name that is not here

Use it, and open an issue. The list grows by what compats actually need; the point is that the
second person to need "mount" finds it already spelled that way.
