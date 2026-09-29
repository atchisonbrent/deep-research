# Report Schema

`assessment.json` is the machine-readable audit trail behind `report.md`. [`schema/assessment.schema.json`](schema/assessment.schema.json) and [`schema/sources-ledger.schema.json`](schema/sources-ledger.schema.json) describe the same shapes as JSON Schema (draft 2020-12) for editors and agents. They are structural only; `reportctl.py validate` also enforces the cross-references, temporal order, coverage, anchor and guardrail rules below.

## Compatibility

`schema_version` describes the **shape** of `assessment.json`. Validity is decided by the pinned framework release: newer releases add rules (temporal coherence, status/confidence guardrails, snippet limits, placeholder rejection) that older reports may fail. Consumers pin an exact framework tag; a report is "valid" relative to that tag. Rule additions that would fail previously valid reports are released as a **minor** version bump (a breaking change under 0.x semantics) and called out in `CHANGELOG.md`; patch releases never turn a valid report invalid. Where a rule can be phased in, it ships first as a warning and becomes an error at the following minor version, as the unverified-excerpt rule does. The 0.2.0 hardening (temporal coherence, status/confidence guardrails, snippet limits, placeholder rejection, required hypothesis alternatives, frontmatter title check) shipped as immediate errors in that minor release after verifying every existing consumer report against it.

