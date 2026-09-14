# genai-roi-measurement

Automating interview-based generative-AI ROI measurement: a domain-agnostic
four-agent pipeline with a five-axis validation framework.

> **Anonymized artifact.** This repository accompanies a manuscript under
> double-anonymous review. All author, institutional, and organizational
> identifiers have been removed. Please do not de-anonymize.

---

## Overview

Measuring the return on investment (ROI) of adopting generative AI for knowledge
work is normally a manual consulting task: an analyst reads interview
transcripts, enumerates the work, estimates effort, and computes savings. This
project reframes that task as an automatable design artifact and provides a
reproducible reference implementation.

The pipeline takes an **operational interview transcript from any domain** as its
only domain-specific input and produces an ROI estimate together with the
evidence needed to judge whether that estimate can be trusted. All domain
knowledge lives in the input; the prompts and code contain no domain-specific
logic, so the same pipeline transfers across domains unchanged.

The work is framed as a Design Science Research Methodology (DSRM) study. Its two
central contributions are:

1. A **four-agent procedural pipeline** that maps the ROI-measurement problem
   onto a sequence of specialized agents.
2. A **five-axis validation framework** for evaluating a judgment-type artifact
   whose ground truth is not immediately observable.

---

## The pipeline

| Agent | Stage | Technique | Role |
|-------|-------|-----------|------|
| 1 | Task Extraction & Automatability Classification | Chain-of-Thought | Extract work units; grade each `full` / `partial` / `manual` with a rationale |
| 2 | Process-Graph Construction | typed-graph induction | Assign shape types + edges; derive AS-IS and TO-BE process graphs |
| 3 | Work-Time Estimation | Self-Consistency | Estimate per-task time with source tags and reliability dispersion |
| 4 | ROI Computation & Sensitivity | ReAct (reason + code action) | Compute ROI in code; sweep uncertain parameters |

Three transferable design principles are enforced throughout:

- **DP1 — Role separation.** Each agent has one job; agents hand off through
  fixed JSON with a validation gate that blocks error propagation.
- **DP2 — Delegate arithmetic to code.** No ROI arithmetic is done by the LLM;
  Python evaluates every formula, blocking numeric hallucination.
- **DP3 — Mark the unknown.** Values not stated in the interview are flagged
  (`[MISSING]`) rather than fabricated; low-confidence, high-impact items are
  surfaced as clarifying questions.

---

## The five-axis validation framework

Because the pipeline's output is a judgment-type artifact with no single
observable ground truth, validation is structured as five complementary axes,
each answering a distinct question and filled from evidence the pipeline already
produces:

| Axis | Question | Backing evidence |
|------|----------|------------------|
| 1 Accuracy     | Does output match a (partial) expert reference? | grade agreement, Cohen's κ; time MAE / MAPE |
| 2 Reliability  | Is the result reproducible on the same input?   | Self-Consistency dispersion (CV) |
| 3 Efficiency   | Does it reduce cost/time versus manual work?    | analysis cost vs. estimated recurring saving |
| 4 Transparency | Is the reasoning auditable and grounded?        | rationale coverage; source-tag provenance |
| 5 Robustness   | Does it handle missing / noisy input safely?    | clarifying-question rate; `[MISSING]` handling |

Per-axis adequacy thresholds are intentionally left as future standardization
work; the framework reports evidence per axis rather than a pass/fail verdict.
The five axes validate the artifact's **effort-based** return; adoptions whose
value is a quality uplift at unchanged effort are discussed as a value-model
extension (see the quality-uplift case below), not scored on these five axes.

---

## Model-tier robustness study

To separate the quality of the artifact from the capability of the underlying
model, the full pipeline is run five times at each of three model tiers (weak /
mid / strong), with the accuracy-axis alignment matcher held fixed at the strong
tier so a more capable pipeline is not flattered by a more capable matcher. The
headline finding: **accuracy does not improve with tier** — grade agreement and
time error are flat within run-to-run noise across a roughly fivefold increase in
per-run cost. Because the interview states no explicit durations, the binding
constraint is the information elicited in the interview, not the model applied to
it. The sweep and its aggregation are provided as `notebooks/RUN_EXPERIMENT.ipynb`
(single self-contained cell) and `notebooks/09_tier_sweep_aggregation.ipynb`.

---

## Governance layer

The pipeline is wrapped by a governance layer so it can be operated as a managed
application rather than a one-off script. Each governance function is backed by a
concrete artifact the pipeline emits: an audit trail (rationales + source tags),
reproducibility control (seed, temperature policy, model roster, input hash),
cost & usage monitoring, reliability monitoring (CV threshold violations), a
versioned assumption registry, and a human-in-the-loop review gate.

---

## Repository structure

