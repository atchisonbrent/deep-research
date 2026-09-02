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

Produce durable, decision-grade research across technology, markets, companies, policy, science, product categories, forecasts, and modern events. This skill owns question framing, mode-specific source strategy, source and author evaluation, claim decomposition, comparison, optional competing hypotheses, calibrated probability ranges, and report publication. `grounded-citations` supplies citation semantics; this repository owns source IDs, quote verification, methodology, schema, validator, tests, and CI. The configured report vault owns actual reports and should normally remain private unless the user explicitly chooses public publication.

## When to Use

- “What is actually happening?” about a current or contested event.
- “What is the state of this technology, market, company, scientific question, or policy?”
- “When is this AI model or product likely to launch, and what evidence supports the window?”
- “Compare these architectures, companies, approaches, or product categories beyond surface specifications.”
- “Build a durable market landscape or due-diligence report.”
- A topic is saturated with hype, marketing, propaganda, anonymous claims, rumors, copied reporting, or incomparable benchmarks.
- The user wants source reliability, author credibility, competing explanations, or likelihood estimates.
- A prior report needs a dated update.
- A substantial answer should remain browsable after the chat ends.

Do not use for a quick uncontested lookup, a conventional academic-paper writing workflow, or ordinary news aggregation. For “what exact product should I buy now?”, load `product-buying-research`: it owns live prices, exact SKUs, sellers, warranty, returns, and delivered cost. Use deep research when the product-category landscape, technology, durability evidence, or price/performance frontier itself deserves a durable report; the two skills may be stacked when both layers matter.

## Prerequisites

When the current agent exposes related skills, load `grounded-citations` for citation semantics before retrieval, `arxiv` for scientific literature, `competitor-news-monitor` when converting research into a recurring company watch, and `product-buying-research` for live purchase decisions. Their absence is not fatal: apply the equivalent evidence rules in this skill and record any lost specialist coverage. This is a cross-agent workflow over a self-contained repository contract. A separate report vault normally pins this public framework under `framework/`; the framework checkout itself may also be used as the vault.

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
python3 "$TOOL" --help
```

Require `$FRAMEWORK/METHODOLOGY.md`, `$FRAMEWORK/SCHEMA.md`, `$FRAMEWORK/docs/QUICKSTART.md`, and `$FRAMEWORK/tools/reportctl.py`. The required CLI contract is public and standard-library-only: global `--root <vault>` before the subcommand; `init`; `add-source`; `add-quote --from-file`; `render-sources`; `validate`; `index`; and `scan-sensitive`. If the framework or CLI contract is unavailable, stop before producing a supposedly durable report; do not hand-build substitute IDs or a Sources block.

Use the repository’s current methodology and schema as authoritative. This skill defines the procedure; report-specific truth belongs in the report repository, not in the skill.

Completion: the repository and report-local citation ledger paths are known before source collection.

## Quick Reference

```bash
REPO="<resolved deep_research.repository>"
REPORT="$REPO/reports/YYYY/MM/<slug>"
TOOL="$REPO/framework/tools/reportctl.py"
if ! test -f "$TOOL"; then TOOL="$REPO/tools/reportctl.py"; fi

