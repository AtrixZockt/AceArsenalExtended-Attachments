# ACEAX Attachments

An extension for [ACE3 Arsenal Extended](https://github.com/jetelain/AceArsenalExtended) (ACEAX)
that adds merging to the arsenal's **right panel** — **weapon attachments** and **magazines**.

ACEAX groups similar items behind dropdowns, but only for its ten left-panel tabs — weapons,
uniforms, vests, headgear, backpacks, goggles. The right panel is explicitly skipped:
`IDX_VIRT_ATTACHMENTS` sits in ACEAX's `unsupported` array, so every optic, laser, muzzle device and
bipod variant gets its own row, and so does every magazine.

That adds up fast, because attachments vary along more axes than gear does. One red dot shipped in
three finishes, with and without a magnifier, on two mounts, is **twelve rows for one sight** —
before you count the copies a mod cuts per weapon platform. Weapon mods routinely put several
hundred attachments in the arsenal, and the right panel lists all of them, flat.

Magazines are the same problem with a different shape: one calibre in tracer and non-tracer, in
three round counts and four tracer colours, is a screenful of rows that differ by a word.

This addon supplies the missing half of the machinery. It ships **no grouping data of its own**.

---

## For players

### It does nothing on its own

Loading this addon by itself changes **nothing**. It is the mechanism; the data that says which
items are variants of each other comes from a *compat* addon for whichever weapon mod you run.
Without one, the arsenal behaves exactly as it does with plain ACEAX.

That is deliberate, and it cuts both ways: a compat can ship attachment data and stay perfectly
inert for players who do not have this addon.

Compats built with this toolchain, as a sense of scale:

| compat | attachments | rows |
|---|---|---|
| ACEAX NIArms Compat — carries it alongside its weapon grouping | 121 | **74** |
| ACEAX Tier One Attachments — attachments only | 541 | **47** |

### Requirements

CBA_A3, ACE3, ACE3 Arsenal Extended.

Unlike a compat, these are real `requiredAddons` — the extension is meaningless without ACEAX and
must load after it.

### Will it break my existing setup?

No, and the design is what guarantees that rather than testing alone.

- **It writes no ACE or ACEAX state.** Not `ace_arsenal_virtualItems`, not ACEAX's `meta` or
  `unsupported` tables, not its option-panel variables. The left panel, containers and every
  existing compat are untouched because nothing shared is modified.
- **It only touches panels it has data for.** Grenades, explosives, misc items and container
  contents are not handled at all, and a panel with no grouping data behind it is left exactly as
  ACE built it.
- **It patches none of ACE's controls.** The selection handler is attached at runtime with
  `ctrlAddEventHandler`, which runs *alongside* ACE's own `onLBSelChanged` rather than replacing it —
  so equipping, the weight readout and `ace_arsenal_weaponItemChanged` all still happen, unchanged.
  The only thing this addon contributes to `ace_arsenal_display` is one new control of its own.
- **Unmapped items are left alone.** Anything without grouping data keeps its own row.
- **There is a kill switch.** CBA Settings → *ACE Arsenal Extended* → *Merge attachments and magazines*.
  Turn it off and the arsenal is stock ACEAX again, no restart needed.

Nothing about the items themselves changes — only how the arsenal lists them. Existing loadouts,
missions and templates keep working.

---

## For modders

`tools/` holds the generator that produces the grouping data. It reads a mod's configs off disk,
works out which items are variants of each other from their display names and class names, and
writes the `XtdGearModels` / `XtdGearInfos` config for you. You write one YAML file; everything
under `addons/main/` is generated.

It is not attachment-only — the same generator builds weapon and gear compats, and has been run
against mods ranging from 121 attachments to 841 pieces of gear.

**Start with whichever fits what you are covering:**

| | |
|---|---|
| [docs/ATTACHMENT_COMPAT.md](docs/ATTACHMENT_COMPAT.md) | a weapon mod's **optics, lasers, muzzles, bipods** — the case this addon exists for |
| [docs/NEW_COMPAT.md](docs/NEW_COMPAT.md) | **weapons or gear**, with or without attachments — the longer, more general walkthrough |

Then, either way:

| | |
|---|---|
| [docs/OPTIONS.md](docs/OPTIONS.md) | the shared option-name vocabulary — read this before inventing your own |
| [docs/WORKFLOW.md](docs/WORKFLOW.md) | day-to-day tooling reference, and what every message means |
| [docs/TESTING.md](docs/TESTING.md) | how this addon is verified, and the bugs that actually shipped |

Two things worth knowing before you start:

- **A compat needs no hard dependency on this addon.** List only `aceax_gearinfo` in
  `requiredAddons[]` and put this extension in the Workshop required-items list. The data is inert
  without it, so nobody's game hard-fails.
- **Attachment support can be layered onto an existing compat.** If a mod already has an ACEAX
  compat covering its weapons, yours can add just the attachments on top, mapping a disjoint set of
  classes — no fork, no coordination with the original author. This is proven rather than assumed;
  [docs/TESTING.md](docs/TESTING.md) records the run.

### Building

Needs [HEMTT](https://github.com/BrettMayson/HEMTT) 1.19+ on PATH.

```
hemtt build            # -> .hemttout/build
hemtt launch arsenal   # Arma 3 straight into the ACE Arsenal VR mission
hemtt launch baseline  # ACEAX + this extension only, to check nothing changed
```

---

## How it works

When ACE finishes filling the right panel it raises `ace_arsenal_rightPanelFilled`. At that moment
the list holds exactly the attachments valid for the selected weapon and slot — ACE has already
filtered by `compatibleItems`. A frame later, this addon collapses rows that share a model, keeping
one, and puts the usual ACEAX dropdowns underneath.

Collapsing the *list* rather than the item pool is the important choice. Attachment compatibility is
per weapon, so a representative picked once, globally, might not fit the weapon you have selected —
and the whole family would vanish from the panel. Doing it after the fill sidesteps that entirely,
and has the happy side effect that a dropdown only ever offers variants the current weapon can take.

Three details that matter:

- it runs a frame *after* the event, because ACE goes on to sort the panel and restore the selection
  after raising it;
- the equipped attachment is always the row that survives, so ACE's selection restore finds it
  instead of falling back to `<empty>`;
- the option panel uses its own IDC block, because ACEAX's can be showing a grouped weapon on the
  left at the same moment.

## License

MIT. This addon contains no assets from ACE3, ACEAX or any weapon mod; it reuses ACEAX's checkbox
icons at runtime by path, which is why ACEAX is a hard dependency.

ACE3 Arsenal Extended is by **GrueArbre** — this extension only adds a panel it does not cover.
