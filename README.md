# ACEAX Attachments

An extension for [ACE3 Arsenal Extended](https://github.com/jetelain/AceArsenalExtended) (ACEAX)
that adds **weapon-attachment merging** to the arsenal's right panel.

ACEAX groups similar items behind dropdowns, but only for its ten left-panel tabs — weapons,
uniforms, vests, headgear, backpacks, goggles. Attachments live in the right panel and are
explicitly skipped: `IDX_VIRT_ATTACHMENTS` is listed in ACEAX's `unsupported` array, so every optic,
laser, muzzle device and bipod variant gets its own row.

That adds up. Measured against real mods:

| mod | attachments in the arsenal | rows once merged |
|---|---|---|
| Tier One Weapons | 541 | **186** |
| Modern Combat Carbines | 359 | **162** |

This addon supplies the missing half of the machinery. It does not ship any grouping data itself —
that comes from compat addons, which anyone can build with the toolchain in [`tools/`](tools/).

## Important: it does nothing on its own

Loading this addon by itself changes **nothing**. It needs a compat addon that maps a weapon mod's
attachments into `XtdGearModels` / `XtdGearInfos`. Without one, the arsenal behaves exactly as it
does with plain ACEAX.

That is deliberate, and it works the other way round too: a compat can ship attachment data and stay
perfectly inert for players who do not have this addon. See
[ATTACHMENT_COMPAT.md](ATTACHMENT_COMPAT.md).

## Requirements

CBA_A3, ACE3, ACE3 Arsenal Extended.

Unlike a compat addon, these are real `requiredAddons` — the extension is meaningless without ACEAX,
and it has to load after it.

## Will it break my existing setup?

No, and the design is what guarantees it rather than testing alone.

- **It writes no ACEAX or ACE state.** Not `ace_arsenal_virtualItems`, not ACEAX's `meta` or
  `unsupported` tables, not its option-panel variables. The left panel, magazines, containers and
  every existing compat are untouched because nothing shared is modified.
- **It adds one config property.** ACE's `rightTabContent` control gets a new `onLBSelChanged`, and
  our handler calls ACE's original first — so equipping, the weight readout and the
  `ace_arsenal_weaponItemChanged` event all still happen, unchanged. Everything else about the
  control keeps inheriting from ACE.
- **Unmapped attachments are left alone.** Anything without grouping data keeps its own row.
- **There is a kill switch.** CBA Settings → *ACE Arsenal Extended* → *Merge weapon attachments*.
  Turn it off and the arsenal is stock ACEAX again, no restart needed.

## How it works

When ACE finishes filling the right panel it raises `ace_arsenal_rightPanelFilled`. At that moment
the list holds exactly the attachments valid for the selected weapon and slot — ACE has already
filtered by `compatibleItems`. This addon then collapses rows that share a model, keeping one, and
puts the usual ACEAX dropdowns underneath.

Collapsing the *list* rather than the item pool is the important choice. Attachment compatibility is
per weapon, so a representative picked once, globally, might not fit the weapon you have selected —
and the whole family would disappear. Doing it after the fill sidesteps that entirely, and has the
happy side effect that the dropdown only ever offers variants the current weapon can take.

Two details that matter:

- the equipped attachment is always the row that survives, so ACE's selection restore still finds
  it instead of falling back to `<empty>`;
- the option panel uses its own IDC block, because ACEAX's can be showing a grouped weapon on the
  left at the same time.

## Building

Needs [HEMTT](https://github.com/BrettMayson/HEMTT) 1.19+ on PATH.

```
hemtt build            # -> .hemttout/build
hemtt launch arsenal   # Arma 3 straight into the ACE Arsenal VR mission
hemtt launch baseline  # ACEAX + this extension only, to check nothing changed
```

## Making a compat

`tools/` holds the generator that produces the grouping data, the same one behind the NIArms, BWmod
and Military Gear Pack compats. It reads a mod's configs, works out which attachments are variants
of each other from their display names, and writes the config.

Start at **[ATTACHMENT_COMPAT.md](ATTACHMENT_COMPAT.md)**.

| | |
|---|---|
| [ATTACHMENT_COMPAT.md](ATTACHMENT_COMPAT.md) | build an attachment compat, start to finish |
| [OPTIONS.md](OPTIONS.md) | the shared option-name vocabulary — read this before inventing your own |
| [NEW_COMPAT.md](NEW_COMPAT.md) | the full walkthrough for a compat of any kind |
| [WORKFLOW.md](WORKFLOW.md) | day-to-day tooling reference, and what every warning means |
| [TESTING.md](TESTING.md) | how this addon is verified, including layering onto an existing compat |

## License

MIT. This addon contains no assets from ACE3, ACEAX or any weapon mod; it reuses ACEAX's checkbox
icons at runtime by path, which is why ACEAX is a hard dependency.

ACE3 Arsenal Extended is by **GrueArbre** — this extension only adds a panel it does not cover.
