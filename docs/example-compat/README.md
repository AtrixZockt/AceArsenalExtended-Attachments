# A compat you can copy

A complete, buildable ACEAX compat, written by hand. Two families — one optic, one magazine —
which is enough to show the whole schema without burying it.

Use this when the mod you are covering is small enough to type out. The generator in `tools/`
exists because Tier One Weapons has 541 attachments; if yours has twelve, this is less work and
you can read the result. Nothing here needs Python, PyYAML, a Workshop-installed source mod or a
config dump. HEMTT is the only requirement.

The classes it names are fictional, so **it does nothing until you point it at real ones.** That
is deliberate — a sample wired to real Arma 3 optics would collide with the official Vanilla
compat for anyone running both.

## The files

| | |
|---|---|
| `mod.cpp` | Mod-folder metadata. Not packed into the PBO. |
| `.hemtt/project.toml` | Build config. A compat has no `script_version.hpp`, so the version is written literally here. |
| `addons/main/$PBOPREFIX$` | Where the PBO mounts. **Write this with a text editor** — `\a` is the BEL escape character, so `printf 'z\aceaxfoo\...'` silently produces a corrupt path and the build then fails with a confusing "failed to create directory". |
| `addons/main/config.cpp` | `CfgPatches` plus two `#include`s. That is the entire addon. |
| `addons/main/XtdGearModels.hpp` | Index of the models — one arsenal row each. |
| `addons/main/XtdGearModels_Common.hpp` | Shared option definitions, so a label is written once. |
| `addons/main/XtdGearInfos.hpp` | Index of the infos — one real item each. |
| `addons/main/XtdGear*/foo/...` | The actual data. Every file is commented. |

There is no SQF, no `stringtable.xml`, no `script_component.hpp` and no CBA macros. A compat is
pure config. Splitting the data into one file per model under `XtdGear*/<pack>/<root>/` is only
a habit borrowed from the generated compats so this looks like what you will meet there; two
models would sit perfectly happily inline.

## The model

Three ideas, and that is all of it:

- A **model** is one arsenal row — the Hawkeye family, defined under `XtdGearModels`.
- An **option** is one dropdown under that row — `camo`, `reticle`. Its values are config class
  names (`MILDOT`, never `Mil-dot`): they must start with a letter and contain no spaces. The
  readable form goes in `label`.
- An **info** maps one real in-game item to a model and its position on every option —
  `FooMod_Optic_Hawkeye_Tan_Mildot` is `camo = "TAN"`, `reticle = "MILDOT"`.

Read `XtdGearModels/foo/CfgWeapons/foo_optic_hawkeye.hpp` and then its twin under
`XtdGearInfos/`. The pair is the whole idea.

## Make it yours

1. **Rename the addon.** `aceaxfoo` appears in four places, and they must agree: `$PBOPREFIX$`,
   `prefix` in `.hemtt/project.toml`, `dir` in `mod.cpp`, and the class name `aceaxfoo_main` in
   `config.cpp`. Pick something nobody else will use.
2. **Rename the model classes.** `foo_optic_hawkeye`, `foo_mag_556`, `foo_reticle`, `foo_ammo`.
   These are global config class names — Arma merges same-named classes across addons, so two
   compats defining a bare `reticle` differently would blend into each other. A short prefix of
   your own is the whole protection.
3. **Replace the item class names** in the `XtdGearInfos` files with real ones from your mod.
   These are what actually has to match; everything else is yours to name.
4. `hemtt build`, then load the mod alongside ACEAX and ACEAX Attachments.

The `foo/` folder and the `.hpp` filenames are organisation only — nothing reads them. Rename
them if you like, but they are spelled out in the `#include` lines of `XtdGearModels.hpp` and
`XtdGearInfos.hpp`, so the two have to move together or the build stops with a missing-file
error. Renaming the *classes* without touching the folders is perfectly fine.

Option *names* — `camo`, `reticle`, `ammo` — are the opposite case: they are not global, and
sharing them across compats is the point. See [OPTIONS.md](../OPTIONS.md) before inventing your
own, so compats by different people read alike.

## Four things that fail silently

- **`XtdGearInfos` is plural.** Singular `XtdGearInfo` means a different thing — a class nested
  inside the item's own `CfgWeapons` entry — and a root-level singular is simply never read.
- **Only `camo`, `pantscamo`, `sleeves` and `Faction` work without a base class.** They resolve
  through `XtdGearModels >> Conventional` in `aceax_gearinfo`. Every other axis needs a parent in
  `XtdGearModels_Common.hpp`, or its dropdown shows raw uppercase class names.
- **Every info entry must set every option** the model lists. A missing line reads back as `""`
  and that item then matches no combination at all.
- **No two entries may share the same coordinates**, or they collide on one dropdown position.

If a family does not fill its grid — say the tan version never shipped with a mil-dot — add
`alwaysSelectable = 1;` to the axis so the value stays clickable anyway.

## Where this stops

- Nothing here hard-depends on FooMod. `requiredAddons[]` lists only `aceax_gearinfo`, and the
  `XtdGearInfos` entries name source classes without inheriting from them, so the compat loads
  fine when the source mod is absent — the entries just describe items that are not there. Put
  the source mod in your Workshop required-items list instead.
- Attachment grouping needs **ACEAX Attachments** loaded. The data is inert without it, so
  players who skip it get no error, just no dropdowns.
- When the mod outgrows hand-writing, [ATTACHMENT_COMPAT.md](../ATTACHMENT_COMPAT.md) is the
  generator route end to end. The format it emits is the format here.
