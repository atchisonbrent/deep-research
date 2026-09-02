# Deep Research Methodology

## Objective

Produce the best-supported decision-grade answer to a substantial research question while making the evidence chain, uncertainty, source dependence, analytical judgment, and likely failure modes visible.

The method applies to current and historical events, technology landscapes and states of practice, market and company analysis, entity background, policy and legal-regulatory analysis, scientific synthesis, security incidents, comparative research, product-category landscapes, due diligence, and forecasts such as likely AI model release windows. Each mode has a reference file under `skills/deep-research/references/modes/` that fixes its evidence hierarchy, gates, and output shape. A report may explain what happened, compare alternatives, establish the current state of a field, or estimate what is likely next.

This is not a promise of objective omniscience. It is a repeatable method for being less wrong and easier to correct.

## 1. Frame the research question

Record:

- exact subject, decision, or forecast target;
- research mode and domain;
- decision questions;
- geographic and temporal scope;
- report cutoff in UTC;
- what would materially change the answer;
- exclusions.

A report answers what was reasonably knowable **at its cutoff**. Fast-moving claims decay; historical, technical, and scientific claims may remain stable longer. The report should identify which is which.

## 2. Decompose narratives into atomic claims

Do not research a slogan such as “the program was destroyed,” “Model X launches next month,” “Company Y is winning,” or “this is the best laptop under $2,000.” Split it:

- what observable state or specification is claimed;
- which capability, market, benchmark, customer, or decision criterion it concerns;
- which comparison class and time window apply;
- what evidence supports the stated timeline or advantage;
- what assumptions connect raw facts to the conclusion;
- who made each assertion;
- what remains unobserved.

Atomic claims make contradictions and partial truth visible.

## 3. Build a source map, not a link pile

Seek distinct evidence classes:

1. **Primary records:** official documents, technical documentation, code and release histories, filings, market data, benchmark artifacts, papers, patents, imagery, transcripts, datasets, court records, and direct observations.
2. **Independent reporting:** outlets that performed their own interviews, observation, document work, or analysis.
3. **Specialist analysis:** domain experts with disclosed methods and inspectable assumptions.
4. **Stakeholder statements:** companies, researchers, maintainers, regulators, investors, governments, advocacy groups, witnesses, customers, and other participants.
5. **Commentary and social media:** useful for hypotheses and leads, rarely sufficient alone.

Search deliberately for:

- evidence supporting the leading account;
- the strongest credible contradiction;
- primary material beneath secondary reporting;
- later corrections or updates;
- evidence that would make the preferred story fail.

## 4. Assess source and claim separately

The classic Admiralty insight is useful: **source reliability and information credibility are different axes**. This repository records both without reducing them to one magic number.

### Source-level dimensions

- **Access:** full text, partial text, or snippet only.
- **Source type:** primary record, technical documentation, code repository, benchmark, market data, regulatory filing, company communication, academic paper, patent, wire service, specialist, government, advocacy, analysis, social, or other.
- **Directness:** direct evidence, near-direct reporting, secondary reporting, or commentary.
- **Publisher history:** high, medium, low, or unknown, with a note explaining the basis.
- **Author expertise:** high, medium, low, or unknown, based on evidenced beat experience, relevant credentials, prior work, or demonstrated access.
- **Author track record:** high, medium, low, or unknown. Do not infer it from employer prestige or one article.
- **Transparency:** whether methods, documents, uncertainty, corrections, and sourcing are visible.
- **Incentives and conflicts:** political, financial, institutional, competitive, promotional, access, advocacy, wartime, publication, or personal pressures.
- **Limitations:** anonymous sourcing, no access, translation, stale publication, unverified imagery, model assumptions, and similar constraints.

### Claim-level dimensions

- **Kind:** observed fact, attributed statement, inference, forecast, or unknown.
- **Status:** confirmed, probable, contested, unsupported, or unknown.
- **Confidence range:** bounded probability, not a cosmetic adjective.
- **Supporting and contradicting sources.**
- **Evidence excerpts:** short verbatim text or public artifact coordinates.
- **Independence:** whether supporting sources originate from genuinely separate evidence paths.
- **Falsifiers:** evidence that would lower confidence.
- **Last checked:** staleness is part of truth assessment.

## 5. Do not double-count dependent reporting

Ten links can still be one source.

Assign an `independence_group` when reports depend on the same:

- wire story;
- press release;
- company roadmap, launch briefing, or embargoed demo;
- anonymous official or briefing;
- dataset;
- benchmark harness, market-data feed, analyst note, or supply-chain source;
- satellite image provider;
- leaked document;
- local stringer;
- social-media post.

Corroboration requires a distinct path to the underlying fact, not merely a distinct domain name.
Record an `independence_rationale` explaining the grouping decision. A group
label without its basis is taxonomy, not an audit trail.

