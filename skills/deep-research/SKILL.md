---
name: deep-research
description: Use for complex, contested, or fast-changing research requiring auditable evidence and calibrated uncertainty.
license: MIT
compatibility: Hermes Agent, Claude Code, Codex, and OpenCode with Python 3.11+, Git, shell access, and web retrieval
metadata:
  author: Brent Atchison (atchisonbrent), Helion
  version: "0.2.1" # x-release-version
---

# Deep Research

Produce durable, decision-grade research across technology, markets, companies, policy, law, science, security, history, product categories, forecasts, and modern events. This skill owns the procedure: framing, mode routing, mapping the evidence landscape, retrieval, source and claim assessment, synthesis, and review. The framework repository owns the methodology, schema, and `reportctl.py`, which captures source text, verifies quotations, and validates the report. The configured report vault owns actual reports and should normally remain private unless the user explicitly chooses public publication.

Two failures matter most, and most of this procedure exists to prevent them:

1. **Shallow retrieval presented as a finished answer.** A report can be accurate about everything it read and still be wrong because it did not read the studies, data series, or records a specialist would consider decisive. Map the evidence landscape first, search deliberately against your own conclusion, and do not declare a question unresolved until the evidence that could resolve it has actually been sought.
2. **Correct-looking artifacts that do not say what the sources say.** Citations that resolve and quotations that match prove correspondence, not support. Bind quotations to captured source text, anchor prose to claims, and have someone else audit a sample for meaning.

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

When the current agent exposes related skills, load `grounded-citations` for citation semantics, `arxiv` for scientific literature, `competitor-news-monitor` for a recurring company watch, and `product-buying-research` for live purchase decisions. Their absence is not fatal: apply the equivalent rules here and record any lost specialist coverage.

