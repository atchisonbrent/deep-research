# Deep Research Methodology

## Objective

Produce the best-supported decision-grade answer to a substantial research question while making the evidence chain, uncertainty, source dependence, analytical judgment, and likely failure modes visible.

The method applies to current and historical events, technology landscapes and states of practice, market and company analysis, entity background, policy and legal-regulatory analysis, scientific synthesis, security incidents, comparative research, product-category landscapes, due diligence, and forecasts such as likely AI model release windows. Each mode has a reference file under `skills/deep-research/references/modes/` that fixes its evidence hierarchy, gates, and output shape. A report may explain what happened, compare alternatives, establish the current state of a field, or estimate what is likely next.

This is not a promise of objective omniscience. It is a repeatable method for being less wrong and easier to correct.

Two failure modes dominate AI-assisted research, and the method is organized against them. The first is **shallow retrieval**: a report that is accurate about everything it read but did not read what a specialist would consider decisive, then labels the unanswered question "unknown." The second is **correspondence without support**: citations that resolve and quotations that match, attached to prose that says something the evidence does not. Sections 3, 5 and 10 address the first; sections 9 and 12 the second.

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

## 3. Map the evidence landscape, then build a source map

Before collecting support for any conclusion, list for each decision question what a specialist would expect a serious answer to engage: canonical studies and reviews, the most recent authoritative work, official data series, audits, filings, budgets and court records that measure the thing directly, and the best-informed advocates on each side. Search scholarly indexes for empirical questions, and follow citation trails backward from the strongest recent work and forward to work that cites it. Record these searches in the report's search log (`log-search --purpose map`).

The map is a checklist to close, not a bibliography to admire. Each item is eventually read, shown unavailable by logged searches, or dismissed with a reason. A summary—a literature review, a government explainer, a news account of a study—is a pointer to primary work; retrieve the primary work for load-bearing uses.

Prefer depth to breadth. A report with seven decision questions and eighty sources has roughly ten sources per question; one with two decisive questions and the same effort can actually settle them.

### Source classes

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
- **Confidence range:** bounded probability, not a cosmetic adjective. Non-forecast claims may instead use the explicit qualitative contract in `SCHEMA.md`, where `status` is an evidence-backed judgment rather than a concealed probability; evidence, independence and citation checks still apply. Forecasts and hypotheses stay numerical.
- **Attribution versus truth:** for attributed claims, `status` records whether the source said it and `underlying_status` whether what it said is established. An agency's own statistics can be confirmed as reported and still be unaudited.
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

A byline matters when the author’s beat, access, method, or record is relevant. It is not a celebrity score. Author audits are optional in the schema: do them when an author's expertise or record bears on a load-bearing claim, especially a single-source one, and skip them otherwise rather than filling fields with `unknown`.

When you do record an author, include:

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
- preserve resolved misses and score them later instead of editing the old forecast;
- give each open hypothesis a `resolve_by` date on which it can be scored, or an `unresolvable_reason`.

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

## 9. Provenance, anchors, and citation discipline

### Provenance

Capture the text of every source actually read with `reportctl.py fetch` (or `capture` for browser renders, PDF extractions and archive copies). The tool stores the extracted text under its SHA-256 and records retrieval metadata in the ledger. `add-evidence --snapshot` then verifies each quotation against that stored text and binds the quotation to the hash. Anyone holding the snapshot store can re-verify every quotation, and edited text no longer matches its hash. This is a much stronger claim than "the quotation appears in a file the analyst supplied," which is all `--from-file` can establish.

Snapshots are private by default and live outside Git. Commit them beside the report only when the text may be redistributed, such as US federal government works or openly licensed papers. Back up the private store with the vault.

### Anchors

Mark where the prose asserts each load-bearing claim by placing the claim ID after the citation: `…fell 24%.[2]{C3}`. Anchors make the report's argument traceable to its ledger: the validator checks that an anchored passage cites only sources its claims list and that factual claims cite their own support, and a semantic reviewer can compare the passage with the claim it is supposed to express. Build presentation editions from `reportctl.py reader`, which removes anchors.

### Citation rules

Use a report-local `sources-ledger.json` with stable numeric IDs.

