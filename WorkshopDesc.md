[h1]What's This?[/h1]
[url=https://steamcommunity.com/sharedfiles/filedetails/?id=2522638637]ACE3 Arsenal Extended[/url] groups similar gear behind dropdowns, so instead of scrolling past forty helmets you pick one entry and choose the camo. It does that for the arsenal's [b]left[/b] panel only — weapons, uniforms, vests, headgear, backpacks, goggles.

Attachments and magazines live in the [b]right[/b] panel, and it deliberately skips them. So every optic, laser, muzzle device, bipod and magazine variant still gets its own row.

This addon adds that missing half.

It adds up faster than gear does, because attachments vary along more axes. One red dot in three finishes, with and without a magnifier, on two mounts, is [b]twelve rows for one sight[/b] — before you count the copies a mod cuts for each weapon platform. Weapon mods routinely put several hundred attachments in the arsenal, and the right panel lists every one of them, flat.

Magazines are the same problem wearing a different hat: one calibre in tracer and non-tracer, across three round counts and four tracer colours, is a screenful of rows that differ by a single word.

[h1]Important: It Does Nothing On Its Own[/h1]
This is the mechanism, not the data. It needs a [b]compat[/b] addon for whichever weapon mod you run, telling it which items are variants of each other.

Load it by itself and nothing changes at all. That's by design — and it works the other way round too, so a compat can ship right-panel data and stay completely inert for players who don't have this.

Compats that ship attachment data, as a sense of scale:
[list]
[*] [url=https://steamcommunity.com/sharedfiles/filedetails/?id=3791721792]ACEAX Tier One Attachments[/url] — 541 attachments into 47 rows
[*] [url=https://steamcommunity.com/sharedfiles/filedetails/?id=3788512518]ACEAX NIArms Compat[/url] — 121 attachments into 74 rows, on top of the weapon grouping it already does
[/list]

Those compats work fine without this addon — the attachment half simply sits idle. Adding this is what switches it on.

[h1]Will It Break Anything?[/h1]
No, and the design is what guarantees that rather than testing alone.

[list]
[*] It writes no ACE or ACE Arsenal Extended state. The left panel, containers and every existing compat are untouched, because nothing shared is modified
[*] It patches none of ACE's controls. The handler is attached at runtime and runs [i]alongside[/i] ACE's own, so equipping, the weight readout and everything else still work exactly as before
[*] Items with no grouping data keep their own row, exactly as they do now
[*] It only touches panels it has data for. Grenades, explosives, misc items and container contents aren't handled at all
[*] There's a kill switch: [b]CBA Settings → ACE Arsenal Extended → Merge attachments and magazines[/b]. Turn it off and you're back to stock behaviour, no restart needed
[/list]

Nothing about the items themselves changes — only how the arsenal lists them. Existing loadouts, missions and templates keep working.

[h1]For Modders[/h1]
The GitHub repo ships the full toolchain that generates a compat: it reads a weapon mod's configs, works out which items are variants of each other, and writes the config for you. There's a documented option vocabulary so compats written by different people read the same way.

Two things worth knowing:
[list]
[*] A compat needs [b]no hard dependency[/b] on this addon — the data is inert without it, so nobody's game hard-fails
[*] Right-panel support can be [b]layered onto an existing compat[/b]. If a weapon mod already has an ACEAX compat covering its guns, yours can add just the attachments and magazines on top. You don't have to fork or replace someone else's work
[/list]

[url=https://github.com/AtrixZockt/AceArsenalExtended-Attachments]github.com/AtrixZockt/AceArsenalExtended-Attachments[/url] — MIT licensed, documentation in [i]docs/[/i].

[h1]Requirements[/h1]
[list]
[*] CBA_A3
[*] ACE3
[*] [url=https://steamcommunity.com/sharedfiles/filedetails/?id=2522638637]ACE3 Arsenal Extended[/url]
[*] A compat addon for your weapon mod — see above
[/list]

[h1]Credits[/h1]
[b]GrueArbre[/b] for ACE3 Arsenal Extended, which does the real work here. This extension only adds a panel it doesn't cover, and reuses its option UI to do it.

No assets from ACE3, ACE Arsenal Extended or any weapon mod are included.
