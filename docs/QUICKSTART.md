# Quickstart

The deterministic report tooling runs with **Python 3.11+ and Git only**. That tooling does **not** conduct research autonomously: it does not retrieve sources, assess credibility, assign probabilities, or write conclusions. For the intended automated workflow, use the included skill with Hermes Agent, Claude Code, Codex, or OpenCode. Without an AI agent, a human can still fill the report schema manually and use Python to manage citations and validate the artifact.

## 1. Clone and test

```bash
git clone https://github.com/atchisonbrent/deep-research.git
cd deep-research
python3 -m unittest discover -s tests -v
```

There are no third-party Python dependencies.

To inspect a complete real-world artifact before creating your own, open [`examples/iran-war-six-month-assessment/report.md`](../examples/iran-war-six-month-assessment/report.md) alongside its `assessment.json` and `sources-ledger.json`.

For Claude Code, Codex, OpenCode, and Hermes installation, see [`INTEGRATIONS.md`](INTEGRATIONS.md).

The supported default is `python3 tools/install-latest.py`, which installs from GitHub's latest published release into a versioned local checkout. Direct `install-skill.py install` calls are for exact tagged checkouts; unreleased development installs require `--allow-unreleased`.

### Private report vault with public machinery

Keep actual reports in a separate private repository and pin this framework:

```bash
git submodule add https://github.com/atchisonbrent/deep-research.git framework
git commit -m "chore: pin deep-research framework"
```

Run commands from the private vault with:

```bash
python3 framework/tools/reportctl.py --root . <command> ...
```

The submodule commit makes validation reproducible. Updating the framework is a reviewed dependency change; reports remain private.

## 2. Initialize a report

This creates a deliberately incomplete scaffold. It is not a generated research result. An AI agent or human researcher must replace the placeholders after collecting and evaluating evidence.

```bash
python3 tools/reportctl.py init \
  --slug next-frontier-models \
  --title "Likely next frontier model releases" \
  --mode release-forecast \
  --domain artificial-intelligence \
  --cutoff 2026-08-31T10:49:00Z
```

The command prints the created directory and creates:

- `report.md`
- `assessment.json`
- `sources-ledger.json`
- `evidence/`

Read `METHODOLOGY.md` and `SCHEMA.md` before assigning confidence.

## 3. Register sources

```bash
REPORT=reports/2026/08/next-frontier-models

python3 tools/reportctl.py add-source "$REPORT" \
  https://example.com/source \
  --title "Example source" \
  --accessed 2026-08-31
```

The command prints a stable numeric source ID. Registering the same URL again returns the existing ID.

Populate the matching detailed source record in `assessment.json`: publisher, author evidence, source type, access, directness, independence group and rationale, incentives, limitations, and reliability dimensions. These values are analyst judgments supported by evidence; `reportctl.py` validates their shape and downstream consistency but does not invent or independently score them.

## 4. Verify a short quotation

Save or extract the source text to a local file, then attach an excerpt:

```bash
python3 tools/reportctl.py add-quote "$REPORT" 1 \
  --text "Exact wording copied from the source." \
  --from-file /path/to/extracted-source.txt
```

The command refuses text not found in the evidence file. Do not commit full copyrighted source dumps; keep short excerpts in the ledger/assessment and URLs to public originals.

`add-quote` verifies and records the ledger excerpt only. The preferred one-step path is `add-evidence`, which verifies the quotation, records it in the ledger, and appends the claim-facing `evidence` record in `assessment.json` so the two stay in agreement:

```bash
python3 tools/reportctl.py add-evidence "$REPORT" 1 \
  --text "Exact wording copied from the source." \
  --from-file /path/to/extracted-source.txt \
  --claim C1 --claim C2 \
  --location "section 3, paragraph 2" \
  --captured-at 2026-08-31T10:00:00Z
```

The claim must already list the source in its `source_ids`. For non-text evidence (a figure, a specification-table cell, a commit), write the `evidence` entry by hand with `"kind": "artifact"` and a precise `location`; artifacts are exempt from the ledger-quote match. Any `excerpt`-kind entry without a verified ledger quote produces a validation warning; `validate --strict` promotes warnings to errors.

## 5. Draft and render citations

Use `[1]`, `[2]`, and so on in `report.md`. When an entire paragraph uses the same source set, cite once at the paragraph end. Mixed-source paragraphs need sentence- or clause-local citations. Put a citation at the end of every data-bearing table row.

Generate the Sources block mechanically:

```bash
python3 tools/reportctl.py render-sources "$REPORT"
```

## 6. Validate

```bash
python3 tools/reportctl.py validate "$REPORT"
python3 tools/reportctl.py validate --strict "$REPORT"   # warnings become errors
python3 tools/reportctl.py --json validate "$REPORT"     # machine-readable result
python3 tools/reportctl.py index
python3 tools/reportctl.py index --check
python3 tools/reportctl.py scan-sensitive
python3 -m unittest discover -s tests -v
git diff --check
```

The validator checks source/claim/evidence integrity, independence-aware confidence guardrails, citation scope and coverage, report lineage, review state, and forecast requirements. Passing validation means the report satisfies the declared audit contract—not that Python has proven the report true.

## 7. Update, score, and calibrate

When new evidence arrives after a report's cutoff, do not edit the old report. Create a linked successor:

```bash
python3 tools/reportctl.py supersede reports/2026/08/next-frontier-models \
  --slug next-frontier-models-2026-10 \
  --title "Likely next frontier model releases — October update" \
  --cutoff 2026-10-01T00:00:00Z
```

When a hypothesis resolves, record the outcome without touching its original range, then review calibration across the vault:

```bash
python3 tools/reportctl.py resolve reports/2026/08/next-frontier-models H1 --outcome true --at 2026-10-15
python3 tools/reportctl.py calibration
```

## 8. Publish or integrate

The included GitHub Actions workflow runs the same checks on pushes and pull requests. Other agents and applications can consume:

- `report.md` for human-readable analysis;
- `assessment.json` for claims, evidence, confidence, hypotheses, and gaps;
- `sources-ledger.json` for stable citation identity.

To integrate with another agent, instruct it to read `AGENTS.md`, `METHODOLOGY.md`, and `SCHEMA.md`, use `reportctl.py` rather than hand-generating source IDs, and preserve cutoffs when creating updates.
