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
| `length` | suppressor / barrel length | `SHORT`, `LONG` |
| `cover` | lens caps, killflash | `NONE`, `KILLFLASH`, `CAPPED` |

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
