---
name: deep-research
description: Use for complex, contested, or fast-changing research requiring auditable evidence and calibrated uncertainty.
license: MIT
compatibility: Hermes Agent, Claude Code, Codex, and OpenCode with Python 3.11+, Git, shell access, and web retrieval
metadata:
  author: Brent Atchison (atchisonbrent), Helion
  version: "0.1.7" # x-release-version
---

# Deep Research

Produce durable, decision-grade research across technology, markets, companies, policy, law, science, security, history, product categories, forecasts, and modern events. This skill owns question framing, mode routing, source and author evaluation, claim decomposition, competing hypotheses or criteria matrices, calibrated probability ranges, and report publication. The framework repository owns methodology, schema, source IDs, quote verification, validator, tests, and CI. The configured report vault owns actual reports and should normally remain private unless the user explicitly chooses public publication.

## When to Use

- "What is actually happening?" about a current, contested, or historical event.
- "What is the state of this technology, practice, market, company, scientific question, policy, or legal exposure?"
- "When is this model, product, or rule likely to ship, and what evidence supports the window?"
- "Compare these options against my requirements," or "map this product category."
- "Who or what is this organization, project, or public-role person, and can I rely on them?"
- "What happened in this breach or outage, and who did it?"
- Due diligence with a materiality threshold and go/no-go conditions.
- A topic saturated with hype, marketing, propaganda, anonymous claims, rumor, copied reporting, or incomparable benchmarks.
- A prior report needs a dated update, or a substantial answer should remain browsable after the chat ends.

Do not use for a quick uncontested lookup, a conventional academic-paper writing workflow, or ordinary news aggregation. For "what exact product should I buy now," load `product-buying-research`; it owns live prices, exact SKUs, sellers, warranty, returns, and delivered cost. The two skills stack when both the durable landscape and the expiring purchase decision matter.

## Prerequisites

When the current agent exposes related skills, load `grounded-citations` for citation semantics before retrieval, `arxiv` for scientific literature, `competitor-news-monitor` when converting research into a recurring company watch, and `product-buying-research` for live purchase decisions. Their absence is not fatal: apply the equivalent evidence rules here and record any lost specialist coverage. This is a cross-agent workflow over a self-contained repository contract.

Resolve the report vault in this order: injected `deep_research.repository` configuration when the agent supports it; `DEEP_RESEARCH_REPOSITORY`; the current repository when it contains `tools/reportctl.py`; then `~/workspace/research-reports`. Expand `~`, and set:

```bash
REPO="<resolved deep_research.repository>"
if test -f "$REPO/framework/tools/reportctl.py"; then
  FRAMEWORK="$REPO/framework"
elif test -f "$REPO/tools/reportctl.py"; then
  FRAMEWORK="$REPO"
else
  echo "deep-research framework not found" >&2
  exit 1
fi
TOOL="$FRAMEWORK/tools/reportctl.py"
test -f "$TOOL"
python3 "$TOOL" add-evidence --help >/dev/null || { echo "pinned framework predates add-evidence; update the vault's framework pin" >&2; exit 1; }
python3 "$TOOL" validate --help | grep -q -- --strict || { echo "pinned framework predates validate --strict" >&2; exit 1; }
```

Require `$FRAMEWORK/METHODOLOGY.md`, `$FRAMEWORK/SCHEMA.md`, `$FRAMEWORK/docs/QUICKSTART.md`, and `$FRAMEWORK/tools/reportctl.py`. The required CLI contract is public and standard-library-only: global `--root <vault>` (and optional `--json`) before the subcommand; `init`; `add-source`; `add-quote --from-file`; `add-evidence`; `render-sources`; `validate [--strict]`; `index`; `scan-sensitive`; `supersede`; `resolve`; and `calibration`. If the framework or CLI contract is unavailable, stop before producing a supposedly durable report; do not hand-build substitute IDs or a Sources block.

Use the repository's current methodology and schema as authoritative. This skill defines the procedure; mode-specific evidence hierarchies live in `references/modes/`; report-specific truth belongs in the report repository.