The 0.3.0 rules (snapshot-bound quotations, claim anchors, search log, sought counter-evidence, source dispositions, primary tracing, attribution/truth separation, hypothesis resolution dates, semantic audit and coverage review; see [Rule codes](#rule-codes)) ship as **warnings**, so `validate --strict` fails reports written before them while default `validate` still passes. Their structural errors—a malformed search log, a citation-adjacent anchor naming no claim, a quotation bound to an unrecorded or altered snapshot—are immediate errors, because they can arise only from content written for 0.3.0: pre-0.3.0 reports lack those fields, and anchor recognition deliberately ignores brace-wrapped text that is not placed like an anchor (see [Claim anchors](#claim-anchors)). A frozen v0.2.1 fixture in the test suite guards this.

## Top-level fields

- `schema_version`: currently `1`.
- `report`: identity, research mode, domain, dates, cutoff, status, lineage, questions, and summary.
- `sources`: detailed source and author assessments keyed by numeric citation ID.
- `claims`: atomic factual, inferential, forecast, or unknown propositions.
- `evidence`: short excerpts or artifact coordinates tied to claims.
- `hypotheses`: competing explanations with probability ranges, update triggers and resolution dates.
- `searches`: the search log—what was searched, where, why, and what it yielded.
- `coverage_gaps`: known missing evidence or access limitations, as free text or structured objects (see below).
- `review`: deterministic and independent review state.

## Controlled values

### Report status

`draft`, `reviewed`, `superseded`

Scaffold placeholders written by `init` carry an explicit marker (`[[deep-research placeholder]]`); the validator rejects that marker wherever it remains in `report.md`, `report.summary`, or `report.questions`. Ordinary prose that happens to say "replace with" is not affected, and pre-0.2.0 scaffolds without the marker are not detected.

`reviewed` requires a passed independent review record. `superseded` requires a `lineage.superseded_by` target. Lineage values are repository-relative report directories under `reports/`; the validator checks that they exist and that successor cutoffs move forward.

### Research mode

`general`, `event-assessment`, `historical-analysis`, `technology-landscape`, `state-of-practice`, `market-analysis`, `company-research`, `entity-background`, `release-forecast`, `policy-analysis`, `legal-regulatory`, `scientific-synthesis`, `security-incident`, `comparative-analysis`, `product-landscape`, `due-diligence`

Each mode has a reference file under `skills/deep-research/references/modes/` whose **Output sections** list is the `report.md` skeleton that `init --mode` scaffolds. `event-assessment`, `security-incident`, and `release-forecast` require at least one hypothesis; any report with a `forecast`-kind claim does too.

`domain` is a lowercase kebab-case label such as `artificial-intelligence`, `semiconductors`, `public-markets`, or `consumer-audio`. Reuse an existing domain label when possible so indexes do not fragment into `ai`, `AI`, and `artificial-intelligence`.

### Source access

`full`, `partial`, `snippet`

### Source type

`primary-record`, `wire-service`, `specialist`, `government`, `advocacy`, `analysis`, `social`, `technical-documentation`, `code-repository`, `benchmark`, `market-data`, `regulatory-filing`, `company-communication`, `academic-paper`, `patent`, `other`

### Directness

`direct`, `near-direct`, `secondary`, `commentary`

### Reliability dimensions

`high`, `medium`, `low`, `unknown`

### Claim kind

`fact`, `attributed`, `inference`, `forecast`, `unknown`

### Claim status

`confirmed`, `probable`, `contested`, `unsupported`, `unknown`

### Importance

`load-bearing`, `supporting`, `context`

## Probability ranges

Claims default to `confidence_mode: "quantitative"` (also the default when omitted)
and use a two-element `confidence` array: `[low, high]`.

Non-forecast claims may explicitly select `confidence_mode: "qualitative"`.
They must omit `confidence`, provide non-empty `confidence_limitations`, and
retain a non-empty rationale and a non-empty list of textual falsifiers.
`status` expresses the qualitative assessment; it is not a hidden probability.
Missing confidence without explicit opt-in remains an error. Forecast claims
and hypothesis probabilities remain numerical. Qualitative mode does not waive
source, independence-group-count, evidence, citation, cutoff or review checks. Numerical
status floors/ceilings and interval-width rules apply only to numerical ranges;
confirmed factual/attributed claims retain their evidence requirements in either mode.

Example fields on an otherwise complete non-forecast claim:

```json
{"confidence_mode": "qualitative", "confidence_limitations": "The primary record verifies what was reported, not its causal effect.", "rationale": "Direct record supports the bounded attribution.", "falsifiers": ["Correction or withdrawal of the record."]}
```

Hypotheses use:

```json
{"low": 0.35, "central": 0.50, "high": 0.65}
```

Each hypothesis must name at least one credible `alternatives` entry; a hypothesis with no alternative is an assertion, not a hypothesis. Each hypothesis also retains a `resolution` object. It begins as `open`; a later update may mark it `resolved` with an outcome and date, or `superseded` with the same fields, where `outcome` names the better-framed successor hypothesis and `resolved_at` records when scoring stopped. This preserves misses and creates an actual calibration record instead of a museum of unscored forecasts.

All values are between 0 and 1 and ordered. Ranges communicate epistemic uncertainty; they are not mechanically calculated source-vote totals.

## Independence

Every source has an `independence_group`. Sources that rely on the same wire story, official briefing, press release, dataset, image provider, witness, or leaked document share a group. Different URLs are not presumed independent.

Every group assignment also carries `independence_rationale`. A confirmed load-bearing fact or attributed event must have either a full direct source or two distinct independence groups. Single-group indirect claims cannot exceed 0.95 confidence and must retain an interval at least 0.15 wide. These are guardrails against false corroboration, not a mechanical probability formula.

## Author evidence

`authors` is optional; omit it when no byline audit was performed. `reliability.author_expertise` and `author_track_record` default to `unknown` when omitted. When an author is recorded, only `name` is required; `expertise_evidence`, `expertise_url`, `track_record_evidence` and `conflicts` are recorded when researched. A `high` aggregate author-expertise rating requires at least one public `expertise_url`. An empty or omitted author list forces author ratings to `unknown`; publisher prestige cannot silently stand in for a byline audit.

## Evidence excerpts

Evidence entries contain short public excerpts or artifact coordinates—not full articles. Each entry names one source and one or more claims. The validator checks referential integrity; the research workflow must verify verbatim text against retrieved source material before publication.

Each entry carries a `kind`:

- `excerpt` (default when omitted): verbatim text from the source. The excerpt must match, after whitespace normalization, a `quotes[].text` entry recorded on the same source in `sources-ledger.json`. Create those quotes with `reportctl.py add-evidence --snapshot` (see [Snapshots](#snapshots)). An unmatched excerpt is an advisory **warning** and an error under `validate --strict`.
- `artifact`: a coordinate for non-text evidence—figure, table cell, dataset row, commit hash, timestamp in a recording, or a specification-table value. Artifacts are exempt from the ledger-quote match but must still name a precise `location`.

**What this establishes, honestly.** For snapshot-bound quotations with the snapshot present, the validator proves the quotation appears in text whose hash matches the ledger record, and that the text has not been altered since capture. `fetch` records the final URL, HTTP status, content type and raw-response hash, so a retrieval is a tool observation rather than an analyst's claim. It still does not prove that a `capture` file came from the registered URL (its `note` says how it was obtained), that a page served the same text to everyone, that an excerpt *entails* its claim, or that an `artifact` label was deserved. Entailment is what the [entailment audit](#entailment-audit) samples. The framework makes fabrication effortful, visible and, for fetched text, checkable—not impossible.

An evidence source must also appear in every claim it supports. This prevents a quote from one source being attached to a claim whose declared source set says something else.

## Snapshots

A snapshot is the extracted text of a retrieved source, canonicalized (line endings, runs of spaces, blank lines) and stored as `<sha256>.txt` with a `<sha256>.json` metadata file. `reportctl.py fetch <report> <url>` retrieves HTML, plain text, JSON or XML with the standard library and PDFs through `pdftotext` when installed; `capture <report> <url> --from-file <text> --note …` records text obtained any other way. Both register the source when new and append a record to its ledger entry:

```json
{"id": 4, "url": "…", "title": "…", "accessed": "2026-09-20",
 "snapshots": [{"sha256": "3f2a…", "method": "fetch", "retrieved_at": "2026-09-20T14:03:11Z", "store": "vault",
                "final_url": "…", "status": 200, "content_type": "text/html; charset=utf-8", "raw_sha256": "9c1e…"}],
 "quotes": [{"text": "Fentanyl investigations decreased by 24 percent", "added": "2026-09-20", "snapshot": "3f2a…", "offset": 18234}]}
```

Stores are searched in order: `<report>/evidence/snapshots/` (committed; redistributable text only) and then `$DEEP_RESEARCH_SNAPSHOTS` or `<vault>/.snapshots/` (private and Git-ignored). `add-evidence --snapshot <digest|prefix|latest>` and `add-quote --snapshot …` refuse text absent from the snapshot and bind the quotation with `snapshot` and `offset`. `--from-file` remains available and records `file_sha256`, but such quotations are unbound.

`fetch` and `capture` refuse to write the private store when it sits inside a Git work tree that does not ignore it, so full source text cannot be committed by accident; add `.snapshots/` to the vault's `.gitignore` or point `DEEP_RESEARCH_SNAPSHOTS` outside the repository. Redirects are followed only to http(s) URLs. `scan-sensitive` skips the private store, which is not repository content.

During validation, a bound quotation whose snapshot is present is re-verified: the stored text must match its hash and contain the quotation. When the snapshot is absent (for example in CI without the private store), the binding is checked structurally and a note reports how many snapshots were unavailable; `validate --verify-snapshots` turns absence into an error. Snapshot `retrieved_at` may not follow the cutoff.

## Claim anchors

Report prose marks where it asserts a claim or hypothesis by placing its ID in braces directly after the citation group: `…fell 24%.[2]{C3}` or `[2]{C3,C5}`. A brace group of claim-pattern IDs is an anchor when it directly follows a citation group or another anchor, or when every ID in it names an existing claim or hypothesis (so `…below certainty {H1}.` also works). Other brace-wrapped text, such as `{JSON}` in ordinary prose, is left alone, and inline code and fenced code blocks are never anchors. Within a citation unit (paragraph, list item or table row) containing anchors:

- every anchor must name a claim or hypothesis (a hypothesis stands for its basis claims);
- every cited source must appear in an anchored claim's `source_ids` or `contradicting_source_ids`;
- a `fact` or `attributed` claim with sources must be cited through at least one of its own `source_ids`.

Load-bearing claims that appear nowhere in the prose produce a warning. Anchors are removed before citation-coverage and sentence checks, and `reportctl.py reader <report>` prints the report without them for presentation builds.

## Search log

`searches` records how evidence was found, so reviewers can audit coverage and selection:

```json
{"id": "S4", "question": 2, "purpose": "counter", "engine": "Google Scholar", "query": "Secure Communities crime null effect",
 "run_at": "2026-09-20T15:10:00Z", "results_considered": 20, "source_ids": [11, 76], "notes": "Found Treyger et al. and Hines–Peri."}
```

`purpose` is `map` (charting what evidence exists), `support`, `counter` (seeking disconfirmation), `primary` (tracing a summary to its source), `gap` (trying to close a coverage gap) or `update`. `question` is the 1-based report question served, or null. `source_ids` must be assessment sources. `reportctl.py log-search` appends entries with the next `S` ID. Run times may not follow the cutoff.

Claims and hypotheses reference counter-searches through `counter_search_ids`; coverage gaps reference the searches that tried to close them through `search_ids`.

## Research depth

These rules make depth reviewable without pretending to measure it:

- every report question should have at least one logged search;
- every load-bearing `inference` or `forecast` claim should list `contradicting_source_ids` or link a `counter` search, and every hypothesis should link a `counter` search; a counter-search counts only when `results_considered` is at least 1;
- `missing-primary`, `access` and `unresolved-contradiction` gaps should list `search_ids`;
- every assessment source that `report.md` does not cite should carry a `disposition` (`background-only`, `superseded-by-better-source`, `duplicate`, `irrelevant`, `failed-retrieval`, `rejected-unreliable`) with a `disposition_note`; `cited` is also accepted and must be true;
- a load-bearing claim supported only by `secondary` or `commentary` sources should be traced to primary evidence or named in a `missing-primary` gap's `claim_ids`.

## Attribution and truth

For `attributed` claims, `status` describes the attribution—did the named source say this? Record `underlying_status` (same vocabulary) for whether the attributed proposition is itself established. A confirmed attribution of an unaudited agency statistic is typically `status: confirmed`, `underlying_status: probable`.

## Temporal coherence

The cutoff is the report's epistemic boundary, so the validator rejects any `retrieved_at`, `captured_at`, or `last_checked` value later than `report.cutoff`, and any `published_at` later than its source's `retrieved_at`. The cutoff may not follow `report.updated`; it may follow `report.created`, because a draft is scaffolded before its evidence window closes. Snapshot retrievals and search runs are also bounded by the cutoff. Date-only values compare by calendar day.

## Status and confidence

For quantitative claims, `status` and `confidence` must agree: `confirmed` requires low ≥ 0.80; `probable` requires low ≥ 0.50; `contested` requires high ≤ 0.90; `unsupported` requires high ≤ 0.50; `unknown` claims must span at least 0.30. These are coherence guardrails, not a formula for choosing the interval.

## Access

A load-bearing `fact` or `attributed` claim cannot rest only on `snippet`-access sources. A snippet supports its literal text and nothing more.

## Citation ledger

`sources-ledger.json` uses the `grounded-citations` ledger format:

```json
{
  "version": 1,
  "sources": [
    {"id": 1, "url": "https://example.com", "title": "Example", "accessed": "2026-08-31"}
  ]
}
```

Every `assessment.json` source must match one ledger ID, URL, and title. Every numeric Markdown citation must resolve to the ledger. The ledger and assessment may retain consulted but uncited sources; `render-sources` includes only IDs actually cited by `report.md`. A single citation group may appear at the end of a paragraph when every sentence in that paragraph shares the same evidence; mixed-source paragraphs need sentence- or clause-local citations. Data-bearing table rows are independent citation units. The generated `## Sources` block must exactly match the cited subset.

## Coverage gaps

Each entry is either a non-empty string (accepted for compatibility) or an object:

```json
{"kind": "matrix-cell", "candidate": "Alpha", "criterion": "delivered cost", "description": "No all-in quote at cutoff.", "claim_ids": ["C7"]}
```

`kind` is one of `matrix-cell`, `access`, `missing-primary`, `unresolved-identity`, `unresolved-contradiction`, `not-researched`, `other`. `matrix-cell` gaps must name `candidate` and `criterion`; optional `claim_ids` must reference existing claims; optional `search_ids` must reference logged searches and are expected for `missing-primary`, `access` and `unresolved-contradiction`. Structured gaps let a successor report or a reviewer see exactly which cell, source, or identity was unresolved instead of parsing prose.

## Lifecycle commands

- `supersede <predecessor> --slug … --title … --cutoff …` creates a dated successor scaffold, copies the predecessor's questions, sets `lineage.supersedes`, and marks the predecessor `superseded` with `lineage.superseded_by`. The predecessor's cutoff and content are untouched.
- `resolve <report> <H-id> --outcome … --at …` records a hypothesis outcome without editing its probability range. Outcomes `true`/`false` (or yes/no, occurred/did-not-occur) also record a binary `outcome_value` used for scoring.
- `calibration` summarizes every hypothesis in the vault: open count, resolved count, Brier score over central estimates, and how many outcomes fell inside the stated interval. It is the reason ranges are recorded as numbers rather than adjectives. With fewer than 20 scored outcomes it says so; small samples cannot separate skill from luck.
- `due [--as-of …]` lists open hypotheses whose `resolve_by` has arrived.

Open hypotheses should carry `resolve_by` (an ISO date not before the cutoff on which the outcome can be observed) or, when no future observation can score them, an `unresolvable_reason`.

## Review state

`review.independent_review` is one of `not-run`, `passed`, `findings`, or `blocked`. A report may remain `draft` with any of those states. Setting `report.status` to `reviewed` requires `independent_review: passed` plus:

- `exact_revision`: immutable reviewed Git revision or staged-diff identity;
- `route`: reviewer/model/process used;
- `findings_disposition`: list showing how findings were handled;
- `rereview_required`: boolean recording whether later material changes invalidate the pass;
- `notes`: remaining uncertainty and review scope.

### Entailment audit

`review.entailment_audit` records a semantic check of a sample:

```json
{"route": "DeepSeek-V4.1-Flash via Hermes, no author steering", "audited_at": "2026-09-21T02:10:00Z", "seed": 81723, "population": 97,
 "items": [{"claim_id": "C3", "evidence_id": "E7", "excerpt_verdict": "supports", "prose_verdict": "overstates",
            "note": "Prose says 'caused'; the audit reports a decline alongside the shift.", "disposition": "Rewrote to 'alongside'."}]}
```

`audit-sample <report> --size N [--seed S] --out packet.json` draws load-bearing claim/evidence pairs first, includes each excerpt's surrounding snapshot text when available and every anchored passage for the claim, and leaves verdict fields empty. The judge fills `excerpt_verdict` (`supports`, `partial`, `contradicts`, `unrelated`, or null without an excerpt) and `prose_verdict` (`faithful`, `overstates`, `understates`, `contradicts`, `not-anchored`). `record-audit <report> --from-file packet.json --route …` stores the verdicts and reports problem counts. Any problem verdict requires a `disposition`.

### Coverage review

`review.coverage_review` records a review whose task is to find decisive evidence the research missed:

```json
{"route": "…", "web_access": true, "missing_evidence": ["EOIR in-absentia series", "Hines & Peri (2019)"], "disposition": "Both retrieved; see S12–S14, C40–C42."}
```

A `reviewed` report without an entailment audit, or without a coverage review that had web access, receives a warning.

## Rule codes

Validator messages for rules added in 0.3.0 start with a code:

| Code | Rule | Severity |
|---|---|---|
| P1 | ledger quotation not bound to a snapshot | warning |
| P2 | malformed snapshot record, or quotation bound to an unrecorded snapshot | error |
| P3 | stored snapshot altered, or bound quotation absent from it | error |
| P4 | bound snapshot missing locally under `--verify-snapshots` | error (flag only) |
| A1 | citation-adjacent anchor names no claim or hypothesis | error |
| A2 | anchored passage cites a foreign source, or a factual claim without its own support | error |
| A3 | load-bearing claim not anchored in the prose | warning |
| D1 | no search log, question without a search, or malformed search entry | warning / error when malformed |
| D2 | load-bearing judgment without contradicting sources or counter-search; unknown counter-search IDs | warning / error |
| D3 | searched-kind gap without `search_ids`; unknown search IDs | warning / error |
| D4 | retrieved source neither cited nor dispositioned; invalid disposition | warning / error |
| D5 | load-bearing claim resting only on secondary/commentary sources | warning |
| D6 | load-bearing attributed claim without `underlying_status`; invalid value | warning / error |
| C1 | open hypothesis without `resolve_by` or `unresolvable_reason`; invalid date | warning / error |
| R1 | reviewed report without entailment audit; malformed audit or undispositioned problem | warning / error |
| R2 | reviewed report without web-enabled coverage review; malformed record | warning / error |
