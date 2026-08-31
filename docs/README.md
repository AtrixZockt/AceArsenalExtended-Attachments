# Documentation

Everything here is about **building a compat** — the grouping data that tells the arsenal how a
weapon mod is put together. The addon itself needs no configuration.

## Start with whichever fits what you are covering

| | |
|---|---|
| **[ATTACHMENT_COMPAT.md](ATTACHMENT_COMPAT.md)** | Covering a weapon mod's **optics, lasers, muzzle devices and bipods** — the case this addon exists for. End to end, assuming no prior knowledge. |
| **[NEW_COMPAT.md](NEW_COMPAT.md)** | Covering **weapons or gear** (uniforms, vests, helmets, facewear, backpacks), with or without attachments. The longer, more general walkthrough — every scaffold file in full. |

Then, whichever you started with:

| | |
|---|---|
| **[example-compat/](example-compat/)** | A complete compat, written by hand and buildable — copy it, rename two things, point it at your classes. No Python, no config dump. Start here if the mod is small enough to type out, or just to see what the format actually looks like. |
| **[OPTIONS.md](OPTIONS.md)** | The shared option-name vocabulary — `camo`, `mount`, `magnifier`, `platform` and friends — plus the tables for mods that write the distinction somewhere awkward: `compose:`, `name_prefixes:`, `class_prefixes:`. Read before inventing your own names, so compats by different people read alike. |
| **[WORKFLOW.md](WORKFLOW.md)** | Day-to-day reference: what each script does, what order to run them in, and what every message means. |
| **[TESTING.md](TESTING.md)** | How the addon itself is verified, and write-ups of the bugs that actually shipped. Worth skimming before changing anything in `tools/`. |

## The short version

```
python tools/init_mod.py <workshop_id> --prefix aceaxfoo --model-prefix foo --author "You"
#   ... create the scaffold files it lists
python tools/dump_configs.py     # read the mod's configs out of the game
python tools/init_overrides.py   # scaffold the hand-written half
python tools/report.py --families
#   ... edit tools/overrides.yml -- this is the part that needs judgement
python tools/gen_aceax.py --check
python tools/gen_aceax.py
hemtt build
python tools/verify.py
python tools/report.py --coverage
```

`overrides.yml` is where the work is. The rest is mechanical.

## Three things that catch people out

- **A compat must not hard-depend on this addon.** List `aceax_gearinfo` in `requiredAddons[]` and
  nothing else; put the extension in the Workshop required-items list instead. Attachment data is
  inert without it, so players who skip it get no error.
- **Option *values* are config class names.** `X1_6`, never `1.6x` — they must start with a letter
  and contain no spaces. The readable form goes in `label`.
- **`verify.py` warning "N variants reachable only via the weak-match fallback" is not cosmetic.**
  It means two axes are coupled — one only has a value when the other does — so no single dropdown
  click can cross between them, and clicking one may hand the player the wrong class. A large count
  is the signal to split an entry, not to merge harder. [OPTIONS.md](OPTIONS.md) has the worked
  example.
