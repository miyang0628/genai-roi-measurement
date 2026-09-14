#!/usr/bin/env python3
"""
One-time, idempotent patcher so the notebooks support the tier sweep with
*genuinely independent* repeats. Run once before running the sweep:

    python experiments/patch_notebooks.py

This version fixes a subtle but important bug in the previous approach. Earlier
we appended a cache-disabling shim as a NEW cell after the one that defines
llm_call. But in these notebooks the llm_call definition AND all its calls live
in the same first code cell, so a shim appended at the end of the cell ran only
AFTER every call had already happened -- it had no effect, the cache stayed on,
and repeated runs collapsed to identical cached results (std = 0 across seeds).

Instead, this patcher edits the source directly:

  1. nb 01/015/02/03/04 -- inject, as the FIRST line inside llm_call's body,
     a guard that (a) forces use_cache=False when ROI_DISABLE_PIPELINE_CACHE=1,
     and (b) mixes the active seed (ROI_SEED) into the cache salt. Runs on every
     call, before the cache lookup.
  2. nb 02 -- make the Self-Consistency rollout salt include the seed.
  3. nb 04 -- matcher tier becomes os.getenv("ROI_MATCHER_TIER","strong").
  4. nb 00 -- fill strong-tier pricing (None -> gpt-5.4 prices).

Idempotent (sentinel-guarded). Back-ups: <notebook>.ipynb.bak (first change).
"""
from __future__ import annotations
import json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB = ROOT / "notebooks"

PIPELINE_NBS = [
    "01_agent1_task_extraction.ipynb",
    "015_agent1_5_process_graph.ipynb",
    "02_agent2_time_estimation.ipynb",
    "03_agent3_roi_computation.ipynb",
    "04_five_axis_validation.ipynb",
]

BODY_ANCHOR = '    model = MODELS[tier]["name"]\n'
GUARD = (
    '    # [ROI-PATCH] independent-repeat controls (added by patch_notebooks.py)\n'
    '    import os as _roi_os\n'
    '    _roi_seed = _roi_os.getenv("ROI_SEED", "")\n'
    '    if _roi_os.getenv("ROI_DISABLE_PIPELINE_CACHE", "0") == "1":\n'
    '        use_cache = False\n'
    '    try:\n'
    '        salt = f"{salt}|seed={_roi_seed}"\n'
    '    except NameError:\n'
    '        pass\n'
)

NB02_SALT_OLD = '            use_cache=True, salt=f"rollout-{k}",   # distinct cache per rollout\n'
NB02_SALT_NEW = (
    '            use_cache=True,\n'
    '            salt=f"rollout-{k}|seed={__import__(\'os\').getenv(\'ROI_SEED\',\'\')}",  # [ROI-PATCH] seed-aware\n'
)

MATCHER_OLD = "    mres = llm_call(MATCH_SYSTEM, MATCH_USER, tier=DEFAULT_TIER, temperature=0.0,\n"
MATCHER_NEW = (
    "    import os as _os_match  # [ROI-PATCH] matcher tier fixed for fair comparison\n"
    "    _MATCHER_TIER = _os_match.getenv(\"ROI_MATCHER_TIER\", \"strong\")\n"
    "    mres = llm_call(MATCH_SYSTEM, MATCH_USER, tier=_MATCHER_TIER, temperature=0.0,\n"
)

NB00_PRICE_OLD = '        "in": None, "cached_in": None, "out": None,  # fill before using \'strong\'\n'
NB00_PRICE_NEW = '        "in": 2.50, "cached_in": 0.25, "out": 15.00,  # [ROI-PATCH] gpt-5.4 pricing\n'


def backup_once(path):
    bak = path.with_suffix(".ipynb.bak")
    if not bak.exists():
        shutil.copy2(path, bak)

def _load(path): return json.loads(path.read_text(encoding="utf-8"))
def _save(path, nb): path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")


def patch_guard(path):
    nb = _load(path); changed = False
    for cell in nb["cells"]:
        if cell["cell_type"] != "code": continue
        src = cell["source"]
        if any("ROI-PATCH] independent-repeat controls" in ln for ln in src): continue
        for j, ln in enumerate(src):
            if ln == BODY_ANCHOR:
                cell["source"] = src[:j] + [GUARD] + src[j:]; changed = True; break
        if changed: break
    if changed: backup_once(path); _save(path, nb)
    return changed


def patch_nb02_salt(path):
    nb = _load(path); changed = False
    for cell in nb["cells"]:
        if cell["cell_type"] != "code": continue
        if any("ROI-PATCH] seed-aware" in ln for ln in cell["source"]): continue
        for j, ln in enumerate(cell["source"]):
            if ln == NB02_SALT_OLD:
                cell["source"] = cell["source"][:j] + [NB02_SALT_NEW] + cell["source"][j+1:]
                changed = True; break
        if changed: break
    if changed: backup_once(path); _save(path, nb)
    return changed


def patch_matcher(path):
    nb = _load(path); changed = False
    for cell in nb["cells"]:
        if cell["cell_type"] != "code": continue
        if any("ROI-PATCH] matcher tier" in ln for ln in cell["source"]): continue
        for j, ln in enumerate(cell["source"]):
            if ln == MATCHER_OLD:
                cell["source"] = cell["source"][:j] + [MATCHER_NEW] + cell["source"][j+1:]
                changed = True; break
        if changed: break
    if changed: backup_once(path); _save(path, nb)
    return changed


def patch_nb00_pricing(path):
    nb = _load(path); changed = False
    for cell in nb["cells"]:
        if cell["cell_type"] != "code": continue
        if any("ROI-PATCH] gpt-5.4 pricing" in ln for ln in cell["source"]): continue
        for j, ln in enumerate(cell["source"]):
            if ln == NB00_PRICE_OLD:
                cell["source"][j] = NB00_PRICE_NEW; changed = True; break
        if changed: break
    if changed: backup_once(path); _save(path, nb)
    return changed


def main():
    print("Patching strong-tier pricing in 00_setup_and_data.ipynb ...",
          "changed" if patch_nb00_pricing(NB / "00_setup_and_data.ipynb") else "already / not found")
    print("Patching matcher tier in 04_five_axis_validation.ipynb ...",
          "changed" if patch_matcher(NB / "04_five_axis_validation.ipynb") else "already / not found")
    print("Patching Agent-2 rollout salt (seed-aware) ...",
          "changed" if patch_nb02_salt(NB / "02_agent2_time_estimation.ipynb") else "already / not found")
    for name in PIPELINE_NBS:
        p = NB / name
        if not p.exists():
            print(f"  {name}: MISSING, skipped"); continue
        print(f"Injecting cache/seed guard into {name} ...",
              "changed" if patch_guard(p) else "already / anchor not found")
    print("\nDone. Back-ups saved as <notebook>.ipynb.bak (first time only).")
    print("Verify with:  python experiments/verify_patches.py")


if __name__ == "__main__":
    main()
