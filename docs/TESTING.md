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

CBA Settings → *ACE Arsenal Extended* → *Merge attachments and magazines* → off.

With a compat loaded, the arsenal must become indistinguishable from having the addon absent. No
restart. This is the escape hatch if an ACE update ever breaks the fork.

## 3. Toolchain is a no-op on existing compats

`tools/` here is one generator serving every compat, so a change made for one mod must not silently
alter another. **Any change to `tools/*.py` is guarded the same way**, and it is the check to run
first — before worrying about whether the new feature works:

```
python tools/gen_aceax.py      # in a throwaway copy of each existing compat
diff -r old/addons new/addons  # must be empty
```

Run it in a *copy*, not in place; regenerating a compat you did not mean to touch is a poor way to
find out the guard would have failed.

This has held for every feature added so far — attachment kinds, `compose:`, `name_prefixes:`, the
vanilla gear and backpack fallbacks — because each is reachable only through a key the older compats
do not set, or only after the normal path has already failed. A compat with no `kinds:` line means
weapons only, so attachment support cannot leak into an existing repo either.

---

## 4. Two compats over one mod — the layering test

The question this settles is whether attachment support can be **layered onto a compat someone else
already wrote**, or whether covering a mod means owning all of it. It is the thing the addon is
designed for, so it is tested against real data rather than argued about.

**Tier One Weapons** (`2268351256`) is the vehicle, because someone else already covers half of it:

- **541 arsenal-visible attachments** — bipod 21, muzzle 34, optic 178, pointer 308 — the largest
  measured, folding to **47 rows**;
- ACEAX already ships **`@aceax_compat_tier1`** in its `optionals/` folder, covering that mod's
  **weapons only**: 15 models, 139 classes, and zero attachments.

So an attachments-only compat has to sit on top of a stranger's work and not collide with it.