Resolve the report vault in this order: injected `deep_research.repository` configuration; `DEEP_RESEARCH_REPOSITORY`; the current repository when it contains `tools/reportctl.py`; then `~/workspace/research-reports`. Expand `~`, and set:

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
python3 "$TOOL" add-evidence --help >/dev/null || { echo "pinned framework predates add-evidence; update the vault's framework pin" >&2; exit 1; }
python3 "$TOOL" validate --help | grep -q -- --strict || { echo "pinned framework predates validate --strict" >&2; exit 1; }
python3 "$TOOL" fetch --help >/dev/null || { echo "pinned framework predates snapshot capture; update the vault's framework pin" >&2; exit 1; }
```

Require `$FRAMEWORK/METHODOLOGY.md`, `$FRAMEWORK/SCHEMA.md`, and `$FRAMEWORK/tools/reportctl.py`. The CLI takes a global `--root <vault>` (and optional `--json`) before the subcommand. If the framework is unavailable, stop before producing a supposedly durable report; do not hand-build substitute IDs, quotations, or a Sources block. The pinned schema and validator own the JSON shape; `$FRAMEWORK/schema/*.schema.json` is its machine-readable form. Never invent field names.

Completion: the repository, framework, report directory, and snapshot store are known before source collection.

## Quick Reference

```bash
R="python3 $TOOL --root $REPO"
REPORT="$REPO/reports/YYYY/MM/<slug>"

$R init --slug <slug> --title "<title>" --mode <mode> --domain <domain> --cutoff <ISO-8601-UTC>
$R log-search "$REPORT" --question 1 --purpose map --engine "<tool>" --query "<query>" --considered <n>
$R fetch "$REPORT" <url> --title "<title>"                     # capture text, register source
$R capture "$REPORT" <url> --from-file <text> --note "<how>"    # browser/PDF/archive text
$R add-evidence "$REPORT" <id> --snapshot latest --text "<verbatim>" --claim <C-ID> --location "<where>" --captured-at <ISO>
$R render-sources "$REPORT"
$R validate --strict --verify-snapshots "$REPORT"
$R audit-sample "$REPORT" --size 12 --out audit.json   # give to an independent judge
$R record-audit "$REPORT" --from-file audit.json --route "<judge>"
$R reader "$REPORT" --out reader.md                     # anchor-free text for PDF/HTML
$R index && $R index --check && $R scan-sensitive
$R due                                                  # hypotheses ready to score
```

Use the agent's web search for discovery and `fetch` for evidence. When `fetch` is blocked (403, consent wall, script-rendered page) or the source is a PDF without `pdftotext`, read it with a browser or extractor, save the text, and `capture` it with a note saying how. Try an archive snapshot when a page is gone and record the archive URL. If the agent has no web retrieval, stop with an explicit coverage gap rather than inventing current evidence.

`fetch` stores text in the private vault store (`<vault>/.snapshots/` or `$DEEP_RESEARCH_SNAPSHOTS`) by default; the vault must Git-ignore it, and `fetch` refuses otherwise. Use `--store report` only for text that may be redistributed—US federal government works, openly licensed papers, your own measurements—so it is committed beside the report.

## Procedure

### 1. Orient, choose a mode, and freeze the research contract

Read `$FRAMEWORK/METHODOLOGY.md`, `$FRAMEWORK/SCHEMA.md`, `reports/index.md`, `references/modes/README.md`, and any prior report on the subject. Get the current date/time from the shell. Pick one primary mode from `references/modes/README.md` and read that mode's file in full; it fixes the evidence hierarchy, decomposition pattern, gates, output sections, and completion criteria. Define:

- exact decision questions and intended use; mark the one or two **decisive** questions whose answers would most change the verdict;
- mode, domain, comparison class, geography, jurisdiction, and temporal scope;
- UTC cutoff, exclusions, volatile inputs, and whether this is a new report or a dated update. The cutoff closes the evidence window: `fetch` and `log-search` refuse later timestamps. Use a date-only cutoff for single-day work; for longer research, advance a draft's cutoff as retrieval continues and freeze it before synthesis.

**Prefer depth to breadth.** More than about five decision questions in one report usually means each is answered from a handful of sources. Split into linked reports, or state which questions receive full treatment and which are context. Spend effort on retrieval and reading before presentation formats.

Create the skeleton with `init --mode --domain`. Never silently revise an old report's cutoff or forecast to incorporate later knowledge.

Completion: `assessment.json` has real questions, mode, domain, scope and volatility boundaries; the mode file has been read.

### 2. Decompose conclusions before searching

Turn slogans into atomic candidate claims using the mode's decomposition pattern. Separate observed facts, attributed statements, inference, forecasts, and unknowns. For causal, intentional, strategic, or forecast questions, write the leading hypothesis, the strongest credible alternative, a mixed explanation where appropriate, and the insufficient-evidence possibility before deciding which is true. For descriptive landscapes and comparisons, use the mode's criteria matrix instead of manufacturing hypotheses. Apply mode gates as gates, not decoration.

Completion: initial claim IDs plus hypotheses or a criteria matrix exist; unresolved matrix cells have named `coverage_gaps` entries.

### 3. Map the evidence landscape before collecting

Before gathering support for anything, answer for each decision question: **what evidence would a specialist expect a serious answer to engage?** List it:

- the canonical studies, reviews, and meta-analyses (search scholarly indexes such as Google Scholar, SSRN, NBER, PubMed, or arXiv—not only the open web);
- the official data series, audits, filings, court records, budgets, and inspector-general or auditor reports that measure the thing directly;
- the most recent authoritative work, and whether it revises older findings;
- the best-informed advocates on each side and the evidence they rely on.

Log these as `map` searches with `log-search`. The map is a checklist: every listed item is later read, found unavailable (gap with its searches), or judged irrelevant with a reason. For empirical questions, follow citation trails backward from the strongest recent work and forward to newer work that cites it. When you catch yourself citing a summary—a CRS report, a literature review, a news account of a study—retrieve the underlying primary work for load-bearing uses.

Completion: each decision question has a logged evidence map that names concrete studies, datasets, or records, not just search terms.

### 4. Retrieve with provenance

Retrieve in parallel across the map and the mode's evidence hierarchy: primary records; independent reporting or analysis with its own evidence path; domain-specialist analysis with inspectable methods; stakeholder statements kept in attribution; and credible contradictory evidence.

`fetch` (or `capture`) every source you actually read; it stores the extracted text under its SHA-256 and registers the source. Log each substantive query with `log-search`, including how many results you inspected and which sources it yielded. Search results are discovery, not evidence: extract the page or mark `access: snippet`, and a snippet cannot support a load-bearing claim. Never hand-number IDs. Keep consulted sources in the ledger; `render-sources` publishes only cited IDs.

Write each source's assessment into `assessment.json` (access, type, directness, independence, incentives, limitations, publisher history, transparency). A source failure is a coverage gap, not negative evidence; retry load-bearing failures through a different route before concluding.

Completion: every read source has a snapshot or a recorded reason it could not be captured; the search log shows how sources were found.

### 5. Seek disconfirmation deliberately

For every load-bearing inference, forecast, and hypothesis, run at least one search designed to prove it wrong—log it with `--purpose counter`, record how many results you actually inspected, and link it through `counter_search_ids`. Look for the strongest opposing case as its best-informed proponents make it, later corrections, replications and failed replications, and evidence that would make the preferred story fail. Record what you find in `contradicting_source_ids`, even when you ultimately weigh it less.

Balance means symmetric search effort, not symmetric conclusions. If favorable and unfavorable evidence for a position were sought with different intensity, the report is biased regardless of its tone.

Completion: each load-bearing judgment shows either contradicting sources or a logged counter-search.

### 6. Map independence before counting corroboration

Assign every source an `independence_group` and `independence_rationale` based on its underlying evidence path. Syndicated copies, outlets repeating one briefing or leak, and analyses sharing one dataset or benchmark harness are one group unless shown otherwise. Do not average source ratings or count domains as votes; ten rewrites of one briefing remain one briefing.

### 7. Assess the publication, author, and particular claim separately

Source reputation sets a prior; the particular claim's evidence decides how far to move. A reputable outlet can publish a weak anonymous-source story; an interested party can supply authentic primary evidence. Read `references/reliability-rubric.md`. Author audits are optional—record `authors` only when a byline is visible and the author's expertise or record bears on a load-bearing claim; unknown author history is not low reliability, it is unknown. Never infer reliability from tone, nationality, politics, or employer prestige.

For `attributed` claims, `status` says whether the source said it. Also set `underlying_status`: whether what it said is established. "The agency reports 3,715 victims assisted" can be confirmed as attribution while the underlying figure remains only probable because it is self-reported and unaudited.

### 8. Attach evidence to atomic claims

For every load-bearing factual or attributed claim, attach at least one short verbatim excerpt through `add-evidence --snapshot`, which verifies the text against the stored snapshot and binds the quotation to that snapshot's hash. Use `kind: artifact` with a precise `location` for figures, table cells, dataset rows, and commits. `--from-file` remains for text you cannot capture as a snapshot, but it only proves the quotation appears in a file you supplied; `validate --strict` treats it as unfinished. Never paste a snippet, paraphrase into the quote field, or store full copyrighted articles in Git.

State rationale and falsifiers, list supporting and contradicting sources, preserve scope, date, denominator and attribution for numbers, and set `last_checked` to the real retrieval time. Validate after each substantial batch.

### 9. Pass the depth gate before synthesis

Stop and check before writing the verdict:

- Every evidence-map item is read, gapped with its searches, or dismissed with a reason.
- Every retrieved source is cited or has a `disposition` and `disposition_note`. A strong, recent, directly relevant source that you retrieved but are not using is a warning sign: either use it or say precisely why not.
- Every `missing-primary`, `access`, or `unresolved-contradiction` gap names the `search_ids` that tried to close it. Do not call the decisive question unresolved on the strength of searches you did not run.
- Load-bearing claims resting only on secondary sources have been traced to the primary work, or carry a `missing-primary` gap naming them.
- New searches are mostly returning evidence you already hold (saturation) for each decisive question. If not, keep going or narrow the report.

If the gate fails and time is exhausted, publish only with the unfinished items stated in the report's gaps section—never as a complete answer.

### 10. Synthesize without laundering uncertainty

Write the verdict first, then distinguish **Observed**, **Reported**, **Assessed**, **Forecast**, and **Unknown**. Separate specifications from useful performance, demos from shipped availability, benchmark wins from workload fit, correlation from causation, announced plans from execution, and enacted text from enforced rule. Personal accounts are not prevalence estimates; conditional risk is not a forecast.

**Anchor claims in the prose.** Where a passage asserts a load-bearing claim, place its ID after the citation: `…fell 24%.[2]{C3}`. The validator checks that anchored passages cite only sources the anchored claims list, and that factual claims cite their own support; `reader` strips anchors for presentation. Anchors make prose auditable: a reviewer can see what the passage was supposed to say.

If requirements change after synthesis, discard the stale verdict and rerun the mode's gates. If evidence after the cutoff is required, create a successor with `reportctl.py supersede`, which links lineage both ways; never silently advance the old cutoff or hand-edit status to `superseded`.

Assign hypothesis probability ranges only after the claim ledger exists; widen them when intent is private, sourcing is anonymous or dependent, or primary evidence is missing. Give each open hypothesis a `resolve_by` date on which it can be scored, or an `unresolvable_reason`. Record outcomes with `resolve`; never edit an old range. Read `calibration` before assigning new ranges in the same domain, remembering that a few scored outcomes are a ledger, not a calibration estimate.

Completion: a reader can identify what happened, what is inferred, what remains unknown, what evidence would change the judgment, and which claim each conclusion rests on.

### 11. Cite at the narrowest honest scope

When every sentence in a paragraph comes from the same source set, cite it **once at the paragraph end**. When a paragraph mixes sources, evidence categories, or your own analysis, cite the relevant sentence or clause directly—or split the paragraph. Use no more than three source IDs in one citation group. Never fix low coverage by copying paragraph citations onto every sentence; that creates dense but false attribution. Mark genuinely unsourced load-bearing judgment `[unverified]` and either research it or make the uncertainty explicit. Cite every data-bearing table row. Generate the Sources block with `render-sources`; never hand-type URLs.

### 12. Edit prose conservatively

Perform a restrained prose pass after synthesis and before validation and review; the user need not request it. When available, load the `humanizer` skill in embedded mode. Remove empty introductions, inflated framing, redundant conclusions, and awkward phrasing only where readability improves. Preserve supported claims, attribution, negation, uncertainty, legal distinctions, dates, quantities, denominators, populations, comparison classes, quotations, citation scope, **claim anchors**, tables, and mode-required headings. Do not invent facts, citations, or first-person experience. Edit report-body prose only. Keep the pre-edit draft as a recoverable revision, compare the result against it and the claim ledger, and reject any edit that changes meaning. Record the pre-edit revision and the comparison in the review notes.

### 13. Validate

Run, in order:

1. `render-sources`;
2. `validate`, then `validate --strict --verify-snapshots` where the snapshot store is present, and repair what they report—citation scope, anchors, provenance, depth, temporal and status/confidence coherence, placeholders;
3. `index` and `index --check`;
4. the framework unit tests, `scan-sensitive`, and `git diff --check`.

Warnings under `--strict` are unfinished work. Do not lower thresholds, remove required metadata, fabricate ranges, or bypass checks to make a draft pass. If a framework rule genuinely conflicts with a correct report, obtain framework-owner approval, change the framework with tests, publish it, and update the vault pin; preserve failed receipts and record the recovery separately.

### 14. Audit meaning, then challenge the whole

**Semantic audit.** Run `audit-sample` and give the packet to a judge other than the author—a different model family or a person. The judge decides, per item, whether the excerpt in its snapshot context supports the claim and whether the anchored prose says what the claim says, no more and no less. Record verdicts with `record-audit`; every problem verdict needs a disposition describing the repair. Report the audited sample size with any problem rate; it is an estimate, not a guarantee.

**Independent review.** For high-impact, contested, investment-relevant, architecture-shaping, or forecast-heavy research, obtain two lenses from a reviewer other than the author, through whatever bounded, credential-free route the agent provides. Freeze the cutoff and exact revision first; never give the reviewer credentials or secret material, answer on its behalf, or steer its verdict.

1. **Correspondence review** reads the report, assessment, ledger, snapshots or excerpts, and the prose-pass diff. It asks: do sources entail the prose; are sources double-counted; are ranges too narrow; are falsifiers missing; are categories conflated (benchmark/product, announcement/availability, correlation/causation, enacted/enforced, output/outcome)?
2. **Coverage review** gets web access and one job: **find what the research missed**—decisive studies, data series, records, or counter-evidence absent from the ledger. A reviewer confined to the supplied files cannot see omissions. Record it in `review.coverage_review` with `web_access`, the `missing_evidence` it named, and your disposition.

Verify every finding locally. If remediation changes a load-bearing conclusion, range, independence, or evidence chain, rerun review. Record the exact revision, route, findings disposition, re-review decision, and remaining uncertainty in `assessment.json.review`.

### 15. Publish as immutable-at-cutoff history

Inspect the complete diff, and verify that `origin` resolves to the intended repository with the **expected visibility** before any push. Default to a private vault; publishing report contents publicly requires explicit user intent after the sensitive-content scan. Build presentation formats from `reader` output. Commit, push, read back the exact remote revision, and require the repository's CI to succeed before claiming publication. Later knowledge goes in a linked successor; do not rewrite the old report into retrospective perfection. Back up the private snapshot store alongside the vault; without it, quotations can be checked only structurally.

## Pitfalls

- **Declaring "unknown" before searching.** An unresolved decisive question with no logged searches is an unfinished report, not a finding.
- **Found but unused.** Retrieving the best current study and citing an older summary instead is worse than never finding it.
- **Summaries of summaries.** A review or government explainer is a map to the primary literature, not a substitute for it on load-bearing points.
- **Outlet scorecards become astrology.** Evaluate a source's access, method, incentives, and this claim separately.
- **A primary source is direct, not neutral.** A vendor benchmark proves what the vendor measured; a roadmap proves an announced plan; an agency's own statistics prove what it reports.
- **Anonymous officials are not independent because two outlets quote them.**
- **Search results are discovery, not evidence.** Extract the page or mark snippet access.
- **Matching a quote is not supporting a claim.** The semantic audit exists because correspondence checks cannot read.
- **Probability precision can hide ignorance.** Use ranges and explain what widens them.
- **Citation coverage is not citation quality.**
- **Claims have different half-lives.** Preserve cutoff, label volatile inputs, and create dated updates.
- **The mode file is the contract, not a suggestion.** Read it before retrieval.
- **Private Git is not a secret dump.** Store short excerpts, hashes, and redistributable text—not credentials or full copyrighted articles.

## Verification

- [ ] UTC cutoff, mode, domain, questions, decisive questions, intended use, and volatile inputs are explicit; scope favors depth
- [ ] The mode file was read and its gates applied before ranking or synthesis
- [ ] Each decision question has a logged evidence map naming concrete studies, data, or records
- [ ] Every source actually read has a `fetch`/`capture` snapshot or a recorded reason it could not
- [ ] Each load-bearing inference, forecast, and hypothesis shows contradicting sources or a logged counter-search
- [ ] Independence groups prevent duplicate corroboration
- [ ] Load-bearing excerpts are snapshot-bound through `add-evidence --snapshot` (or declared `artifact` coordinates)
- [ ] Attributed claims distinguish attribution (`status`) from truth (`underlying_status`)
- [ ] Depth gate passed: map items closed, uncited sources dispositioned, searched gaps link searches, secondary-only claims traced or gapped
- [ ] Load-bearing claims are anchored in the prose; Observed/Reported/Assessed/Forecast/Unknown are distinguishable
- [ ] Open hypotheses carry `resolve_by` or `unresolvable_reason`
- [ ] `render-sources` produced the Sources block; `validate --strict --verify-snapshots`, index check, sensitive scan, framework tests, and `git diff --check` pass
- [ ] Semantic audit recorded with dispositions; consequential reports received correspondence and web-enabled coverage review
- [ ] Commit, push, remote state, CI, and snapshot-store backup were verified
