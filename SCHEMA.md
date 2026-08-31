# Report Schema

`assessment.json` is the machine-readable audit trail behind `report.md`.

## Top-level fields

- `schema_version`: currently `1`.
- `report`: identity, research mode, domain, dates, cutoff, status, lineage, questions, and summary.
- `sources`: detailed source and author assessments keyed by numeric citation ID.
- `claims`: atomic factual, inferential, forecast, or unknown propositions.
- `evidence`: short excerpts or artifact coordinates tied to claims.
- `hypotheses`: competing explanations with probability ranges and update triggers.
- `coverage_gaps`: known missing evidence or access limitations.
- `review`: deterministic and independent review state.

## Controlled values

### Report status

`draft`, `reviewed`, `superseded`

`reviewed` requires a passed independent review record. `superseded` requires a `lineage.superseded_by` target. Lineage values are repository-relative report directories under `reports/`; the validator checks that they exist and that successor cutoffs move forward.

### Research mode

`general`, `event-assessment`, `technology-landscape`, `market-analysis`, `company-research`, `release-forecast`, `policy-analysis`, `scientific-synthesis`, `comparative-analysis`, `product-landscape`, `due-diligence`

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

Each hypothesis also retains a `resolution` object. It begins as `open`; a later update may mark it `resolved` with an outcome and date or `superseded` by a better-framed hypothesis. This preserves misses and creates an actual calibration record instead of a museum of unscored forecasts.

All values are between 0 and 1 and ordered. Ranges communicate epistemic uncertainty; they are not mechanically calculated source-vote totals.

## Independence

Every source has an `independence_group`. Sources that rely on the same wire story, official briefing, press release, dataset, image provider, witness, or leaked document share a group. Different URLs are not presumed independent.

Every group assignment also carries `independence_rationale`. A confirmed load-bearing fact or attributed event must have either a full direct source or two distinct independence groups. Single-group indirect claims cannot exceed 0.95 confidence and must retain an interval at least 0.15 wide. These are guardrails against false corroboration, not a mechanical probability formula.

## Author evidence

Per-author expertise remains `unknown` unless `expertise_evidence` explains the basis. A `high` aggregate author-expertise rating requires at least one public `expertise_url`. An empty author list forces author expertise and track record to `unknown`; publisher prestige cannot silently stand in for a byline audit.

## Evidence excerpts

Evidence entries contain short public excerpts or artifact coordinates—not full articles. Each entry names one source and one or more claims. The validator checks referential integrity; the research workflow must verify verbatim text against retrieved source material before publication.

An evidence source must also appear in every claim it supports. This prevents a quote from one source being attached to a claim whose declared source set says something else.

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

## Review state

`review.independent_review` is one of `not-run`, `passed`, `findings`, or `blocked`. A report may remain `draft` with any of those states. Setting `report.status` to `reviewed` requires `independent_review: passed` plus:

- `exact_revision`: immutable reviewed Git revision or staged-diff identity;
- `route`: reviewer/model/process used;
- `findings_disposition`: list showing how findings were handled;
- `rereview_required`: boolean recording whether later material changes invalidate the pass;
- `notes`: remaining uncertainty and review scope.
