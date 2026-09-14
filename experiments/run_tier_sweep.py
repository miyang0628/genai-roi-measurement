#!/usr/bin/env python3
"""
Three-tier robustness experiment driver.

Runs the FULL pipeline (Agent 1 -> 1.5 process graph -> Agent 2 -> Agent 3 ->
five-axis validation) for each requested model tier, repeated over several seeds,
and aggregates the five-axis metrics into a per-tier mean +/- std table.

Design decisions (see experiments/PROTOCOL.md):
  * Full pipeline per tier (ROI/efficiency vary with tier, not only accuracy).
  * 5 independent runs per tier by default (reliability measured across runs).
  * The accuracy-axis MATCHER is held at a FIXED tier (default: strong) so a
    better matcher cannot flatter a stronger pipeline. The matcher is an
    evaluation instrument, not part of the artifact under test.
  * Pipeline LLM cache is DISABLED for repeats so the 5 runs are independent.

HOW IT WORKS
  The notebooks read the active tier from run_manifest.json ("default_tier") and
  honour a few environment variables this driver sets. For each (tier, seed) the
  driver: (1) rewrites default_tier in the manifest, (2) sets env overrides,
  (3) executes notebooks 01, 015, 02, 03, 04 in order via nbconvert, and
  (4) copies the produced five_axis_report.json into
  experiments/results/<tier>/run_<seed>/.

REQUIREMENTS
  * A valid OPENAI_API_KEY in .env and the three LLM_MODEL_* names.
  * run_manifest.json -> models.strong pricing filled in (currently null) if the
    strong tier is included, otherwise its efficiency axis will be null.
  * jupyter / nbconvert installed (pip install nbconvert ipykernel).

USAGE
  python experiments/run_tier_sweep.py --tiers weak mid strong \
      --repeats 5 --matcher-tier strong --seeds 42 43 44 45 46

  # dry run: print the plan and validate prerequisites without calling the API
  python experiments/run_tier_sweep.py --tiers weak mid strong --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOKS = ROOT / "notebooks"
INFER = ROOT / "artifacts" / "inference"
MANIFEST = ROOT / "artifacts" / "run_manifest.json"
RESULTS = ROOT / "experiments" / "results"

# Pipeline notebooks, in execution order. 04 produces five_axis_report.json.
PIPELINE = [
    "01_agent1_task_extraction.ipynb",
    "015_agent1_5_process_graph.ipynb",
    "02_agent2_time_estimation.ipynb",
    "03_agent3_roi_computation.ipynb",
    "04_five_axis_validation.ipynb",
]

# Metrics we pull out of each run's five_axis_report.json for aggregation.
ACCURACY_KEYS = ["grade_agreement", "grade_cohen_kappa", "time_MAE_min",
                 "time_MAPE_pct", "matched_pairs", "unmatched_reference"]
RELIABILITY_KEYS = ["mean_cv_minutes", "median_cv_minutes", "pct_nodes_low_cv"]
EFFICIENCY_KEYS = ["annual_saving_usd", "pipeline_llm_cost_usd",
                   "saving_to_cost_ratio"]
TRANSPARENCY_KEYS = ["grade_rationale_coverage_pct", "pct_estimates_grounded"]
ROBUSTNESS_KEYS = ["clarifying_rate_pct", "missing_system_flagged"]


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def save_manifest(m: dict) -> None:
    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2),
                        encoding="utf-8")


def check_prereqs(tiers: list[str]) -> list[str]:
    """Return a list of human-readable problems; empty means OK."""
    problems = []
    m = load_manifest()
    if not (ROOT / ".env").exists():
        problems.append("Missing .env (need OPENAI_API_KEY and LLM_MODEL_* names).")
    for t in tiers:
        spec = m.get("models", {}).get(t, {})
        if not spec.get("name"):
            problems.append(f"Tier '{t}' has no model name in run_manifest.json.")
        if None in (spec.get("in"), spec.get("out")):
            problems.append(
                f"Tier '{t}' pricing is null (models.{t}.in/out); the efficiency "
                f"axis will be uncomputable for this tier. Fill it before running.")
    # nbconvert must be importable AND runnable as `python -m nbconvert`.
    import importlib.util
    if importlib.util.find_spec("nbconvert") is None:
        problems.append("`nbconvert` not importable; run `pip install nbconvert ipykernel`.")
    else:
        probe = subprocess.run(
            [sys.executable, "-m", "nbconvert", "--version"],
            capture_output=True, text=True)
        if probe.returncode != 0:
            problems.append(
                "`python -m nbconvert` failed to run; run "
                "`pip install --upgrade nbconvert ipykernel`.")
    if importlib.util.find_spec("ipykernel") is None:
        problems.append("`ipykernel` not installed; run `pip install ipykernel`.")
    else:
        # Confirm a usable kernel is registered (default 'python3').
        kern = os.environ.get("ROI_KERNEL", "python3")
        ks = subprocess.run([sys.executable, "-m", "jupyter", "kernelspec", "list",
                             "--json"], capture_output=True, text=True)
        if ks.returncode == 0:
            try:
                names = set(json.loads(ks.stdout).get("kernelspecs", {}).keys())
                if kern not in names:
                    problems.append(
                        f"Kernel '{kern}' is not registered (found: {sorted(names)}). "
                        f"Run `python -m ipykernel install --user --name python3`, "
                        f"or set ROI_KERNEL to one of the found names.")
            except Exception:
                pass  # non-fatal; run_notebook will surface a clear error if needed
    return problems


def run_notebook(nb: str, env: dict) -> None:
    """Execute one notebook in-place via nbconvert, inheriting env overrides.

    The kernel is pinned to a known name (env ROI_KERNEL, else 'python3') so a
    notebook whose saved kernelspec points at a named conda env (e.g.
    'credit_override_env') does not fail with NoSuchKernel on another machine.
    """
    kernel = env.get("ROI_KERNEL", "python3")
    cmd = [
        sys.executable, "-m", "nbconvert", "--to", "notebook",
        "--execute", "--inplace", "--ExecutePreprocessor.timeout=1200",
        f"--ExecutePreprocessor.kernel_name={kernel}",
        str(NOTEBOOKS / nb),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), env=env,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        tail = proc.stderr[-2000:]
        hint = ""
        if "NoSuchKernel" in tail:
            hint = ("\nHINT: the notebook's saved kernel is unavailable. Register "
                    "one named 'python3' with:\n"
                    "  python -m ipykernel install --user --name python3\n"
                    "or pass a different kernel via the ROI_KERNEL env var.")
        raise RuntimeError(
            f"Notebook {nb} failed (exit {proc.returncode}).\n"
            f"STDERR tail:\n{tail}{hint}")


def one_run(tier: str, seed: int, matcher_tier: str, disable_cache: bool) -> dict:
    """Run the full pipeline once for (tier, seed); return the five-axis report."""
    m = load_manifest()
    m["default_tier"] = tier
    m["seed"] = seed
    # keep every agent stage on the swept tier
    for stage in m.get("pipeline_cfg", {}):
        m["pipeline_cfg"][stage]["tier"] = tier
    save_manifest(m)

    env = os.environ.copy()
    env["ROI_ACTIVE_TIER"] = tier
    env["ROI_SEED"] = str(seed)
    env["ROI_MATCHER_TIER"] = matcher_tier          # honoured by nb 04 (see patch)
    env["ROI_DISABLE_PIPELINE_CACHE"] = "1" if disable_cache else "0"
    env["PYTHONHASHSEED"] = str(seed)

    for nb in PIPELINE:
        run_notebook(nb, env)

    report = json.loads((INFER / "five_axis_report.json").read_text(encoding="utf-8"))
    dest = RESULTS / tier / f"run_{seed}"
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(INFER / "five_axis_report.json", dest / "five_axis_report.json")
    if (INFER / "agent3_roi.json").exists():
        shutil.copy2(INFER / "agent3_roi.json", dest / "agent3_roi.json")
    return report


def flatten(report: dict) -> dict:
    ax = report["axes"]
    out = {}
    for k in ACCURACY_KEYS:      out[f"acc.{k}"] = ax["1_accuracy"].get(k)
    for k in RELIABILITY_KEYS:   out[f"rel.{k}"] = ax["2_reliability"].get(k)
    for k in EFFICIENCY_KEYS:    out[f"eff.{k}"] = ax["3_efficiency"].get(k)
    for k in TRANSPARENCY_KEYS:  out[f"tra.{k}"] = ax["4_transparency"].get(k)
    for k in ROBUSTNESS_KEYS:    out[f"rob.{k}"] = ax["5_robustness"].get(k)
    return out


def agg(values: list) -> dict:
    nums = [v for v in values if isinstance(v, (int, float))]
    if not nums:
        return {"mean": None, "std": None, "n": 0}
    return {
        "mean": round(statistics.mean(nums), 4),
        "std": round(statistics.pstdev(nums), 4) if len(nums) > 1 else 0.0,
        "n": len(nums),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiers", nargs="+", default=["weak", "mid", "strong"])
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--seeds", nargs="+", type=int, default=None,
                    help="Explicit seeds; defaults to 42..42+repeats-1.")
    ap.add_argument("--matcher-tier", default="strong")
    ap.add_argument("--keep-cache", action="store_true",
                    help="Do NOT disable the pipeline cache (not recommended for repeats).")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    seeds = args.seeds or list(range(42, 42 + args.repeats))
    if len(seeds) != args.repeats and args.seeds is None:
        seeds = seeds[:args.repeats]

    print(f"Tiers      : {args.tiers}")
    print(f"Seeds      : {seeds}  ({len(seeds)} runs/tier)")
    print(f"Matcher    : fixed at '{args.matcher_tier}'")
    print(f"Cache      : {'kept' if args.keep_cache else 'DISABLED for pipeline'}")

    problems = check_prereqs(args.tiers + [args.matcher_tier])
    if problems:
        print("\nPREREQUISITE PROBLEMS:")
        for p in problems:
            print(f"  - {p}")
        if not args.dry_run:
            print("\nFix the above, or re-run with --dry-run to only see the plan.")
            sys.exit(1)

    if args.dry_run:
        print("\n[dry-run] Prerequisites checked; no API calls made. "
              "Remove --dry-run to execute.")
        return

    original_manifest = MANIFEST.read_text(encoding="utf-8")  # restore later
    RESULTS.mkdir(parents=True, exist_ok=True)
    per_tier_runs: dict[str, list[dict]] = {t: [] for t in args.tiers}

    try:
        for tier in args.tiers:
            for seed in seeds:
                print(f"\n=== tier={tier} seed={seed} ===")
                report = one_run(tier, seed, args.matcher_tier,
                                 disable_cache=not args.keep_cache)
                per_tier_runs[tier].append(flatten(report))
                acc = report["axes"]["1_accuracy"]
                print(f"    kappa={acc.get('grade_cohen_kappa')} "
                      f"MAPE={acc.get('time_MAPE_pct')}%")
    finally:
        MANIFEST.write_text(original_manifest, encoding="utf-8")  # always restore
        print("\n[restored original run_manifest.json]")

    # ---- aggregate -----------------------------------------------------------
    metric_names = sorted({k for runs in per_tier_runs.values()
                           for r in runs for k in r})
    summary = {"generated_utc": datetime.now(timezone.utc).isoformat(),
               "seeds": seeds, "matcher_tier": args.matcher_tier,
               "tiers": {}}
    rows = []
    for tier in args.tiers:
        runs = per_tier_runs[tier]
        summary["tiers"][tier] = {}
        for mname in metric_names:
            a = agg([r.get(mname) for r in runs])
            summary["tiers"][tier][mname] = a
            rows.append({"tier": tier, "metric": mname,
                         "mean": a["mean"], "std": a["std"], "n": a["n"]})

    (RESULTS / "tier_comparison.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # CSV
    import csv
    with (RESULTS / "tier_comparison.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["tier", "metric", "mean", "std", "n"])
        w.writeheader()
        w.writerows(rows)

    print("\nWrote:")
    print(f"  {RESULTS / 'tier_comparison.json'}")
    print(f"  {RESULTS / 'tier_comparison.csv'}")
    print("\nHeadline (mean across runs):")
    for tier in args.tiers:
        t = summary["tiers"][tier]
        k = t.get("acc.grade_cohen_kappa", {}).get("mean")
        mape = t.get("acc.time_MAPE_pct", {}).get("mean")
        print(f"  {tier:6s}  kappa={k}  MAPE={mape}%")


if __name__ == "__main__":
    main()