```
.
├── notebooks/
│   ├── 00_setup_and_data.ipynb            Foundation: API, schema, loaders, LLM utils
│   ├── 01_agent1_task_extraction.ipynb    Agent 1 — extraction + automatability grading
│   ├── 015_agent1_5_process_graph.ipynb   Agent 2 — AS-IS / TO-BE process graph
│   ├── 02_agent2_time_estimation.ipynb    Agent 3 — time estimation (Self-Consistency)
│   ├── 03_agent3_roi_computation.ipynb    Agent 4 — ROI + sensitivity analysis
│   ├── 04_five_axis_validation.ipynb      Five-axis validation framework
│   ├── 05_dashboard_and_figures.ipynb     Consolidated HTML dashboard
│   ├── 06_paper_figures.ipynb             Publication-quality data-driven figures
│   ├── 07_cross_domain_demonstration.ipynb Transferability across domains + appendix export
│   ├── 08_governance_report.ipynb         Governance-layer consolidation
│   ├── RUN_EXPERIMENT.ipynb               Model-tier sweep (single self-contained cell)
│   └── 09_tier_sweep_aggregation.ipynb    Tier-sweep aggregation → paper tables
├── data/
│   └── raw/
│       ├── interview_<case>.txt           Input interview transcripts
│       └── ground_truth_<case>.json       Partial expert reference (Accuracy axis)
├── experiments/                           Tier-sweep protocol, results, and helpers
├── artifacts/                             Generated outputs (see below)
├── requirements.txt
└── README.md
```

> **Note on agent numbering.** The notebook filenames retain their original
> `agent1 / agent1_5 / agent2 / agent3` stems for stable ordering, but the
> manuscript numbers the four agents sequentially as **Agent 1 (extraction),
> Agent 2 (process graph), Agent 3 (time estimation), Agent 4 (ROI)**. The
> mapping is given in the structure above.

Generated under `artifacts/`: per-agent JSON (`inference/`), paper tables
(`tables/`), figures (`figures/`), the governance report (`governance/`),
appendix assets (`appendix/`), a cost ledger, a run manifest, and an HTML
dashboard.

---

## Cases

The primary demonstration is a technology-credit evaluation interview. Three
further interviews from unrelated domains (hospital billing, legal contract
review, manufacturing settlement) exercise **transferability**. A fifth
interview — an R&D patent-drafting process — is included as a **quality-uplift**
case: one where the value of adoption is improved output quality at unchanged
human effort rather than time saved. It motivates a value-model extension of the
effort-based ROI and is not part of the transferability check.

---

## Getting started

### Requirements

- Python 3.10+
- An OpenAI API key
- Packages in `requirements.txt`

```bash
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your_key_here
LLM_MODEL_WEAK=gpt-4o-mini
LLM_MODEL_MID=<your mid-tier model>
LLM_MODEL_STRONG=<your strong-tier model>
```

Model pricing for the three tiers is recorded in `artifacts/run_manifest.json`
and is used by the efficiency axis; update it if your rates differ.

### Running the pipeline

Execute the notebooks in order:

```
00 → 01 → 015 → 02 → 03 → 04 → 05 → 06 → 07 → 08
```

Notebook 00 writes a run manifest that later notebooks read, so each notebook is
otherwise self-contained. A single weak-tier pass is inexpensive. Extraction and
ROI run at temperature 0; only the Self-Consistency time-estimation stage samples
at a positive temperature.

### Running the model-tier study

Open `notebooks/RUN_EXPERIMENT.ipynb` (one self-contained cell), set the `CONFIG`
dict at the top (tiers, seeds, matcher tier), and Run All. It writes
`experiments/results/tier_comparison.json`; then run
`notebooks/09_tier_sweep_aggregation.ipynb` for the paper tables. For independent
repeats the cache is bypassed and the active seed is mixed into the cache key, so
the runs are genuinely independent — every tier × seed makes real API calls.

---

## Reproducibility

- Fixed random seed across all stages; the per-agent temperature policy, model
  roster, and an input-interview hash are recorded in the run manifest so a run
  can be repeated and its inputs verified.
- An assumption registry hashes all editable economic/behavioral parameters
  (cost model, priors, automation ratios) so any change is traceable.
- A single-pass illustrative run caches responses on disk
  (`artifacts/llm_cache/`) for cheap re-execution. The model-tier study
  deliberately **disables** this cache and salts cache keys by seed, so its five
  repeats per tier are independent rather than collapsing onto one cached result.

All monetary figures in the illustrative runs derive from prior/implied time
estimates; the sample interviews state no explicit durations or volumes. The
sensitivity analysis therefore reports an ROI **range** and a break-even point
rather than a single number.

---

## Data note

The interview transcripts and expert references included here are illustrative
examples used to demonstrate the method. They are provided solely so the pipeline
and its validation can be reproduced end-to-end.

---

## Anonymity note (for reviewers and re-uploaders)

This artifact is prepared for double-anonymous review. If you re-upload or fork
it, please ensure Git commit metadata (author name and email) does not
de-anonymize the authors, for example by committing under a neutral identity:

```bash
git config user.name "Anonymous"
git config user.email "anonymous@example.com"
```

---

## License

To be released under an open-source license upon publication. During anonymous
review, please treat this repository as review-only material.