- Register sources at retrieval time.
- When an entire paragraph derives from the same source set, place that citation group once at the paragraph end.
- When a paragraph mixes evidence paths, put citations directly after the sentence or clause each source supports; split the paragraph when that is clearer.
- Use no more than three citations per sentence.
- Cite the primary record for what it says and independent reporting for interpretation or context.
- A citation to a source repeating another source is not independent corroboration.
- Never cite a search snippet as though the full page was read; mark access as `snippet`.
- Attach short verbatim evidence excerpts for load-bearing claims through `add-evidence --snapshot`, so each excerpt is checked against captured source text. Use `kind: artifact` for figures, table cells, and other non-text coordinates.
- Cite data-bearing table rows; tables are not exempt from coverage. Header rows are labels, not evidence, and are not counted.
- `[unverified]` is an uncertainty marker, not a citation and not coverage credit.

## 10. Coverage, disconfirmation, and stopping rules

Seek disconfirmation with the same intensity as support. For every load-bearing inference, forecast and hypothesis, run and log at least one search designed to prove it wrong, and record what it finds as contradicting sources even when that evidence is ultimately weighed less. Balance is symmetric search effort, not symmetric conclusions.

Continue retrieval until:

- every evidence-map item is read, shown unavailable by logged searches, or dismissed with a reason;
- every load-bearing claim has direct evidence or is labeled inference/unknown, and secondary-only support has been traced to primary work or recorded as a missing-primary gap;
- the strongest credible counter-account was sought and logged;
- every retrieved source is either cited or carries a disposition explaining why not—strong, recent, directly relevant evidence that was found and not used is a defect, not tidiness;
- every gap that says evidence is missing or inaccessible links the searches that tried;
- source dependence is mapped, and important numbers have scope and date;
- further searches on each decisive question mostly return evidence already held.

A decisive question may be reported as unresolved only after the evidence that could resolve it has been sought. Stop and state degraded coverage when access barriers, language, censorship, safety, or time prevent that standard; say which checklist items remain open.

## 11. Update policy

An update must identify:

- previous report and cutoff;
- new evidence;
- claims whose status or confidence changed;
- hypotheses whose ranges moved;
- prior statements now corrected;
- unchanged high-value unknowns.

Use `reportctl.py supersede` to create the successor: it records `lineage.supersedes` in the new report, sets the old report's status to `superseded`, and points `lineage.superseded_by` at the successor. The validator checks existence and chronological cutoff order.

Never edit an old forecast until it looks prescient. Preserve the miss; that is how calibration improves. `reportctl.py due` lists open hypotheses whose `resolve_by` date has arrived; run it on a schedule. Score them with `reportctl.py resolve`, and review the vault-wide record with `reportctl.py calibration`. A forecast that is never scored was a mood, not a forecast. Until dozens of outcomes are scored, the record is a ledger of hits and misses, not evidence of calibration.

## 12. Semantic audit and independent review

Deterministic checks establish correspondence: IDs resolve, quotations appear in captured text, anchored passages cite their claims' sources. They cannot establish that an excerpt entails a claim or that prose says what its claim says. Close that gap by sampling. `reportctl.py audit-sample` draws a reproducible sample of claim, excerpt-in-context, and anchored-prose triples; a judge other than the author records, for each, whether the excerpt supports the claim and whether the prose is faithful to it. Problem verdicts need recorded repairs. The sample's problem rate is an estimate of the report's error rate and belongs in the review record.

Independent review has two lenses, and they need different access:

1. **Correspondence review** works from the report, assessment, ledger, snapshots and prose-pass diff. It tests whether the evidence entails the prose.
2. **Coverage review** gets web access and one task: find decisive evidence the research missed. A reviewer confined to the supplied files cannot detect omissions, so without this lens depth is never reviewed at all.

For either lens, ask the reviewer to challenge:

- missing alternatives;
- double-counted sources;
- author or publisher assumptions;
- unsupported causal language;
- probability ranges that are too narrow;
- absent falsifiers;
- conflation of outputs with outcomes, specifications with useful performance, announcements with availability, or tactical results with strategic goals;
- contradictions hidden by prose.

The reviewer’s verdict is evidence, not authority. Verify every proposed correction against the report artifacts.