python3 "$TOOL" --root "$REPO" init --slug <slug> --title "<title>" --mode <research-mode> --domain <domain> --cutoff <ISO-8601-UTC>
python3 "$TOOL" --root "$REPO" add-source "$REPORT" <url> --title "<title>" --accessed <ISO-date>
python3 "$TOOL" --root "$REPO" add-quote "$REPORT" <id> --text "<verbatim>" --from-file <fetched-text-file>
python3 "$TOOL" --root "$REPO" render-sources "$REPORT"
python3 "$TOOL" --root "$REPO" validate "$REPORT"
python3 "$TOOL" --root "$REPO" index
python3 "$TOOL" --root "$REPO" index --check
python3 "$TOOL" --root "$REPO" scan-sensitive
```

Invoke commands through the agent's shell tool. Use its web-search capability for discovery and its fetch/extract capability for actual page evidence. Use a browser only when extraction fails or dynamic content is load-bearing. Tool names differ across Hermes, Claude Code, Codex, and OpenCode; the evidence standard does not. If the active agent has no web retrieval, stop with an explicit coverage gap rather than inventing current evidence.

## Procedure

### 1. Orient, choose a mode, and freeze the research contract

Read `$FRAMEWORK/METHODOLOGY.md`, `$FRAMEWORK/SCHEMA.md`, `reports/index.md`, this skill's `references/research-modes.md`, and any prior report on the subject. Use `terminal` to obtain the current date/time; do not infer it. Define:

- exact decision questions and intended use;
- research mode and domain;
- comparison class, audience, geography, and temporal scope where relevant;
- UTC cutoff;
- excluded adjacent topics, products, markets, companies, or periods;
- what would materially change the verdict;
- which inputs are volatile enough to require refresh at decision time;
- whether this is a new report or dated update.

For comparative analysis with volatile availability, pricing, or exact options, also define hard constraints, soft preferences, minimum acceptable outcomes, and the common transaction basis. Put the comparison contract and criteria matrix in `report.md`; represent their factual premises and decision-relevant conclusions with the schema-defined claims, evidence, and coverage gaps in `assessment.json`. Do not invent assessment fields.

Create the report skeleton with the pinned framework’s `reportctl.py --root "$REPO" init`, including `--mode` and `--domain`. Never silently revise an old report’s cutoff or forecast to incorporate later knowledge.

Completion: `assessment.json` contains real questions, mode, domain, scope, and volatility boundaries, and the report directory exists.

For those volatile comparative analyses, treat the contract as a gate rather than decorative context. Before ranking anything, remove candidates that fail a hard requirement. Evaluate the complete simultaneous workload rather than isolated specifications: capacity, compatibility, operating constraints, and required quality must hold at the same time. A nominal capacity or benchmark does not prove useful workload fit. If nothing passes, report **no viable candidate within the comparison class** instead of manufacturing a winner. Represent that overall conclusion as an inference over one evidenced gate-failure claim per candidate, not as a magically confirmed universal negative.

### 2. Decompose conclusions before searching

Turn slogans and broad narratives into atomic candidate claims. Separate:

- observed events, specifications, measurements, filings, releases, or market facts;
- attributed statements;
- inferred capability, quality, motive, trajectory, or competitive position;
- outcome or decision relevance;
- future forecast;
- unknowns.

For causal, intentional, strategic, or forecast questions, write the leading hypothesis, strongest credible alternative, mixed explanation where appropriate, and insufficient-evidence possibility before deciding which is true. For descriptive landscapes and comparisons, use an explicit criteria matrix instead; do not manufacture dramatic hypotheses because the schema permits them.

Build every criteria matrix symmetrically. A criterion is load-bearing when a material change in it could change a gate outcome or verdict; list those criteria explicitly. For every retained candidate and load-bearing criterion, record exactly one of:

1. a value on the common unit, scope, and measurement basis;
2. a value normalized to that basis with the conversion or bounding rationale visible;
3. `N/A` with a reason the criterion does not apply; or
4. an unresolved comparison gap.

Never rank a measured value against silence. Record each unresolved cell in `assessment.json.coverage_gaps`, naming the candidate and criterion. If unresolved gaps dominate the load-bearing criteria, report **insufficient evidence to rank** and list the retained candidates and missing evidence instead of manufacturing a winner.

When an available measurement is only a proxy for the user's target concern, display the proxy and explain what it omits, but give it ranking weight only when every retained candidate has a proxy on one shared, mutually comparable basis—the same observable condition or a commonly normalized proxy. Otherwise treat the proxy-only cells as unresolved for ranking. A conservative lower bound may carry ranking weight only when its basis is condition-independent or demonstrably dominates the common condition; otherwise it is a gap. An `N/A` cell on a load-bearing criterion carries no ranking weight and means that criterion does not differentiate the candidate; if the criterion is a hard requirement, treat `N/A` as a re-check signal rather than a pass. If unresolved gaps in total dominate the load-bearing criteria, report **insufficient evidence to rank** and list the retained candidates and missing evidence. Include deltas from a declared baseline when they make material differences legible.

For transactional comparisons, load `product-buying-research` when available; it owns exact option, seller/provider, availability, checkout, and delivered-cost collection. Import that bounded transaction evidence into the durable report while deep research owns the eligibility gate and synthesis. Normalize dates or quantity, required protection or service tier, taxes, delivery or pickup, mandatory fees, essential extras, refundability, included usage, and foreseeable operating costs. A listed price can be registered with its scope, but it cannot support a load-bearing ranking until the common transaction basis is established. Never rank a pre-tax teaser against an all-in protected total. Stop before personal data, payment, terms acceptance, or any transaction commit.

Completion: initial claim IDs plus either hypotheses or a criteria matrix exist before synthesis; matrices live in `report.md`, and every unresolved cell has a named `coverage_gaps` entry.

### 3. Build a deliberately diverse source map

Retrieve in parallel across evidence classes:

1. mode-appropriate primary records: technical documentation, code and release history, filings, market data, benchmark artifacts, papers, patents, official records, or raw data;
2. independent reporting or analysis with its own evidence path;
3. domain-specialist analysis with inspectable methods;
4. owner, vendor, company, regulator, researcher, customer, participant, or other stakeholder statements;
5. credible contradictory evidence or alternative interpretation;
6. technical, scientific, financial, legal, operational, consumer, or policy specialists as the question requires.

Register each URL with the pinned framework’s `add-source` command immediately after retrieval. Never hand-number IDs or delete an uncited but genuinely consulted source merely to make the bibliography look tidy; the ledger and assessment may retain consulted sources while `render-sources` publishes only cited IDs. Then read `$FRAMEWORK/SCHEMA.md` and use `write_file` for a complete initial `assessment.json` or `patch` for a targeted update; the ledger owns citation identity and verified quotes, while `assessment.json` owns access, independence, source/author assessment, claims, evidence, hypotheses, gaps, and review state. Record `access: snippet` there when only a search description was read; a snippet cannot support a body-level claim. Never invent field names—the pinned schema and validator own the shape.

A source failure is a coverage gap, not negative evidence. Retry load-bearing failures through a different route before concluding.

For comparative options, treat identity as a load-bearing claim when the exact model, trim, generation, configuration, seller, provider, or service tier affects eligibility or value. Compare the listing or catalog label with authoritative specifications and inspectable identifiers, media, order/configuration details, or primary records. A platform category, badge, title, or seller assertion is not authentication by itself. Exclude an option when unresolved identity could make it fail a hard requirement; otherwise rank it only under the lowest verified capability and preserve the contradiction as a coverage gap.

Completion: each decision question has mode-appropriate primary evidence, an independent analysis or reporting path, and one sought contradiction or alternative interpretation—or a documented gap explaining why not.

### 4. Map independence before counting corroboration

Assign every source an `independence_group` based on its underlying evidence path. Treat these as one group unless proven distinct:

- syndicated copies of one wire report;
- outlets repeating one press release or official briefing;
- outlets repeating one launch leak, analyst note, benchmark result, roadmap, or supply-chain source;
- stories drawing from the same anonymous official;
- analyses using the same dataset, benchmark harness, market feed, customer sample, paper corpus, or imagery;
- reports sourced from one witness, stringer, leak, or social post.

Do not average source ratings or count domains as votes. Ten rewrites of one briefing remain one briefing.

Completion: every source has a defensible independence group, and corroboration claims rely on genuinely separate groups.

### 5. Assess the publication, author, and particular claim separately

For each source, write the schema-defined access, type, directness, incentives, limitations, transparency, and publisher history into `assessment.json` with `write_file` or `patch`. For authors:

- capture only visible bylines;
- research beat, role, relevant credentials, prior work, corrections, or documented failures when the author carries a load-bearing claim;
- attach retrievable evidence for expertise or track record;
- use `unknown` when this was not established;
- never infer reliability from tone, nationality, politics, employer prestige, or one apparently correct article.

A reputable outlet can publish a weak anonymous-source story. A partisan or interested source can provide authentic primary evidence. Source reputation affects prior confidence; the claim’s evidence determines the update.

Read `references/reliability-rubric.md` for the evaluation questions and prohibited shortcuts.

Completion: every source and load-bearing author has an explicit assessment or visible `unknown`, never an invented biography or universal truth score.

### 6. Attach evidence to atomic claims

Populate the schema-defined `claims` and short `evidence` excerpts in `assessment.json` with `write_file` or `patch`; validate after each substantial batch so malformed references do not compound. For every load-bearing factual or attributed claim:

- attach at least one short verbatim excerpt or public artifact coordinate;
- verify excerpts against fetched text before recording them;
- list supporting and contradicting source IDs;
- state rationale and falsifiers;
- set `last_checked` to the real cutoff/retrieval time;
- preserve scope, date, denominator, and attribution for numbers.

Use `reportctl.py add-quote --from-file` for cited sources when fetched text is available. It verifies case-sensitive wording with whitespace normalization. Add the separate claim-facing evidence record to `assessment.json`; the ledger proves quotation identity while the assessment declares what the quotation supports. Do not quote a snippet, paraphrase into the quote field, or store full copyrighted articles in Git.

Completion: the validator can trace every load-bearing factual claim to a source and evidence excerpt.

### 7. Synthesize without laundering uncertainty

Write the verdict first, then distinguish:

- **Observed** — inspectable evidence;
- **Reported** — attributed reporting;
- **Assessed** — synthesis or inference;
- **Forecast** — future expectation;
- **Unknown** — unavailable or contradictory evidence.

Separate specifications from useful performance, demos from shipped availability, benchmark wins from workload fit, market narratives from measured economics, correlation from causation, and announced plans from demonstrated execution. For motive questions, distinguish demonstrated decision chains from incentives and speculation.

If the user changes a hard requirement, intended use, workload, budget basis, or mandatory feature after synthesis, discard the stale draft verdict and rerun the eligibility gate, workload fit, normalized totals, and ranking. If no fresh evidence is needed, update the draft without changing its frozen cutoff. If evidence after the cutoff is required, create a dated successor report—even when the prior artifact is still draft—and connect `lineage.supersedes` and `lineage.superseded_by`; never silently advance the old cutoff or set status to `superseded` without a valid successor.

Assign hypothesis probability ranges only after the claim ledger exists. Widen ranges when private intent, anonymous sourcing, dependence, access restrictions, or missing primary evidence dominate. Include update triggers that would move the range.

Completion: a reader can identify what happened, what is inferred, what remains unknown, and what evidence would change the judgment.

### 8. Cite at the narrowest honest scope

When every sentence in a paragraph comes from the same source set, cite that set **once at the paragraph end**. Do not produce `[1]` after every sentence like a machine being paid by the bracket. When a paragraph mixes sources, evidence categories, or your own analysis, cite the relevant sentence or clause directly—or split the paragraph. Use no more than three source IDs in one citation group.

Never fix low citation coverage by copying all paragraph citations onto every sentence. That creates formally dense but semantically false attribution—the exact failure this workflow exists to prevent. Instead:

1. split compound or mixed-source claims;
2. identify the precise source scope: clause, sentence, paragraph, or table row;
3. cite once at the end of that honest scope;
4. mark genuinely unsourced load-bearing judgment `[unverified]` and either research it or make the uncertainty explicit.

Generate the Sources block mechanically with `reportctl.py render-sources`; never hand-number or hand-retype URLs.

Cite every data-bearing comparison-matrix and normalized-cost-table row at the narrowest honest scope. The validator treats table rows as independent citation units; a citation on the paragraph above does not cover them.

Completion: citation IDs are stable, scoped to the claims they support, semantically accurate, readable, and generated source URLs match the ledger.

### 9. Run both validation layers

Run deterministic checks in this order:

1. run `reportctl.py --root "$REPO" render-sources` to generate the cited subset mechanically;
2. run `reportctl.py --root "$REPO" validate` and repair semantic citation scope, unknown IDs, source-block drift, evidence/claim mismatches, independence errors, and over-citation;
3. regenerate and check `reports/index.md`;
4. run the pinned framework unit tests, `scan-sensitive`, and `git diff --check`.

Do not lower thresholds merely to make a draft pass. If a paragraph mixes evidence paths, cite locally or split it; if it uses one source set, cite once at the end. If a sentence is analytical judgment rather than externally checkable fact, classify it correctly rather than decorating it with irrelevant citations.

Completion: the pinned framework’s report validator, tests, index check, sensitive-content scan, and Git checks pass.

### 10. Independently challenge consequential work

For high-impact, high-cost, strongly contested, architecture-shaping, investment-relevant, or forecast-heavy research, load `quota-aware-independent-review` and `structured-agent-handoff`. Freeze the report cutoff and exact staged revision before review. The reviewer must run through the approved fresh, explicitly different-model route and receive only a bounded packet containing the methodology, report, assessment, and ledger—never credentials or secret material. The author/implementer may clarify scope but must not answer on the reviewer’s behalf or steer it toward a preferred verdict.

Ask the reviewer to find:

- missing alternatives or counter-evidence;
- double-counted dependence;
- unsupported source/author assumptions;
- claims whose evidence does not entail the prose;
- probability intervals that are too narrow;
- absent falsifiers or update triggers;
- category errors such as benchmark-to-product, announcement-to-availability, correlation-to-causation, or output-to-outcome conflation;
- hidden contradictions.

Verify every finding locally. If remediation changes a load-bearing conclusion, probability range, source independence, or evidence chain, rerun independent review.

Completion: `assessment.json.review` records the exact frozen revision, actual route, review status, findings disposition, re-review decision, and remaining uncertainty.

### 11. Publish as immutable-at-cutoff history

When available, load `safe-repository-automation`; otherwise apply its fail-closed publication invariants here. Update the generated index, inspect the complete diff, and verify that the configured `origin` resolves to the intended repository and that GitHub reports the **expected visibility** before any push. Default to a private vault. Publishing report contents publicly requires explicit user intent after the sensitive-content scan. Commit, push, read back the exact remote revision, and require the repository’s actual CI run to succeed before claiming publication. A later update links to the prior report and records what changed; it does not rewrite the old report into retrospective perfection.

Completion: local and remote branches match, CI is green, and the report is browsable from `reports/index.md`.

## Pitfalls

- **Outlet scorecards become astrology.** Evaluate a source’s history, author, access, method, incentives, and this claim separately.
- **Unknown author history is not low reliability.** It is unknown.
- **A primary source is direct, not neutral.** A vendor benchmark proves what the vendor measured under chosen conditions, not general usefulness; a roadmap proves an announced plan, not delivery.
- **Anonymous officials are not independent because two outlets quote them.** Map the underlying source path.
- **Search results are discovery, not evidence.** Extract the page or mark snippet access.
- **Probability precision can hide ignorance.** Use ranges and explain what widens them.
- **Citation coverage is not citation quality.** Never propagate a citation set across a paragraph to satisfy a counter.
- **Claims have different half-lives.** Preserve cutoff, label volatile prices, roadmaps, benchmarks, and market inputs, and create dated updates.
- **A requirement change invalidates more than one sentence.** Re-run eligibility, workload fit, totals, and ranking instead of appending a caveat to a stale verdict; preserve cutoff and lineage rules.
- **Advertised capacity is not workload fit.** Test all simultaneous people, cargo, compatibility, operating, and comfort constraints that matter to the decision.
- **A shared table can still be asymmetric.** Every load-bearing candidate/criterion cell needs a comparable value, declared normalization, justified N/A, or named unresolved gap; proxy-only cells are not secretly evidence.
- **Headline prices are not comparable totals.** Normalize transaction stage, required tiers, fees, taxes, logistics, refundability, and essential extras.
- **Catalog identity can be wrong.** Verify consequential model, trim, provider, and configuration claims against primary identifiers or preserve the contradiction as unresolved.
- **Private Git is not a secret dump.** Store short excerpts and public artifacts, not credentials, leaked secrets, or full copyrighted articles.

## Verification

- [ ] UTC cutoff, research mode, domain, questions, intended use, and volatile inputs are explicit
- [ ] Volatile comparative work records hard constraints, soft preferences, simultaneous workload, and minimum acceptable outcomes in `report.md`
- [ ] Every retained candidate/load-bearing-criterion cell has a common-basis value, declared normalization, justified N/A, or named unresolved gap
- [ ] Every unresolved matrix cell has a candidate-and-criterion entry in `assessment.json.coverage_gaps`
- [ ] Proxy measurements name the target concern and limitations and carry weight only on a common comparable basis; material deltas use a declared baseline
- [ ] Transactional comparisons use `product-buying-research` when available and share one decision-grade cost basis
- [ ] Consequential comparative-option identities are verified, conservatively bounded, or excluded
- [ ] Prior report and methodology were read
- [ ] Conclusions decomposed into atomic claims before synthesis
- [ ] Mode-appropriate primary, independent, specialist, stakeholder, and contradictory paths sought
- [ ] Independence groups prevent duplicate corroboration
- [ ] Publisher and author judgments have evidence or say `unknown`
- [ ] Every load-bearing factual claim has a short verified excerpt or artifact coordinate
- [ ] Observed, reported, assessed, forecast, and unknown are distinguishable
- [ ] Forecast/causal hypotheses use ranges, alternatives, basis claims, falsifiers, and update triggers; descriptive research uses a criteria matrix
- [ ] Material requirement changes triggered a full re-gate and a cutoff/lineage-correct draft or successor
- [ ] Citations were registered at retrieval and attached once per honest clause, sentence, paragraph, or table-row scope
- [ ] `render-sources` generated a Sources block matching the report’s cited subset
- [ ] Pinned `reportctl.py validate`, index check, sensitive scan, framework unit tests, and `git diff --check` pass
- [ ] Consequential reports received independent adversarial review
- [ ] Commit, push, remote state, and CI were verified