## 6. Handle authors honestly

A byline matters when the author’s beat, access, method, or record is relevant. It is not a celebrity score.

Record:

- visible byline names;
- role or beat when stated by the publisher;
- specific expertise evidence and URL when retrieved;
- corrections or notable prior accuracy failures when directly documented;
- conflicts or access dependencies.

If this research was not performed, use `unknown`. Never manufacture a writer profile from tone, employer, nationality, or perceived politics.

## 7. Form competing hypotheses when the question earns them

For causal, intentional, strategic, or forecast questions, create at least:

- the leading explanation;
- the strongest credible alternative;
- a mixed or multi-causal explanation where appropriate;
- the “insufficient evidence” possibility.

Assign a low/central/high probability range only after the claim ledger exists. The range should widen when evidence is indirect, sources are dependent, private intent is central, or important observations are missing.

Probability is a statement about the analyst’s evidence state—not a frequency measured by the universe.

Do not manufacture hypotheses for a straightforward technical landscape or descriptive comparison. In those modes, a claim matrix, alternatives table, or decision criteria can carry the analysis and `hypotheses` may be empty. Event assessment, security incidents, and release forecasts are inherently causal or forecast-shaped and require at least one hypothesis with a named alternative.

### Forecast-specific discipline

For release timelines, market moves, or product roadmaps:

- distinguish announced dates from leaks, analyst estimates, inference, and wishful repetition;
- trace every rumor back to its earliest visible evidence path;
- separate model existence, internal testing, API availability, preview, general availability, and regional rollout;
- use release windows rather than a single day unless the date is formally committed;
- record base rates, dependencies, blockers, and explicit update triggers;
- preserve resolved misses and score them later instead of editing the old forecast.

### Product-category boundary

Deep research may map a product category, technology trajectory, durability evidence, price/performance frontier, and premium alternatives. A live “what should I buy?” decision should hand off to the dedicated product-buying workflow for current price, exact SKU, seller, delivered cost, warranty, return friction, and availability. Category understanding compounds; a checkout recommendation expires quickly.

## 8. Distinguish evidence from judgment

Use these labels in prose and structured data:

- **Observed:** directly supported by inspectable evidence.
- **Reported:** attributed to a named publication or person.
- **Assessed:** synthesis or inference from multiple claims.
- **Forecast:** expectation about future events.
- **Unknown:** evidence is absent, inaccessible, or contradictory.

A confident sentence must not quietly change category halfway through.

## 9. Citation discipline

Use a report-local `sources-ledger.json` with stable numeric IDs.

- Register sources at retrieval time.
- When an entire paragraph derives from the same source set, place that citation group once at the paragraph end.
- When a paragraph mixes evidence paths, put citations directly after the sentence or clause each source supports; split the paragraph when that is clearer.
- Use no more than three citations per sentence.
- Cite the primary record for what it says and independent reporting for interpretation or context.
- A citation to a source repeating another source is not independent corroboration.
- Never cite a search snippet as though the full page was read; mark access as `snippet`.
- Attach short verbatim evidence excerpts for load-bearing claims, recorded through `add-evidence` (or `add-quote` plus a matching evidence entry) so the excerpt is provably checked against fetched text. Use `kind: artifact` for figures, table cells, and other non-text coordinates.
- Cite data-bearing table rows; tables are not exempt from coverage. Header rows are labels, not evidence, and are not counted.
- `[unverified]` is an uncertainty marker, not a citation and not coverage credit.

## 10. Coverage and stopping rules

Continue retrieval until:

- every load-bearing claim has direct evidence or is labeled inference/unknown;
- the strongest credible counter-account was sought;
- source dependence is mapped;
- important numbers have scope and date;
- author/source gaps are visible;
- further sources are mostly repeating known evidence.

Stop and state degraded coverage when access barriers, language, censorship, safety, or time prevent that standard.

## 11. Update policy

An update must identify:

- previous report and cutoff;
- new evidence;
- claims whose status or confidence changed;
- hypotheses whose ranges moved;
- prior statements now corrected;
- unchanged high-value unknowns.

Record `lineage.supersedes` in the new report. If an older report is explicitly
retired, set its status to `superseded` and point `lineage.superseded_by` at the
new report. The validator checks existence and chronological cutoff order.

Never edit an old forecast until it looks prescient. Preserve the miss; that is how calibration improves.

## 12. Independent review

Use an independent reviewer for high-stakes or architecture-shaping reports. Ask it to challenge:

- missing alternatives;
- double-counted sources;
- author or publisher assumptions;
- unsupported causal language;
- probability ranges that are too narrow;
- absent falsifiers;
- conflation of outputs with outcomes, specifications with useful performance, announcements with availability, or tactical results with strategic goals;
- contradictions hidden by prose.

The reviewer’s verdict is evidence, not authority. Verify every proposed correction against the report artifacts.