Completion: the repository, framework, and report-local citation ledger paths are known before source collection.

## Quick Reference

```bash
REPO="<resolved deep_research.repository>"
REPORT="$REPO/reports/YYYY/MM/<slug>"
TOOL="$REPO/framework/tools/reportctl.py"
if ! test -f "$TOOL"; then TOOL="$REPO/tools/reportctl.py"; fi

python3 "$TOOL" --root "$REPO" init --slug <slug> --title "<title>" --mode <research-mode> --domain <domain> --cutoff <ISO-8601-UTC>
python3 "$TOOL" --root "$REPO" add-source "$REPORT" <url> --title "<title>" --accessed <ISO-date>
python3 "$TOOL" --root "$REPO" add-evidence "$REPORT" <id> --text "<verbatim>" --from-file <fetched-text-file> --claim <CLAIM-ID> --location "<where>" --captured-at <ISO-8601-UTC>
python3 "$TOOL" --root "$REPO" render-sources "$REPORT"
python3 "$TOOL" --root "$REPO" validate "$REPORT"
python3 "$TOOL" --root "$REPO" validate --strict "$REPORT"
python3 "$TOOL" --root "$REPO" index
python3 "$TOOL" --root "$REPO" index --check
python3 "$TOOL" --root "$REPO" scan-sensitive
```

Invoke commands through the agent's shell tool. Use its web-search capability for discovery and its fetch/extract capability for actual page evidence; save fetched text to a file so `add-evidence` can verify excerpts against it. Use a browser only when extraction fails or dynamic content is load-bearing; when a page is blocked or paywalled, try an archive snapshot and record the archive URL as the retrieved source. Tool names differ across Hermes, Claude Code, Codex, and OpenCode; the evidence standard does not. If the active agent has no web retrieval, stop with an explicit coverage gap rather than inventing current evidence.

## Procedure

### 1. Orient, choose a mode, and freeze the research contract

Read `$FRAMEWORK/METHODOLOGY.md`, `$FRAMEWORK/SCHEMA.md`, `reports/index.md`, `references/modes/README.md`, and any prior report on the subject. Use the shell to obtain the current date/time; do not infer it. Pick one primary mode from the table in `references/modes/README.md` and read that mode's file in full; it defines the evidence hierarchy, decomposition pattern, gates, output sections, and completion criteria for the rest of this procedure. Define:

- exact decision questions and intended use;
- research mode and domain;
- comparison class, audience, geography, jurisdiction, and temporal scope where relevant;
- UTC cutoff;
- excluded adjacent topics, products, markets, companies, actors, or periods;
- what would materially change the verdict;
- which inputs are volatile enough to require refresh at decision time;
- whether this is a new report or a dated update.

Create the report skeleton with `reportctl.py --root "$REPO" init`, including `--mode` and `--domain`; it scaffolds the mode's output sections. Never silently revise an old report's cutoff or forecast to incorporate later knowledge.

Completion: `assessment.json` contains real questions, mode, domain, scope, and volatility boundaries; the report directory exists; the mode file has been read.

### 2. Decompose conclusions before searching

Turn slogans and broad narratives into atomic candidate claims using the mode's decomposition pattern. Separate:

- observed events, specifications, measurements, filings, releases, or market facts;
- attributed statements;
- inferred capability, quality, motive, trajectory, or competitive position;
- outcome or decision relevance;
- future forecast;
- unknowns.

For causal, intentional, strategic, or forecast questions, write the leading hypothesis, strongest credible alternative, mixed explanation where appropriate, and insufficient-evidence possibility before deciding which is true. For descriptive landscapes and comparisons, use the mode's criteria matrix or claim table instead; do not manufacture dramatic hypotheses because the schema permits them. Apply the mode gates from the mode file (eligibility gate and symmetric matrix for `comparative-analysis`, release ladder for `release-forecast`, identity resolution for `entity-background`, and so on) as gates, not decoration.

Completion: initial claim IDs plus either hypotheses or a criteria matrix exist before synthesis; matrices live in `report.md`, and every unresolved cell has a named `coverage_gaps` entry.

