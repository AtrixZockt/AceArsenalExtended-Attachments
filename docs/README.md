# Documentation

Everything here is about **building a compat** — the grouping data that tells the arsenal how a
weapon mod is put together. The addon itself needs no configuration.

## Read in this order

| | |
|---|---|
| **[ATTACHMENT_COMPAT.md](ATTACHMENT_COMPAT.md)** | Start here. Building an attachment compat end to end: dumping a mod's configs, generating the data, checking it, shipping it. |
| **[OPTIONS.md](OPTIONS.md)** | The shared option-name vocabulary — `camo`, `mount`, `magnifier`, `platform` and friends — plus `compose:` for mods that write a whole accessory stack into one display name. Read before inventing your own names, so compats by different people read alike. |
| **[NEW_COMPAT.md](NEW_COMPAT.md)** | The complete walkthrough for a compat of any kind, gear and weapons included, not just attachments. |
| **[WORKFLOW.md](WORKFLOW.md)** | Day-to-day reference: what each script does, what order to run them in, and what every warning means. |
| **[TESTING.md](TESTING.md)** | How the addon itself is verified — including running two compats over one mod, and write-ups of the bugs that actually shipped. |

## The short version

```
python tools/dump_configs.py     # read the mod's configs out of the game
python tools/init_overrides.py   # scaffold the hand-written half
#   ... edit tools/overrides.yml -- this is the part that needs judgement
python tools/gen_aceax.py --check
python tools/gen_aceax.py
hemtt build
python tools/verify.py
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
