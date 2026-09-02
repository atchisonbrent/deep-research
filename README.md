# Deep Research

An open framework for AI-assisted, versioned, evidence-backed deep research across technology, practice, markets, companies, people and organizations, policy, law, science, security, history, products, forecasts, and modern events. Sixteen research modes each carry their own evidence hierarchy, gates, and report skeleton.

This repository is designed for:

- **People**, who need a decision-grade answer without replaying the news cycle or rediscovering an entire technical or market landscape.
- **Research agents and automation**, which need a durable, machine-readable evidence and uncertainty record that can be updated without rediscovering prior work.

## What this is

This project has two cooperating parts:

1. **An Agent Skills research workflow** for Hermes Agent, Claude Code, Codex, and OpenCode. The AI agent frames the question, retrieves and reads sources, evaluates authors and evidence, decomposes claims, considers alternatives, assigns justified confidence ranges, and writes the report.
2. **A Python evidence and validation framework.** `reportctl.py` creates report scaffolding, maintains stable source IDs, verifies quoted text against supplied source extracts, renders citations, checks the structured claim/evidence graph, enforces selected confidence guardrails, scans for sensitive material, and validates the finished artifact.

**Python does not perform the research or grade truth automatically.** It does not browse the web, decide whether Reuters or a named researcher is trustworthy, infer source independence, assign probabilities, or write the verdict. Those are analytical judgments made by the AI agent—or by a human using the same schema. Python checks that those judgments are explicit, internally consistent, traceable to evidence, and within the framework's declared guardrails.

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
- excerpt evidence matches a quotation that was verified against fetched source text, or is declared a non-text artifact;
- timestamps do not postdate the report cutoff, and claim status agrees with its confidence interval;
- forecast reports contain hypotheses, ranges, alternatives, and update triggers;
- source, report-lineage, review-state, and sensitive-content rules are satisfied.

It cannot establish that a source is actually independent merely because an analyst labeled it so, that an excerpt entails the conclusion, or that a probability range is objectively correct. Those remain reviewable analytical judgments. The structured files make the judgments inspectable instead of hiding them in fluent prose.

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
