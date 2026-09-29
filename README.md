# Deep Research

An open framework for AI-assisted, versioned, evidence-backed deep research across technology, practice, markets, companies, people and organizations, policy, law, science, security, history, products, forecasts, and modern events. Sixteen research modes each carry their own evidence hierarchy, gates, and report skeleton.

This repository is designed for:

- **People**, who need a decision-grade answer without replaying the news cycle or rediscovering an entire technical or market landscape.
- **Research agents and automation**, which need a durable, machine-readable evidence and uncertainty record that can be updated without rediscovering prior work.

## What this is

This project has two cooperating parts:

1. **An Agent Skills research workflow** for Hermes Agent, Claude Code, Codex, and OpenCode. The AI agent frames the question, retrieves and reads sources, evaluates authors and evidence, decomposes claims, considers alternatives, assigns justified confidence ranges, and writes the report.
2. **A Python evidence and validation framework.** `reportctl.py` creates report scaffolding, retrieves and hashes source text, binds quotations to that captured text, keeps a search log, maintains stable source IDs, renders citations, checks the claim/evidence graph and the prose-to-claim anchors, enforces confidence and research-depth guardrails, draws samples for semantic audit, scans for sensitive material, and validates the finished artifact.

**Python records and checks; it does not judge.** It fetches the pages the agent chooses and records exactly what they said, but it does not choose what to search for, decide whether Reuters or a named researcher is trustworthy, infer source independence, assign probabilities, decide whether an excerpt supports a claim, or write the verdict. Those are analytical judgments made by the AI agent—or by a human using the same schema—and audited by an independent reviewer. Python makes those judgments explicit, traceable to captured evidence, and within declared guardrails.

The deterministic tooling is Python-standard-library-only. An AI agent is required for the intended automated research experience; without one, the repository is a manual research template and validator rather than an autonomous researcher. Start with [`docs/QUICKSTART.md`](docs/QUICKSTART.md).

The reusable cross-agent skill is public at [`skills/deep-research/`](skills/deep-research/). It defines the research workflow and mode routing; the framework CLI enforces the durable report contract.

The same Agent Skills package works with **Hermes Agent, Claude Code, Codex, and OpenCode**. See [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md). From any clone, install all user-level adapters from the **latest published release**:

```bash
python3 tools/install-latest.py
```

The bootstrapper asks GitHub for the latest published SemVer release, verifies the remote tag's commit, checks that exact tag out under `~/.local/share/deep-research/releases/`, and links consumers to that versioned release checkout. It never silently installs an arbitrary `main` revision.