### 3. Build a deliberately diverse source map

Retrieve in parallel across the mode's evidence hierarchy, always including:

1. mode-appropriate primary records;
2. independent reporting or analysis with its own evidence path;
3. domain-specialist analysis with inspectable methods;
4. stakeholder statements kept in attribution;
5. credible contradictory evidence or alternative interpretation.

Register each URL with `add-source` immediately after retrieval and save the fetched text to a file. Never hand-number IDs or delete an uncited but genuinely consulted source merely to make the bibliography look tidy; the ledger and assessment may retain consulted sources while `render-sources` publishes only cited IDs. Then read `$FRAMEWORK/SCHEMA.md` and write a complete initial `assessment.json` (or patch a targeted update); the ledger owns citation identity and verified quotes, while `assessment.json` owns access, independence, source/author assessment, claims, evidence, hypotheses, gaps, and review state. Record `access: snippet` when only a search description was read; a snippet cannot support a load-bearing claim. Never invent field names—the pinned schema and validator own the shape.

A source failure is a coverage gap, not negative evidence. Retry load-bearing failures through a different route before concluding.

Completion: each decision question has mode-appropriate primary evidence, an independent analysis or reporting path, and one sought contradiction or alternative interpretation—or a documented gap explaining why not.

### 4. Map independence before counting corroboration

Assign every source an `independence_group` based on its underlying evidence path. Treat these as one group unless proven distinct:

- syndicated copies of one wire report;
- outlets repeating one press release, official briefing, launch leak, analyst note, benchmark result, roadmap, or supply-chain source;
- stories drawing from the same anonymous official, witness, stringer, leak, or social post;
- analyses using the same dataset, cohort, benchmark harness, market feed, customer sample, paper corpus, or imagery.

Do not average source ratings or count domains as votes. Ten rewrites of one briefing remain one briefing.

Completion: every source has a defensible independence group with a rationale, and corroboration claims rely on genuinely separate groups.

### 5. Assess the publication, author, and particular claim separately

For each source, write the schema-defined access, type, directness, incentives, limitations, transparency, and publisher history into `assessment.json`. For authors:

- capture only visible bylines;
- research beat, role, relevant credentials, prior work, corrections, or documented failures when the author carries a load-bearing claim;
- attach retrievable evidence for expertise or track record;
- use `unknown` when this was not established;
- never infer reliability from tone, nationality, politics, employer prestige, or one apparently correct article.

A reputable outlet can publish a weak anonymous-source story. A partisan or interested source can provide authentic primary evidence. Source reputation affects prior confidence; the claim's evidence determines the update. Read `references/reliability-rubric.md` for the evaluation questions and prohibited shortcuts.

Completion: every source and load-bearing author has an explicit assessment or visible `unknown`, never an invented biography or universal truth score.

### 6. Attach evidence to atomic claims

Populate the schema-defined `claims` and `evidence` in `assessment.json`; validate after each substantial batch so malformed references do not compound. For every load-bearing factual or attributed claim:

- attach at least one short verbatim excerpt or public artifact coordinate;
- list supporting and contradicting source IDs;
- state rationale and falsifiers;
- set `last_checked` to the real retrieval time, never later than the cutoff;
- preserve scope, date, denominator, and attribution for numbers.

Use `reportctl.py add-evidence --from-file` for every excerpt: it verifies case-sensitive wording with whitespace normalization against the fetched text, records the quote in the ledger, and appends the claim-facing evidence record in one step, so the validator can confirm the excerpt corresponds to a checked quotation. Keep the fetched text file under the report's `evidence/` directory; the command proves the quote is in that file, and Git history shows where the file came from. Use `add-quote --from-file` only when the evidence entry already exists. For non-text evidence—a figure, table cell, dataset row, or commit—write the evidence entry with `"kind": "artifact"` and a precise `location`. An `excerpt` without a verified ledger quote is a validation warning today and an error under `--strict`; never paste a snippet, paraphrase into the quote field, or store full copyrighted articles in Git.

Completion: the validator can trace every load-bearing factual claim to a source and verified excerpt or artifact coordinate.

