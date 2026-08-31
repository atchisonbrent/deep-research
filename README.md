# Deep Research

An open, standard-library-only framework for versioned, evidence-backed deep research across technology, markets, companies, policy, science, products, forecasts, and modern events.

This repository is designed for:

- **People**, who need a decision-grade answer without replaying the news cycle or rediscovering an entire technical or market landscape.
- **Research agents and automation**, which need a durable, machine-readable evidence and uncertainty record that can be updated without rediscovering prior work.

The core tool is Python-standard-library-only. Hermes Agent is an optional integration, not a runtime dependency. Start with [`docs/QUICKSTART.md`](docs/QUICKSTART.md).

The reusable Hermes skill is public at [`skills/deep-research/`](skills/deep-research/). It defines the research workflow and mode routing; the framework CLI enforces the durable report contract.

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

The public repository includes a real, validated [Iran war six-month assessment](examples/iran-war-six-month-assessment/report.md), plus its [structured assessment](examples/iran-war-six-month-assessment/assessment.json) and [source ledger](examples/iran-war-six-month-assessment/sources-ledger.json). It is preserved at its stated cutoff rather than silently updated after the fact.

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

Register sources and verify short excerpts without external tooling:

```bash
REPORT=reports/2026/08/next-frontier-models
python3 tools/reportctl.py add-source "$REPORT" \
  https://example.com/source --title "Example source" --accessed 2026-08-31
python3 tools/reportctl.py add-quote "$REPORT" 1 \
  --text "Exact source wording" --from-file /path/to/extracted-source.txt
```

Then complete `assessment.json`, draft `report.md`, and validate:

```bash
python3 tools/reportctl.py validate reports/2026/08/next-frontier-models
python3 tools/reportctl.py index
python3 tools/reportctl.py scan-sensitive
python3 -m unittest discover -s tests -v
```

## Hermes Agent skill

Install or link `skills/deep-research/` into your Hermes skills directory, then configure `deep_research.repository` to point at either:

- a private report vault containing this repository as `framework/`; or
- this framework checkout itself, if the reports are intentionally public.

The skill defaults to a private report vault. It requires explicit user intent before publishing report contents publicly; making the methodology public does not make anyone's research archive public.

## Method

Read [`METHODOLOGY.md`](METHODOLOGY.md) before treating a confidence range as meaningful. The short version:

1. define the exact questions, research mode, domain, and cutoff;
2. decompose narratives into atomic claims;
3. retrieve primary records and independent reporting;
4. record source and author limitations explicitly;
5. cluster syndicated or dependent reports so they do not masquerade as corroboration;
6. separate observations, inferences, forecasts, and unknowns;
7. assign probability ranges to hypotheses only after the claim ledger exists;
8. preserve contradictions and update triggers;
9. validate citations and structured evidence before publication.

## Security and copyright

Private or public, the repository must not contain credentials, private personal data, leaked secret material, or unredacted source dumps. Prefer short evidence excerpts plus URLs, dates, hashes, and public archival references. Do not commit full copyrighted articles merely because extraction made it easy.
