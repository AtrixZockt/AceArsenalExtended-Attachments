"""Validate the BUILT pbo the way aceax_gearinfo_fnc_diag_detectErrors would.

Checks the rapified output rather than the source .hpp files, so it catches anything
lost or mangled between authoring and binarisation. Also cross-checks every mapped
class against the source-mod dump, which the in-game diagnostic cannot do.

Every config root the compat emits is validated separately -- CfgWeapons for weapons
and worn gear, CfgVehicles for backpacks, CfgGlasses for facewear.

Usage:
    hemtt build && python tools/verify.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import modinfo  # noqa: E402
from modconfig import Config, unproven_variants  # noqa: E402

REPO = modinfo.REPO
BUILT = modinfo.load().built_pbo


def load_built(pbo: Path) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "config.bin"
        out = Path(tmp) / "config.json"
        subprocess.run(
            ["hemtt", "utils", "pbo", "extract", str(pbo), "config.bin", str(raw)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["hemtt", "utils", "config", "derapify", "-f", "json", str(raw), str(out)],
            check=True,
            capture_output=True,
        )
        return json.loads(out.read_text(encoding="utf-8"))


def main() -> int:
    if not BUILT.is_file():
        print(f"no built pbo at {BUILT} -- run `hemtt build` first", file=sys.stderr)
        return 2

    built = load_built(BUILT)
    config = Config.load()
    arsenal = {i.name.lower(): i for i in config.arsenal_items()}

    errors: list[str] = []
    warnings: list[str] = []
    total_models = total_infos = 0

    # Models and configs are namespaced by config root, and a model is only valid
    # for the root it was declared under -- a helmet must not resolve to a model
    # sitting in CfgGlasses. So each root is validated in isolation.
    for root in config.roots:
        models = built.get("XtdGearModels", {}).get(root, {})
        infos = built.get("XtdGearInfos", {}).get(root, {})
        total_models += len(models)
        total_infos += len(infos)
        used_models: dict[str, list[str]] = {name: [] for name in models}

        for name, info in infos.items():
            model_name = info.get("model", "")
            model = models.get(model_name)
            if model is None:
                errors.append(f"[{root}] {name}: references unknown model {model_name!r}")
                continue
            used_models[model_name].append(name)

            for option in model.get("options", []):
                allowed = model.get(option, {}).get("values", [])
                value = info.get(option, "")
                if not value:
                    errors.append(f"[{root}] {name}: no value for option {option!r}")
                elif value not in allowed:
                    errors.append(
                        f"[{root}] {name}: {option}={value!r} is not one of {allowed}"
                    )

            item = arsenal.get(name.lower())
            if item is None:
                errors.append(
                    f"[{root}] {name}: not an arsenal-visible "
                    f"{modinfo.load().source_name} item"
                )
            elif item.config_root != root:
                errors.append(
                    f"[{root}] {name}: is a {item.config_root} class, mapped under {root}"
                )

        # two configs resolving to the same option combination make one unreachable,
        # and a model spanning two arsenal tabs hides members on the wrong panel
        for model_name, members in used_models.items():
            if not members:
                errors.append(f"[{root}] {model_name}: model has no configs")
                continue

            kinds = {arsenal[n.lower()].kind for n in members if n.lower() in arsenal}
            if len(kinds) > 1:
                errors.append(f"[{root}] {model_name}: spans arsenal tabs {sorted(kinds)}")

            options = models[model_name].get("options", [])
            seen: dict[tuple, str] = {}
            for name in members:
                key = tuple(infos[name].get(o, "") for o in options)
                if key in seen:
                    errors.append(
                        f"[{root}] {model_name}: {seen[key]} and {name} share options "
                        + "+".join(key)
                    )
                seen.setdefault(key, name)

            # can every variant be selected through the dropdowns? values[] is read
            # from the built config rather than inferred, so this validates what shipped
            values = [models[model_name].get(o, {}).get("values", []) for o in options]
            unproven = unproven_variants(seen, values)
            if unproven:
                warnings.append(
                    f"[{root}] {model_name}: {len(unproven)} variant(s) reachable only "
                    f"via the weak-match fallback -- {', '.join(unproven[:3])}"
                    + (" ..." if len(unproven) > 3 else "")
                )

    print(
        f"{total_models} models, {total_infos} configs across {len(config.roots)} config "
        f"root(s), {len(arsenal)} arsenal items in dump"
    )

    if warnings:
        print(f"\n{len(warnings)} warning(s) -- work today, but depend on weak-match ordering:")
        for w in warnings:
            print(f"  {w}")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(f"  {e}")
        return 1

    uncovered = len(arsenal) - total_infos
    print(f"OK -- no errors. {uncovered} items intentionally left ungrouped (no sibling variant).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