```
CBA + ACE + ACEAX core + @aceax_compat_tier1 + Tier One Weapons
    + @aceaxatt + the Tier One attachments compat
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

Also confirm the two do not share option-base class names — your `model_prefix` must differ from
theirs.

### What it came out at

The resulting compat — published as **ACEAX Tier One Attachments** — builds clean: **541 attachments
→ 47 rows**, 38 entries plus 9 with no sibling, and **zero** weak-match warnings.

Getting there from 186 rows needed `compose:` — Tier One writes an optic and its whole accessory
stack into one name (`Micro T-2/Leap/G33/LT 5/8`), so every combination was its own row. See
[OPTIONS.md](OPTIONS.md).

The offline pre-check passed:

```
ours:   532 classes, 38 models        (532 not 541 -- the 9 standalone items get no XtdGearInfo)
theirs: 139 classes, 15 models
INTERSECTION: 0 classes, 0 models
```

Model classes are namespaced apart too — the official compat uses `tier1_`, ours `t1a_`. The two
configs have **no class in common at all**; the official compat does not even define `CamoBase`.

The judgement calls that got it there — deriving a `platform` axis from class names, two-tone
finishes, why the weaponlight is a separate row — belong to that compat and are written up in its
own README, not here. What matters for *this* addon is only that the data exercises it hard.

### The outcome

**It works, and it is the result worth having.** Attachment support can be layered onto a compat
written by someone else, without forking it or coordinating with its author — so a mod that already
has a weapons compat is not closed to further work.

The alternative shape — one compat owning a mod's weapons *and* attachments — also works and is the
right answer for a mod with no compat at all. The NIArms compat is exactly that: it covers both
halves, and its attachment data lies inert for anyone without this addon.

---

## 5. Behaviour, once a compat is loaded

| # | check | why it can break |
|---|---|---|
| 1 | An optic family shows one row with dropdowns | the core feature |
| 1a | **Clicking a different family changes the dropdowns on the FIRST click** | the click path must read the clicked row. `ace_arsenal_currentItems` is not written until the end of ACE's own handler, so reading it here shows the previous attachment — and picking a value from that stale panel silently re-equips the old one |
| 2 | Picking a value equips the right class, weight updates | `changeCurrentConfig` re-enters ACE's handler rather than equipping directly |
| 3 | **Per-weapon compatibility** — select a weapon taking only some of a family; the dropdown offers only those, family still visible | this is *why* the collapse happens after the fill instead of filtering `virtualItems` |
| 4 | **Selection restore** — equip a non-representative variant, switch tabs, come back; it is still selected | the equipped item must be the row that survives, or ACE falls back to `<empty>` and it looks unequipped |
| 5 | **Both panels at once** — grouped weapon on the left, grouped optic on the right | the two option panels use separate IDC blocks; overlap would make them fight |
| 6 | Unmapped attachments keep their own rows | anything without `XtdGearInfo` must be passed through untouched |
| 7 | Switching weapon, then slot, then back | the collapse re-runs per fill; stale `allowedItems` would show wrong values |
| 8 | Container on the left (uniform/vest), attachments on the right | ACE lists *all* attachments there rather than compatible ones; nothing is equipped, so the "keep the equipped row" rule has no input |
| 9 | Scrollbar reaches the bottom row after the panel resizes | resizing a listbox does not refresh its scrollbar — there is a deferred re-commit for this |

Checks 3, 4 and 8 are the ones a naive implementation gets wrong.

### Magazines

The magazine tabs run the same code with a different config root, so everything above applies to
them too. Four checks are specific to them:

| # | check | why it can break |
|---|---|---|
| 1 | Clicking a magazine adds **one**, not two | the addon's `LBSelChanged` handler runs *alongside* ACE's; if it ever equipped anything itself, magazines would double |
| 2 | Swapping via a dropdown adds one and removes none | `changeCurrentConfig` rewrites the row and re-enters ACE's handler — the same path, so the same risk |
| 3 | All four ammunition tabs collapse — current weapon's, secondary muzzle's, compatible, all | they are four separate IDCs; missing one leaves that tab flat with no error |
| 4 | Grenades, explosives, misc items and container contents are **untouched** | `fnc_currentPanelRoot` returns `""` for them; if it did not, the panel would collapse rows nothing has data for |

Check 1 is the one to run first. It is the failure mode the design is built to avoid — see the note
at the top of `fnc_onSelChangedRight.sqf` — and it is silent: nothing errors, you simply end up with
twice the ammunition you asked for.

---

## 5a. When the panel looks wrong — start here

Turn on **CBA Settings → ACE Arsenal Extended → Log right panel merging** and open the arsenal. Every
time the right panel fills, the RPT gets:

```
[aceaxatt] collapse: root=CfgWeapons leftPanel=2002 rightPanel=22 rows=14 equipped=hlc_optic_Kern_550
[aceaxatt]   row 1: optic_Aco -> 
[aceaxatt]   row 2: hlc_optic_Kern_550 -> niarms_fn3011_kern_aarau_4x24
[aceaxatt]   group niarms_fn3011_kern_aarau_4x24 -> rows [2,3]
[aceaxatt] collapse: deleting 1 of 14 rows
```

An unmapped attachment resolving to a blank model is correct and expected — it keeps its own row.
What is *not* expected is many unrelated classes resolving to the same model, which is the shape of
the first bug this addon shipped with.

`equipped=` is the class `fnc_equippedItem` read out of `ace_arsenal_currentItems`, and it is the
first thing to check when the panel shows the wrong variant. It is blank for the compatible-ammunition
tabs and whenever a container is selected on the left — both correct, those panels have no equipped
slot and fall back to the listbox row. A `row N rewritten to equipped X` line means ACE listed the
family under a different class than the one fitted, and the surviving row was reconciled to match.

### First check the RPT for a broken control

```
grep -iE "aceaxatt|updating base class|no type entry" <newest>.rpt
```

**`Updating base class 'X'->''`** naming this addon means a config patch has reset one of ACE's
classes and destroyed its inheritance. It is followed by `Warning: no type entry inside class ...`,
and the control renders as nothing. This is silent unless you go looking, and it is the single most
likely way this addon breaks — see below.

The addon deliberately adds **no** properties to any ACE-owned class; the only thing it contributes
to `ace_arsenal_display >> controls` is its own `aceaxatt_main_rightTabCustom`. If a grep of the
built config shows anything else, that is the bug.

### The first live failure, for reference

The first build emptied the right panel completely: no weapon had any selectable attachment, while
`diag_detectErrors` still returned 0. The config *data* was fine; so, it turned out, was the runtime
code — it never ran.

**The cause was one config block.** The addon patched a single property onto ACE's control:

```cpp
class rightTabContent { onLBSelChanged = "..."; };
```

Re-declaring an existing class without restating its parent **resets that parent**. ACE defines
`rightTabContent: leftTabContent`, so this turned it into a class with no base at all — no `type`,
no `style`, no geometry — and Arma could not build it as a listbox. The panel was not emptied; the
control was broken.

It also hid itself: `lbSize` on a broken control returns 0, so the collapse hit its "too few rows"
guard *before* reaching the debug logging, and the diagnostic build printed nothing at all.

The fix was to stop patching ACE's control and attach the handler at runtime with
`ctrlAddEventHandler`, which adds alongside the config-defined `onLBSelChanged` rather than
replacing it (that is `ctrlSetEventHandler`). ACE's handler still equips the item; ours only rebuilds
the option panel. No ACE class is touched, so the failure mode is gone rather than repaired.

Two further changes came out of it, both worth keeping regardless:

- **The collapse was deferred a frame past `ace_arsenal_rightPanelFilled`.** The reasoning was that
  ACE raises that event partway through `fnc_fillRightPanel` and then goes on to call `fillSort` and
  to restore the selection, so waiting until ACE had finished avoided interleaving — and it looked
  like a simplification, because the row to keep was then just `lbCurSel`, with no need to look up
  the equipped class from `ace_arsenal_currentItems`.

  **That was wrong, and it is the third live failure below.** Running after ACE's restore means
  mutating a list ACE has already selected into: every deleted row shifts the ones beneath it, and
  nothing put the selection back. The collapse now runs *during* the event again — before the sort
  and the restore — and chooses the surviving row from the equipped item instead of from `lbCurSel`.
  Only `refreshOptions` still waits a frame, because it reads a selection ACE has not set yet.
- **A safety floor**, refusing any pass that wanted to remove more than half the list. This was a
  mistake and is described below — it shipped, and it broke merging entirely the moment the grouping
  data got good.

Ruled out while diagnosing, recorded so the ground is not covered twice: `continue` inside `for..do`
(every failure mode leaves the list intact, so it cannot empty it), the descending delete order
(correct), ACE's post-event sorting and selection restore (all read `lbSize` live and none rebuild
from `virtualItems`), and the config merge (the built PBO carries exactly one property on
`rightTabContent`).

### The second live failure: a guard that fired on correct behaviour

The safety floor added above went on to cause the next bug, and it is the more instructive one.

Once Tier One's grouping data improved — 541 attachments folding to 47 rows instead of 186 — nothing
merged at all. The RPT said why in one line:

```
[aceaxatt] collapse: deleting 159 of 289 rows
[ACEAXATT] (main) ERROR: collapse would remove 159 of 289 rows -- refusing, panel left intact
```

159 of 289 is 55%. The guard refused above 50%, so **improving the merge pushed it past its own
threshold and switched it off.** The two runs either side are unambiguous:

| grouping data | removal | result |
|---|---|---|
| old, 186 rows | 84 of 289 = 29% | merging worked |
| new, 47 rows | 159 of 289 = 55% | refused, panel untouched |

The premise — "removing more than half means something was misidentified" — was written
defensively while chasing the empty panel above, and it was never what caused that. **No threshold
can work**, because a correct collapse routinely removes nearly everything: pick a weapon that only
takes Micro T-2 variants and the panel goes from 32 rows to 1, which is 97% and exactly the point of
a compat. A genuine "every class resolved to one model" fault sits at 99.7% — above any bound loose
enough to permit the legitimate case. The ratio does not carry the signal.

It is replaced by checks that are actually invariants:

- a row is only ever removed when it resolves to the **same model as a row that stays**, and that
  model comes from authored `XtdGearInfos` data rather than anything inferred at runtime;
- a model with no `XtdGearModels >> CfgWeapons >> <model>` class is skipped, so broken third-party
  data cannot merge rows behind an option panel that cannot be built;
- `count _doomed >= _size` still refuses, because every group keeps one row and that one genuinely
  cannot happen.

The general lesson: a statistical guard over a correctness property will eventually fire on the
success case. Bad groupings are caught offline by `gen_aceax.py --check` and `tools/verify.py`, where
the whole dataset is visible, not one panel at a time.

### The third live failure: an assumption written down as a fact

Fixing the wrong-variant bug above moved `fnc_refreshOptions` off the listbox row and onto the
equipped item from `ace_arsenal_currentItems`. That was right for the refill path and wrong for the
click path, and the commit said so in a comment:

```
// Safe on the click path too: ACE's config-defined onLBSelChanged runs before
// handlers added with ctrlAddEventHandler, so by the time fnc_onSelChangedRight
// gets here ACE has equipped the clicked item and currentItems is current.
```

Nobody had established that. ACE writes `GVAR(currentItems)` at the **end** of its own handler
(`fnc_onSelChangedRight.sqf:65`), so reading it from our handler returned the *previous*
attachment. Clicking a new family showed the old panel; the `if (_model != GVAR(currentModel))`
guard then saw no change and never rebuilt, so it stayed one click behind for good. Worse, picking
a value from that stale panel made `changeCurrentConfig` resolve a variant of the old model and
equip it — the click silently undid itself.

The fix is not to work out which handler runs first. It is to stop depending on the answer: ACE
equips the clicked row's data verbatim (`_item = _control lbData _curSel`), so on a click the row
is what is about to be on the weapon in either ordering. `refreshOptions` now takes a flag saying
which way round the two are, and each caller passes what it actually knows — the row leads on a
click, the weapon leads on a refill.

Two lessons, and the second is the one that cost the time:

- **A comment asserting runtime behaviour is a claim, not documentation.** This one was written
  from plausibility and then read as though it had been verified. Searching ACE3, CBA and ZEN
  afterwards turned up **no** statement of the ordering either way — the only assertions of it on
  disk were this addon's own, which is not evidence. If a claim cannot be checked, write the design
  so it does not matter.
- **Prefer the argument you were handed over the global you could look up.** The event carried the
  answer; the global was a second source that could be, and was, out of step. This is ACE's own
  house style where it hooks a control it does not own — `ace_inventory_fnc_onLBSelChanged` takes
  the index from `params` and defers the rest a frame, rather than reading state another handler
  owns.

A trap worth naming, because it is what made the false claim look reasonable: ACEAX *does* read
`ace_arsenal_currentItems` from its left-panel selection handler. It can, because it **forked the
control class in config** (`aceax_arsenal` `config.cpp`, `class leftTabContent: RscListBox`), which
replaces ACE's handler — so its `call ace_arsenal_fnc_onSelChangedLeft` on the line before is the
only thing that runs ACE's code, and the ordering is its own. This addon adds alongside instead and
controls no ordering at all. The same-looking code is safe there and unsafe here.

`changeCurrentConfig` now also refuses to rewrite a row whose model does not match the panel's,
which turns any future desync of this kind back into a cosmetic glitch rather than a changed
loadout. Check 1a exists to catch the whole class on the first click.

## 6. Things that would break this addon

Worth knowing what to look at first when something does go wrong.

- **ACE renames or renumbers `rightTabContent` (idc 14).** The constants live in
  `addons/main/defines.hpp`, copied from ACE because it ships binarised and there is no header to
  include. Symptom: an `ERROR` on arsenal open saying the control was not found or is not a
  listbox — `XEH_postInit.sqf` checks `ctrlType` for exactly this.
- **Another addon patches `rightTabContent` in config without restating its parent.** Same failure
  this addon shipped with, but caused externally: the control loses its type and the whole panel
  goes blank, for stock ACE as much as for us. The `ctrlType` check names it on arsenal open.
- **ACE moves `ace_arsenal_rightPanelFilled`** so it fires *after* the selection is restored rather
  than before. The collapse now depends on that ordering: it deletes rows during the event precisely
  so ACE's restore runs against the collapsed list and selects the surviving row itself. If the event
  moved, the deletions would once more shift the list under a selection ACE had already made.
  Symptom: check 4 fails first — the right attachment stays on the weapon while the panel highlights
  a different variant, or falls back to `<empty>` and looks unequipped.
- **ACE changes `fnc_baseWeapon`, or a compat declares `baseWeapon` on its variants.** ACE normalises
  the equipped attachment through it before matching rows (`fnc_fillRightPanel`), so the class it
  looks for is not always the class that is fitted. `fnc_collapsePanel` handles the divergence by
  rewriting the surviving row to the equipped class; `fnc_equippedItem` is why the dropdowns stay
  right even when that fails.
- **ACEAX changes its IDC ranges** into ours. Symptom: check 5 — controls from one panel appear in
  the other.
- **ACEAX implements attachments itself.** The generated compat data should still be valid (same
  schema), but this addon would conflict and need to detect and stand down.