### 7. Synthesize without laundering uncertainty

Write the verdict first, then distinguish:

- **Observed** — inspectable evidence;
- **Reported** — attributed reporting;
- **Assessed** — synthesis or inference;
- **Forecast** — future expectation;
- **Unknown** — unavailable or contradictory evidence.

Separate specifications from useful performance, demos from shipped availability, benchmark wins from workload fit, market narratives from measured economics, correlation from causation, announced plans from demonstrated execution, and enacted text from enforced rule. For motive questions, distinguish demonstrated decision chains from incentives and speculation.

If the user changes a hard requirement, intended use, scope, or mandatory criterion after synthesis, discard the stale draft verdict and rerun the mode's gates. If no fresh evidence is needed, update the draft without changing its frozen cutoff. If evidence after the cutoff is required, create a dated successor with `reportctl.py supersede <predecessor> --slug … --title … --cutoff …`—even when the prior artifact is still draft—which links `lineage.supersedes` and `lineage.superseded_by` and retires the predecessor; never silently advance the old cutoff or hand-edit status to `superseded`.

Assign hypothesis probability ranges only after the claim ledger exists. Widen ranges when private intent, anonymous sourcing, dependence, access restrictions, or missing primary evidence dominate. Every hypothesis names at least one credible alternative and observable update triggers. When a prior report's hypothesis has resolved, record it with `reportctl.py resolve … --outcome … --at …` rather than editing the old range, and read `reportctl.py calibration` before assigning new ranges in the same domain.

Completion: a reader can identify what happened, what is inferred, what remains unknown, and what evidence would change the judgment.

### 8. Cite at the narrowest honest scope

When every sentence in a paragraph comes from the same source set, cite that set **once at the paragraph end**. Do not produce `[1]` after every sentence like a machine being paid by the bracket. When a paragraph mixes sources, evidence categories, or your own analysis, cite the relevant sentence or clause directly—or split the paragraph. Use no more than three source IDs in one citation group.

Never fix low citation coverage by copying all paragraph citations onto every sentence. That creates formally dense but semantically false attribution—the exact failure this workflow exists to prevent. Instead:

1. split compound or mixed-source claims;
2. identify the precise source scope: clause, sentence, paragraph, or table row;
3. cite once at the end of that honest scope;
4. mark genuinely unsourced load-bearing judgment `[unverified]` and either research it or make the uncertainty explicit.

Generate the Sources block mechanically with `reportctl.py render-sources`; never hand-number or hand-retype URLs. Cite every data-bearing table row at the narrowest honest scope; the validator treats body rows as independent citation units and ignores header rows.

Completion: citation IDs are stable, scoped to the claims they support, semantically accurate, readable, and generated source URLs match the ledger.

### 9. Run both validation layers

Run deterministic checks in this order:

1. `reportctl.py --root "$REPO" render-sources` to generate the cited subset mechanically;
2. `reportctl.py --root "$REPO" validate` and repair semantic citation scope, unknown IDs, source-block drift, evidence/claim mismatches, independence errors, temporal incoherence, status/confidence incoherence, leftover placeholders, and over-citation; then `validate --strict` and treat any unverified-excerpt warning as work to finish, not noise;
3. regenerate and check `reports/index.md`;
4. run the pinned framework unit tests, `scan-sensitive`, and `git diff --check`.

Do not lower thresholds merely to make a draft pass. If a paragraph mixes evidence paths, cite locally or split it; if it uses one source set, cite once at the end. If a sentence is analytical judgment rather than externally checkable fact, classify it correctly rather than decorating it with irrelevant citations.

Completion: the pinned framework's report validator (including `--strict`), tests, index check, sensitive-content scan, and Git checks pass.

### 10. Independently challenge consequential work

For high-impact, high-cost, strongly contested, architecture-shaping, investment-relevant, or forecast-heavy research, obtain an independent review from a different model or a human reviewer through whatever bounded, credential-free route the current agent provides. Freeze the report cutoff and exact staged revision before review. The reviewer receives only the methodology, report, assessment, and ledger—never credentials or secret material. The author may clarify scope but must not answer on the reviewer's behalf or steer it toward a preferred verdict.