**Releases:** [latest](https://github.com/atchisonbrent/deep-research/releases/latest). See [`RELEASING.md`](RELEASING.md) for the eager release contract and [`CHANGELOG.md`](CHANGELOG.md) for version history.

This repository contains the **public machinery**, not anyone’s private research archive. Clone or fork it directly for public reports, or pin it as a submodule inside a private report vault and run `reportctl.py --root <vault>`.

## Report contract

Each consumer report is a self-contained directory:

```text
reports/YYYY/MM/<slug>/
├── report.md             # readable verdict and analysis
├── assessment.json       # claims, evidence, hypotheses, confidence, gaps
├── sources-ledger.json   # stable numeric citation IDs and URLs
└── evidence/             # optional short excerpts or public artifacts
```

The repository deliberately does **not** assign universal truth scores to outlets. Reliability is assessed at the claim level using source directness, independence, access, author expertise, transparency, incentives, corroboration, and contradictions.

## Example output

The public repository includes a real [Iran war six-month assessment](examples/iran-war-six-month-assessment/report.md), plus its [structured assessment](examples/iran-war-six-month-assessment/assessment.json) and [source ledger](examples/iran-war-six-month-assessment/sources-ledger.json). It is preserved at its stated cutoff rather than silently updated after the fact. It predates framework 0.2.0, so it passes `validate` but not `validate --strict`: its evidence excerpts were recorded before ledger-quote verification existed, and backfilling those quotes without re-retrieving the sources would manufacture verification records. New reports are held to the strict bar; the fixture under `tests/fixtures/minimal-report` shows the strict-clean shape.

Consumer vaults keep their own reports chronological and retain each original cutoff. Material updates create a linked update instead of silently rewriting what was knowable earlier.

## Create a report

```bash
python3 tools/reportctl.py init \
  --slug next-frontier-models \
  --title "Likely next frontier model releases" \
  --mode release-forecast \
  --domain artificial-intelligence \
  --cutoff 2026-08-31T10:49:00Z
```

Log searches, capture what you read, and bind excerpts to the captured text:

```bash
REPORT=reports/2026/08/next-frontier-models
python3 tools/reportctl.py log-search "$REPORT" --question 1 --purpose map \
  --engine "Google Scholar" --query "frontier model release cadence" --considered 15
python3 tools/reportctl.py fetch "$REPORT" https://example.com/source --title "Example source"
python3 tools/reportctl.py add-evidence "$REPORT" 1 --snapshot latest \
  --text "Exact source wording" --claim C1 --location "section 2" --captured-at 2026-08-31T10:00:00Z
```

Then complete `assessment.json`, draft `report.md` with claim anchors (`…wording.[1]{C1}`), and validate:

```bash
python3 tools/reportctl.py render-sources "$REPORT"
python3 tools/reportctl.py validate --strict --verify-snapshots "$REPORT"
python3 tools/reportctl.py audit-sample "$REPORT" --size 12 --out audit.json   # for an independent judge
python3 tools/reportctl.py index
python3 tools/reportctl.py scan-sensitive
python3 -m unittest discover -s tests -v
```

Snapshots live in the `.snapshots/` store (or `$DEEP_RESEARCH_SNAPSHOTS`), which must be Git-ignored—`fetch` refuses to write it otherwise—unless `--store report` commits redistributable text beside the report. PDF retrieval uses `pdftotext` (poppler) when installed; otherwise extract the text another way and `capture` it.

## AI-agent integration

Install or link `skills/deep-research/` into a supported agent's skill directory, then point the workflow at either:

- a private report vault containing this repository as `framework/`; or
- this framework checkout itself, if the reports are intentionally public.

See [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md) for Hermes Agent, Claude Code, Codex, and OpenCode locations and invocation syntax. The workflow defaults to a private report vault. It requires explicit user intent before publishing report contents publicly; making the methodology public does not make anyone's research archive public.

## What the validator can and cannot establish

The validator can establish facts about the **research artifact**, such as:

- every referenced source and claim ID exists;
- load-bearing factual claims have supporting sources and short evidence excerpts;
- a claim marked `confirmed` has either full direct evidence or two declared independence groups;
- a single indirect evidence group cannot receive an implausibly narrow or greater-than-95% confidence range;
- citations resolve and cover the prose/table units they are attached to;
- a quotation bound to a snapshot appears in stored source text whose hash matches the ledger, and that text has not been edited since capture (`--verify-snapshots` requires the text to be present);
- a passage anchored to a claim cites only that claim's sources, and every load-bearing claim is asserted somewhere in the prose;
- each question was searched, load-bearing judgments were searched against, gaps link the searches that tried to close them, and retrieved-but-unused sources carry a stated reason;
- under `validate --strict`, every excerpt is snapshot-bound and every depth, anchor, calibration and review rule is satisfied rather than merely warned about;
- timestamps do not postdate the report cutoff, and claim status agrees with its confidence interval;
- forecast reports contain hypotheses, ranges, alternatives, and update triggers;
- source, report-lineage, review-state, and sensitive-content rules are satisfied.

It cannot establish that a source is actually independent merely because an analyst labeled it so, that an excerpt entails the conclusion or the prose is faithful to its claim, that a `capture` file really came from the registered URL, that the searches logged were the right ones, that an `artifact` label was deserved, or that a probability range is objectively correct. Those remain analytical judgments. The entailment audit estimates how often the first two fail on a sample, and a web-enabled coverage review looks for what the searches missed. The structured files make the judgments inspectable instead of hiding them in fluent prose.

## Method

Read [`METHODOLOGY.md`](METHODOLOGY.md) before treating a confidence range as meaningful. The short version:

1. define the exact questions, research mode, domain, and cutoff;
2. decompose narratives into atomic claims;
3. map the evidence a specialist would expect, then retrieve primary records and independent reporting, capturing what you read;
4. record source and author limitations explicitly;
5. cluster syndicated or dependent reports so they do not masquerade as corroboration;
6. separate observations, inferences, forecasts, and unknowns;
7. assign probability ranges to hypotheses only after the claim ledger exists;
8. search deliberately against your own conclusion, and preserve contradictions and update triggers;
9. do not call a decisive question unresolved until the evidence that could resolve it has been sought;
10. validate, then have someone else audit a sample for meaning and search for what you missed.

## Security and copyright

Private or public, the repository must not contain credentials, private personal data, leaked secret material, or unredacted source dumps. Prefer short evidence excerpts plus URLs, dates, hashes, and public archival references. Do not commit full copyrighted articles merely because extraction made it easy.
