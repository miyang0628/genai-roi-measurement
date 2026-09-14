#!/usr/bin/env python3
"""Verify the patches are in the right place: the cache/seed guard must sit
INSIDE llm_call's body, BEFORE the cache-lookup line, so it actually takes
effect. Also checks matcher tier, seed-aware salt, and nb00 pricing."""
import json
from pathlib import Path

NB = Path(__file__).resolve().parent.parent / "notebooks"
PIPE = ["01_agent1_task_extraction","015_agent1_5_process_graph",
        "02_agent2_time_estimation","03_agent3_roi_computation","04_five_axis_validation"]

ok = True
for name in PIPE:
    nb = json.loads((NB / f"{name}.ipynb").read_text(encoding="utf-8"))
    src = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"]=="code")
    # positions
    p_def   = src.find("def llm_call(")
    p_guard = src.find("ROI-PATCH] independent-repeat controls")
    p_lookup= src.find("if use_cache and cache_file.exists()")
    good = (p_def != -1 and p_guard != -1 and p_lookup != -1
            and p_def < p_guard < p_lookup)
    print(f"{name}: guard inside llm_call before cache-lookup = {good}")
    if not good: ok = False

# nb02 seed-aware salt
s02 = "\n".join("".join(c["source"]) for c in json.loads((NB/"02_agent2_time_estimation.ipynb").read_text(encoding='utf-8'))["cells"] if c["cell_type"]=="code")
print("nb02 rollout salt seed-aware:", "ROI-PATCH] seed-aware" in s02)
# nb04 matcher
s04 = "\n".join("".join(c["source"]) for c in json.loads((NB/"04_five_axis_validation.ipynb").read_text(encoding='utf-8'))["cells"] if c["cell_type"]=="code")
print("nb04 matcher tier fixed:", "ROI_MATCHER_TIER" in s04)
# nb00 pricing
s00 = "\n".join("".join(c["source"]) for c in json.loads((NB/"00_setup_and_data.ipynb").read_text(encoding='utf-8'))["cells"] if c["cell_type"]=="code")
print("nb00 strong priced:", "ROI-PATCH] gpt-5.4 pricing" in s00)

print("\nOVERALL:", "PASS" if ok else "FAIL -- guard misplaced")
