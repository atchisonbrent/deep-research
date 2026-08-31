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

`add-quote` verifies and records the ledger excerpt. You must still add the claim-facing `evidence` record in `assessment.json`, naming the source ID, supported claim IDs, location, and capture date. The ledger proves quotation identity; the assessment explains what that quotation supports.

## 5. Draft and render citations

Use `[1]`, `[2]`, and so on in `report.md`. When an entire paragraph uses the same source set, cite once at the paragraph end. Mixed-source paragraphs need sentence- or clause-local citations. Put a citation at the end of every data-bearing table row.

Generate the Sources block mechanically:

```bash
python3 tools/reportctl.py render-sources "$REPORT"
```

## 6. Validate

```bash
python3 tools/reportctl.py validate "$REPORT"
python3 tools/reportctl.py index
python3 tools/reportctl.py index --check
python3 tools/reportctl.py scan-sensitive
python3 -m unittest discover -s tests -v
git diff --check
```

The validator checks source/claim/evidence integrity, independence-aware confidence guardrails, citation scope and coverage, report lineage, review state, and forecast requirements. Passing validation means the report satisfies the declared audit contract—not that Python has proven the report true.

## 7. Publish or integrate

The included GitHub Actions workflow runs the same checks on pushes and pull requests. Other agents and applications can consume:

- `report.md` for human-readable analysis;
- `assessment.json` for claims, evidence, confidence, hypotheses, and gaps;
- `sources-ledger.json` for stable citation identity.

To integrate with another agent, instruct it to read `AGENTS.md`, `METHODOLOGY.md`, and `SCHEMA.md`, use `reportctl.py` rather than hand-generating source IDs, and preserve cutoffs when creating updates.
