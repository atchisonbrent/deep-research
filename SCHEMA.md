# Report Schema

`assessment.json` is the machine-readable audit trail behind `report.md`.

## Top-level fields

- `schema_version`: currently `1`.
- `report`: identity, research mode, domain, dates, cutoff, status, lineage, questions, and summary.
- `sources`: detailed source and author assessments keyed by numeric citation ID.
- `claims`: atomic factual, inferential, forecast, or unknown propositions.
- `evidence`: short excerpts or artifact coordinates tied to claims.
- `hypotheses`: competing explanations with probability ranges and update triggers.
- `coverage_gaps`: known missing evidence or access limitations, as free text or structured objects (see below).
- `review`: deterministic and independent review state.

## Controlled values

### Report status

`draft`, `reviewed`, `superseded`

Scaffold placeholders from `init` (`Replace with …`) are rejected wherever they remain in `report.md`, `report.summary`, or `report.questions`.

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

Claims use a two-element `confidence` array: `[low, high]`.

Hypotheses use:

```json
{"low": 0.35, "central": 0.50, "high": 0.65}
```

Each hypothesis must name at least one credible `alternatives` entry; a hypothesis with no alternative is an assertion, not a hypothesis. Each hypothesis also retains a `resolution` object. It begins as `open`; a later update may mark it `resolved` with an outcome and date or `superseded` by a better-framed hypothesis. This preserves misses and creates an actual calibration record instead of a museum of unscored forecasts.

All values are between 0 and 1 and ordered. Ranges communicate epistemic uncertainty; they are not mechanically calculated source-vote totals.

## Independence

Every source has an `independence_group`. Sources that rely on the same wire story, official briefing, press release, dataset, image provider, witness, or leaked document share a group. Different URLs are not presumed independent.

Every group assignment also carries `independence_rationale`. A confirmed load-bearing fact or attributed event must have either a full direct source or two distinct independence groups. Single-group indirect claims cannot exceed 0.95 confidence and must retain an interval at least 0.15 wide. These are guardrails against false corroboration, not a mechanical probability formula.

## Author evidence

Per-author expertise remains `unknown` unless `expertise_evidence` explains the basis. A `high` aggregate author-expertise rating requires at least one public `expertise_url`. An empty author list forces author expertise and track record to `unknown`; publisher prestige cannot silently stand in for a byline audit.

## Evidence excerpts

Evidence entries contain short public excerpts or artifact coordinates—not full articles. Each entry names one source and one or more claims. The validator checks referential integrity; the research workflow must verify verbatim text against retrieved source material before publication.

Each entry carries a `kind`:

- `excerpt` (default when omitted): verbatim text from the source. The excerpt must match, after whitespace normalization, a `quotes[].text` entry recorded on the same source in `sources-ledger.json`. Those ledger quotes are written only by `reportctl.py add-quote --from-file` or `add-evidence`, both of which refuse text that is not found verbatim in the fetched source file. An unmatched excerpt is an advisory **warning** in schema 1 and becomes an error under `validate --strict` and in the next schema revision.
- `artifact`: a coordinate for non-text evidence—figure, table cell, dataset row, commit hash, timestamp in a recording, or a specification-table value. Artifacts are exempt from the ledger-quote match but must still name a precise `location`.

An evidence source must also appear in every claim it supports. This prevents a quote from one source being attached to a claim whose declared source set says something else.

## Temporal coherence

The cutoff is the report's epistemic boundary, so the validator rejects any `retrieved_at`, `captured_at`, or `last_checked` value later than `report.cutoff`, and any `published_at` later than its source's `retrieved_at`. Date-only values compare by calendar day.

## Status and confidence

Claim `status` and `confidence` must agree: `confirmed` requires low ≥ 0.80; `probable` requires low ≥ 0.50; `contested` requires high ≤ 0.90; `unsupported` requires high ≤ 0.50; `unknown` claims must span at least 0.30. These are coherence guardrails, not a formula for choosing the interval.

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

`kind` is one of `matrix-cell`, `access`, `missing-primary`, `unresolved-identity`, `unresolved-contradiction`, `not-researched`, `other`. `matrix-cell` gaps must name `candidate` and `criterion`; optional `claim_ids` must reference existing claims. Structured gaps let a successor report or a reviewer see exactly which cell, source, or identity was unresolved instead of parsing prose.

## Lifecycle commands

- `supersede <predecessor> --slug … --title … --cutoff …` creates a dated successor scaffold, copies the predecessor's questions, sets `lineage.supersedes`, and marks the predecessor `superseded` with `lineage.superseded_by`. The predecessor's cutoff and content are untouched.
- `resolve <report> <H-id> --outcome … --at …` records a hypothesis outcome without editing its probability range. Outcomes `true`/`false` (or yes/no, occurred/did-not-occur) also record a binary `outcome_value` used for scoring.
- `calibration` summarizes every hypothesis in the vault: open count, resolved count, Brier score over central estimates, and how many outcomes fell inside the stated interval. It is the reason ranges are recorded as numbers rather than adjectives.

## Review state

`review.independent_review` is one of `not-run`, `passed`, `findings`, or `blocked`. A report may remain `draft` with any of those states. Setting `report.status` to `reviewed` requires `independent_review: passed` plus:

- `exact_revision`: immutable reviewed Git revision or staged-diff identity;
- `route`: reviewer/model/process used;
- `findings_disposition`: list showing how findings were handled;
- `rereview_required`: boolean recording whether later material changes invalidate the pass;
- `notes`: remaining uncertainty and review scope.
