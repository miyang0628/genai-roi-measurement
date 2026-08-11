# genai-roi-measurement

Automating interview-based generative-AI ROI measurement: a domain-agnostic
three-agent pipeline with a five-axis validation framework.

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

1. A **three-agent procedural pipeline** that maps the ROI-measurement problem
   onto a sequence of specialized agents.
2. A **five-axis validation framework** for evaluating a judgment-type artifact
   whose ground truth is not immediately observable.

---

## The pipeline

| Stage | Agent | Technique | Role |
|-------|-------|-----------|------|
| 1   | Task Extraction & Automatability Classification | Chain-of-Thought | Extract work units; grade each `full` / `partial` / `manual` with a rationale |
| 1.5 | Process-Graph Construction | typed-graph induction | Assign shape types + edges; derive AS-IS and TO-BE process graphs |
| 2   | Work-Time Estimation | Self-Consistency | Estimate per-task time with source tags and reliability dispersion |
| 3   | ROI Computation & Sensitivity | ReAct (reason + code action) | Compute ROI in code; sweep three uncertain parameters |

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
│   ├── 00_setup_and_data.ipynb           Foundation: API, schema, loaders, LLM utils
│   ├── 01_agent1_task_extraction.ipynb   Agent 1 — extraction + automatability grading
│   ├── 015_agent1_5_process_graph.ipynb  Agent 1.5 — AS-IS / TO-BE process graph
│   ├── 02_agent2_time_estimation.ipynb   Agent 2 — time estimation (Self-Consistency)
│   ├── 03_agent3_roi_computation.ipynb    Agent 3 — ROI + sensitivity analysis
│   ├── 04_five_axis_validation.ipynb      Five-axis validation framework
│   ├── 05_dashboard_and_figures.ipynb     Consolidated HTML dashboard
│   ├── 06_paper_figures.ipynb             Publication-quality data-driven figures
│   ├── 07_cross_domain_demonstration.ipynb Transferability across domains + appendix export
│   └── 08_governance_report.ipynb         Governance-layer consolidation
├── data/
│   └── raw/
│       ├── interview_<case>.txt           Input interview transcripts
│       └── ground_truth_<case>.json       Partial expert reference (Accuracy axis)
├── artifacts/                             Generated outputs (see below)
├── requirements.txt
└── README.md
```

Generated under `artifacts/`: per-agent JSON (`inference/`), paper tables
(`tables/`), figures (`figures/`), the governance report (`governance/`),
appendix assets (`appendix/`), a cost ledger, a run manifest, and an HTML
dashboard.

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

The illustrative runs use the weak tier and cost only cents per full pass.
Responses are cached on disk (`artifacts/llm_cache/`), so re-runs are free.

### Running

Execute the notebooks in order:

```
00 → 01 → 015 → 02 → 03 → 04 → 05 → 06 → 07 → 08
```

Notebook 00 writes a run manifest that later notebooks read, so each notebook is
otherwise self-contained. A full weak-tier pass is inexpensive and reproducible
(fixed seed; deterministic temperature for extraction and ROI, sampled
temperature only for the Self-Consistency stage).

---

## Reproducibility

- Fixed random seed across all stages.
- Per-agent temperature policy recorded in the run manifest.
- On-disk response cache makes re-runs deterministic and free.
- An assumption registry hashes all editable economic/behavioral parameters
  (cost model, priors, automation ratios) so any change is traceable.

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
