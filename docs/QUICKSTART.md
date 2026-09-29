# Quickstart

The deterministic report tooling runs with **Python 3.11+ and Git only** (plus `pdftotext` from poppler if you want `fetch` to read PDFs). That tooling does **not** conduct research autonomously: it retrieves and hashes the sources you point it at, but it does not choose what to search for, assess credibility, assign probabilities, or write conclusions. For the intended automated workflow, use the included skill with Hermes Agent, Claude Code, Codex, or OpenCode. Without an AI agent, a human can still fill the report schema manually and use Python to manage citations and validate the artifact.

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
echo .snapshots/ >> .gitignore   # private source-text store; never commit it
git add .gitignore
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

## 3. Map, search, and capture sources

Record every substantive search, starting with an evidence map of what a specialist would expect the report to engage:

```bash
REPORT=reports/2026/08/next-frontier-models

python3 tools/reportctl.py log-search "$REPORT" --question 1 --purpose map \
  --engine "Google Scholar" --query "frontier model release cadence" --considered 15 \
  --note "Canonical cadence analyses and vendor release histories to read"
```

Capture each source you actually read. `fetch` retrieves it, extracts text, stores it under its SHA-256, and registers the source:

```bash
python3 tools/reportctl.py fetch "$REPORT" https://example.com/source --title "Example source"
```

When a site blocks scripted retrieval, renders with JavaScript, or serves a PDF without `pdftotext` installed, extract the text another way (a browser, a PDF tool, an archive copy) and record it:

```bash
python3 tools/reportctl.py capture "$REPORT" https://example.com/source \
  --from-file /tmp/source.txt --note "browser render after consent wall"
```

Snapshots go to the private `.snapshots/` store at the vault root (override with `DEEP_RESEARCH_SNAPSHOTS`). A private vault must ignore it—`echo .snapshots/ >> .gitignore`—and `fetch`/`capture` refuse to write an unignored store inside a Git work tree. Add `--store report` only for text you may redistribute, such as US federal government works; it is then committed under the report's `evidence/snapshots/`.

Populate the matching source record in `assessment.json`: publisher, source type, access, directness, independence group and rationale, incentives, limitations, and reliability. Author audits are optional. `reportctl.py` validates shape and consistency but does not score sources. Sources you retrieve but do not cite need a `disposition` and `disposition_note`.

## 4. Attach verified excerpts

```bash
python3 tools/reportctl.py add-evidence "$REPORT" 1 --snapshot latest \
  --text "Exact wording copied from the source." \
  --claim C1 --claim C2 \
  --location "section 3, paragraph 2" \
  --captured-at 2026-08-31T10:00:00Z
```

The command refuses text absent from the snapshot, records the quotation in the ledger bound to the snapshot hash, and appends the claim-facing `evidence` record. The claim must already list the source in its `source_ids`. `--from-file` accepts an arbitrary text file instead, but such quotations are unbound and fail `validate --strict`. For non-text evidence (a figure, a table cell, a commit), write the entry by hand with `"kind": "artifact"` and a precise `location`.

Run at least one `--purpose counter` search for each load-bearing inference, forecast and hypothesis, record how many results you inspected with `--considered`, and link it through `counter_search_ids`. Record contradicting sources you find even when you weigh them less.

## 5. Draft and render citations

Use `[1]`, `[2]`, and so on in `report.md`. When an entire paragraph uses the same source set, cite once at the paragraph end. Mixed-source paragraphs need sentence- or clause-local citations. Put a citation at the end of every data-bearing table row.

Anchor each load-bearing claim where the prose asserts it, after the citation: `…fell 24%.[2]{C3}`. Build PDFs and HTML from `python3 tools/reportctl.py reader "$REPORT" --out reader.md`, which removes anchors.

Generate the Sources block mechanically:

```bash
python3 tools/reportctl.py render-sources "$REPORT"
```

## 6. Validate

```bash
python3 tools/reportctl.py validate "$REPORT"
python3 tools/reportctl.py validate --strict --verify-snapshots "$REPORT"   # warnings become errors; snapshots re-verified
python3 tools/reportctl.py --json validate "$REPORT"     # machine-readable result
python3 tools/reportctl.py index
python3 tools/reportctl.py index --check
python3 tools/reportctl.py scan-sensitive
python3 -m unittest discover -s tests -v
git diff --check
```

The validator checks source/claim/evidence integrity, snapshot provenance, claim anchors, independence-aware confidence guardrails, research-depth records, citation scope and coverage, report lineage, review state, and forecast requirements. Passing validation means the report satisfies the declared audit contract—not that Python has proven the report true.

## 7. Audit meaning

Draw a reproducible sample and give it to a judge other than the author (a different model family or a person):

```bash
python3 tools/reportctl.py audit-sample "$REPORT" --size 12 --out audit.json
# the judge fills excerpt_verdict / prose_verdict / note for each item
python3 tools/reportctl.py record-audit "$REPORT" --from-file audit.json --route "<judge and route>"
```

Every problem verdict needs a `disposition` describing the repair. For consequential reports, also obtain a coverage review from a reviewer with web access whose only task is finding decisive evidence the research missed, and record it in `review.coverage_review`.

## 8. Update, score, and calibrate

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
python3 tools/reportctl.py due    # open hypotheses whose resolve_by date has arrived
```

## 9. Publish or integrate

The included GitHub Actions workflow runs the same checks on pushes and pull requests. Other agents and applications can consume:

- `report.md` for human-readable analysis;
- `assessment.json` for claims, evidence, confidence, hypotheses, and gaps;
- `sources-ledger.json` for stable citation identity.

To integrate with another agent, instruct it to read `AGENTS.md`, `METHODOLOGY.md`, and `SCHEMA.md`, use `reportctl.py` rather than hand-generating source IDs, and preserve cutoffs when creating updates.
