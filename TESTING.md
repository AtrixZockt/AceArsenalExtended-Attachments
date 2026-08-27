# Testing

What this addon has to get right, and how each thing is checked.

The first group matters most: the addon touches the ACE arsenal UI, so *not changing anything for
people who are not using it* outranks the feature itself.

---

## 1. It changes nothing on its own

Run `hemtt launch baseline` — CBA + ACE + ACEAX + this addon, no compat, no weapon mod.

| check | expected |
|---|---|
| Right panel, optic tab | every optic listed individually, exactly as stock ACEAX |
| `diag_log ([] call aceax_gearinfo_fnc_diag_detectErrors);` | `0` |
| Left panel grouping | unchanged — pick any ACEAX compat and confirm its dropdowns still work |
| RPT on load | no errors mentioning `aceaxatt` |
| Equipping an attachment | works; weight readout updates |

This should hold structurally, not just empirically: the addon writes no ACE or ACEAX global. If
something here fails, the cause is the config merge on `rightTabContent`, not the collapse logic.

## 2. The kill switch

CBA Settings → *ACE Arsenal Extended* → *Merge weapon attachments* → off.

With a compat loaded, the arsenal must become indistinguishable from having the addon absent. No
restart. This is the escape hatch if an ACE update ever breaks the fork.

## 3. Toolchain is a no-op on existing compats

The `tools/` here are the same generator the NIArms, BWmod and Military Gear Pack compats use, with
attachment kinds added. Generating those three with these tools must produce byte-identical output
to generating them with their own:

```
python tools/gen_aceax.py     # in a copy of each repo
diff -r old/addons new/addons  # must be empty
```

Verified: identical for all three. A compat with no `kinds:` line means weapons only, so attachment
support cannot leak into an existing repo.

---

## 4. Tier One Weapons — the real test

**Tier One Weapons** (`2268351256`) is the proving ground, because it is the one mod that lets both
layering models be compared directly:

- **541 arsenal-visible attachments** — bipod 21, muzzle 34, optic 178, pointer 308 — the largest
  measured, folding to about 186 rows;
- ACEAX already ships **`@aceax_compat_tier1`** in its `optionals/` folder, covering that mod's
  **weapons only**: 15 models, 139 classes, and zero attachments.

Two compats get built against it. **They are mutually exclusive at runtime.**

### Scenario A — modular: attachments-only, layered on the official weapons compat

The important one. It is the proof that a third party can add attachment support to a mod that
already has a weapons compat, without touching or forking it.

```
CBA + ACE + ACEAX core + @aceax_compat_tier1 + Tier One Weapons
    + @aceaxatt + our Tier One attachments compat
```

| check | expected |
|---|---|
| Left panel | weapons merged by the official compat, unchanged |
| Right panel | attachment families merged by ours |
| `diag_detectErrors` | `0` — proves no conflicting `XtdGearInfos` entries |

**Offline pre-check, before ever launching.** The two compats must map disjoint class sets, or
`XtdGearInfos >> CfgWeapons >> <class>` entries merge into nonsense:

```
hemtt utils pbo extract <aceax_compat_tier1.pbo> config.bin t1.bin
hemtt utils config derapify -f json t1.bin t1.json
python tools/report.py --coverage --csv          # ours
# intersect the two class lists -- must be empty
```

Also confirm the two do not share option-base class names (your `model_prefix` must differ from
theirs) and that the only class they share is `XtdGearModels >> CamoBase`, which every compat is
*meant* to merge into.

### Scenario B — all-in-one: weapons and attachments in one compat

```
CBA + ACE + ACEAX core + Tier One Weapons + @aceaxatt + our full Tier One compat
    (WITHOUT @aceax_compat_tier1)
```

Everything merged by ours, including the weapon rows the official compat would have handled.

### The collision, deliberately

Load **both** the all-in-one compat and `@aceax_compat_tier1`. Both define
`XtdGearInfos >> CfgWeapons >> Tier1_<weapon>` for the same classes; Arma merges same-named config
classes, so a weapon can take its `model` from one and its option values from the other.

Do this once on purpose, record the symptom, and state the exclusivity plainly in the all-in-one
build's Workshop description. Knowing what the failure looks like is worth more than assuming it
cannot happen.

### What this settles

Whether attachment support can be **layered** onto an existing compat, or whether covering a mod
means owning all of it. A working Scenario A is the stronger outcome and the one this addon is
designed for; B is the fallback for mods with no compat at all.

---

## 5. Behaviour, once a compat is loaded

| # | check | why it can break |
|---|---|---|
| 1 | An optic family shows one row with dropdowns | the core feature |
| 2 | Picking a value equips the right class, weight updates | `changeCurrentConfig` re-enters ACE's handler rather than equipping directly |
| 3 | **Per-weapon compatibility** — select a weapon taking only some of a family; the dropdown offers only those, family still visible | this is *why* the collapse happens after the fill instead of filtering `virtualItems` |
| 4 | **Selection restore** — equip a non-representative variant, switch tabs, come back; it is still selected | the equipped item must be the row that survives, or ACE falls back to `<empty>` and it looks unequipped |
| 5 | **Both panels at once** — grouped weapon on the left, grouped optic on the right | the two option panels use separate IDC blocks; overlap would make them fight |
| 6 | Unmapped attachments keep their own rows | anything without `XtdGearInfo` must be passed through untouched |
| 7 | Switching weapon, then slot, then back | the collapse re-runs per fill; stale `allowedItems` would show wrong values |
| 8 | Container on the left (uniform/vest), attachments on the right | ACE lists *all* attachments there rather than compatible ones; nothing is equipped, so the "keep the equipped row" rule has no input |
| 9 | Scrollbar reaches the bottom row after the panel resizes | resizing a listbox does not refresh its scrollbar — there is a deferred re-commit for this |

Checks 3, 4 and 8 are the ones a naive implementation gets wrong.

---

## 6. Things that would break this addon

Worth knowing what to look at first when something does go wrong.

- **ACE renames or renumbers `rightTabContent` (idc 14), or changes its `onLBSelChanged`
  contract.** The constants live in `addons/main/defines.hpp`, copied from ACE because it ships
  binarised and there is no header to include. Symptom: the option panel never appears.
- **ACE moves `ace_arsenal_rightPanelFilled`** so it fires *after* the selection is restored rather
  than before. Symptom: check 4 fails first — attachments look unequipped.
- **ACEAX changes its IDC ranges** into ours. Symptom: check 5 — controls from one panel appear in
  the other.
- **ACEAX implements attachments itself.** The generated compat data should still be valid (same
  schema), but this addon would conflict and need to detect and stand down.