Ask the reviewer to find:

- missing alternatives or counter-evidence;
- double-counted dependence;
- unsupported source/author assumptions;
- claims whose evidence does not entail the prose;
- probability intervals that are too narrow;
- absent falsifiers or update triggers;
- category errors such as benchmark-to-product, announcement-to-availability, correlation-to-causation, enacted-to-enforced, or output-to-outcome conflation;
- hidden contradictions.

Verify every finding locally. If remediation changes a load-bearing conclusion, probability range, source independence, or evidence chain, rerun independent review.

Completion: `assessment.json.review` records the exact frozen revision, actual route, review status, findings disposition, re-review decision, and remaining uncertainty.

### 11. Publish as immutable-at-cutoff history

Update the generated index, inspect the complete diff, and verify that the configured `origin` resolves to the intended repository and that the host reports the **expected visibility** before any push. Default to a private vault. Publishing report contents publicly requires explicit user intent after the sensitive-content scan. Commit, push, read back the exact remote revision, and require the repository's actual CI run to succeed before claiming publication. A later update links to the prior report and records what changed; it does not rewrite the old report into retrospective perfection.

Completion: local and remote branches match, CI is green, and the report is browsable from `reports/index.md`.

## Pitfalls

- **Outlet scorecards become astrology.** Evaluate a source's history, author, access, method, incentives, and this claim separately.
- **Unknown author history is not low reliability.** It is unknown.
- **A primary source is direct, not neutral.** A vendor benchmark proves what the vendor measured under chosen conditions; a roadmap proves an announced plan; a filing proves the disclosed metric under its definition.
- **Anonymous officials are not independent because two outlets quote them.** Map the underlying source path.
- **Search results are discovery, not evidence.** Extract the page or mark snippet access.
- **Probability precision can hide ignorance.** Use ranges and explain what widens them.
- **Citation coverage is not citation quality.** Never propagate a citation set across a paragraph to satisfy a counter.
- **Claims have different half-lives.** Preserve cutoff, label volatile inputs, and create dated updates.
- **A requirement change invalidates more than one sentence.** Rerun the mode's gates instead of appending a caveat; preserve cutoff and lineage rules.
- **The mode file is the contract, not a suggestion.** Its gates decide eligibility, ranking weight, and what counts as primary; read it before retrieval, not after.
- **Private Git is not a secret dump.** Store short excerpts and public artifacts, not credentials, leaked secrets, or full copyrighted articles.

## Verification

- [ ] UTC cutoff, research mode, domain, questions, intended use, and volatile inputs are explicit
- [ ] The mode's reference file was read and its gates were applied before ranking or synthesis
- [ ] Prior report and methodology were read
- [ ] Conclusions decomposed into atomic claims before synthesis
- [ ] Mode-appropriate primary, independent, specialist, stakeholder, and contradictory paths sought
- [ ] Independence groups prevent duplicate corroboration
- [ ] Publisher and author judgments have evidence or say `unknown`
- [ ] Every load-bearing factual claim has a short excerpt verified through `add-evidence`/`add-quote`, or a declared `artifact` coordinate; `validate --strict` passes
- [ ] Observed, reported, assessed, forecast, and unknown are distinguishable
- [ ] Forecast/causal hypotheses use ranges, alternatives, basis claims, falsifiers, and update triggers; descriptive research uses a criteria matrix or claim table
- [ ] Every unresolved matrix cell or missing evidence path has a `coverage_gaps` entry
- [ ] Material requirement changes triggered a full re-gate and a cutoff/lineage-correct draft or successor
- [ ] Citations were registered at retrieval and attached once per honest clause, sentence, paragraph, or table-row scope
- [ ] `render-sources` generated a Sources block matching the report's cited subset
- [ ] Pinned `reportctl.py validate`, index check, sensitive scan, framework unit tests, and `git diff --check` pass
- [ ] Consequential reports received independent adversarial review
- [ ] Commit, push, remote state, and CI were verified
