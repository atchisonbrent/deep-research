# Deep Research Modes

Choose one primary mode before retrieval. Modes change the evidence hierarchy and output shape; they do not change citation or independence requirements.

## General

Use when no narrower mode fits. Define the intended decision explicitly, then borrow the evidence strategy of the closest mode.

## Event assessment

Prioritize primary records, direct observation, independent field or investigative reporting, timelines, stakeholder statements kept in attribution, casualty or impact scope, competing causal accounts, and what remains unobserved.

Output: current state, timeline, actor goals and outcomes where relevant, disputed claims, consequences, forecast, update triggers.

## Technology landscape

Prioritize official technical documentation, code and release history, architecture papers, reproducible benchmarks, issue trackers, operator reports, adoption evidence, and independent experts with demonstrated domain experience.

Output: state of the technology, capability boundaries, maturity, deployment reality, alternatives, tradeoffs, unresolved bottlenecks, likely trajectory.

Do not equate a demo with a product, a benchmark with general performance, a repository star count with adoption, or a specification with operational reliability. Record benchmark harness, version, hardware, prompts, scoring, and comparison conditions before treating results as comparable.

## Market analysis

Prioritize first-party market data, regulatory filings, audited financials, transaction or pricing data, methodology-visible industry datasets, supply/demand indicators, and analysts whose assumptions can be inspected.

Output: market definition, size range rather than one magical TAM, segments, growth drivers, economics, competitive structure, scenarios, sensitivities, and forecast triggers.

Never combine figures with different geographies, category definitions, currencies, or periods without reconciliation.

## Company research

Prioritize regulatory filings, audited results, product and pricing pages, technical documentation, customer evidence, hiring and organizational signals, litigation/regulatory records, and independent reporting.

Output: products, business model, execution record, financial/operational position, competitive advantage claims, dependencies, risks, and open questions.

Company communications are primary evidence of what management says and sometimes of disclosed metrics—not neutral proof of product quality or strategy success.

## Release forecast

Prioritize formal announcements, release histories and cadence, code/config/catalog changes, developer documentation, credible supply-chain or partner evidence, named reporting, and carefully clustered leaks or anonymous reports.

Distinguish:

1. research or model existence;
2. internal testing;
3. external alpha or partner access;
4. public preview;
5. API or product availability;
6. general availability;
7. regional or tier-complete rollout.

Output probability-bearing **windows**, not a theatrical single date, unless formally committed. Include base rate, dependencies, blockers, earliest plausible window, central window, late case, and observable update triggers. Resolve the forecast later; do not edit the miss away.

## Policy analysis

Prioritize enacted text, proposed text, regulations, court decisions, official guidance, implementation data, budget and enforcement capacity, affected-party evidence, and domain legal/economic analysis.

Output: actual rule, implementation state, authority, affected groups, incentives, likely effects, legal/operational uncertainty, scenarios.

Separate proposal, enactment, effective date, enforcement, and observed effect.

## Scientific synthesis

Load `arxiv` where relevant. Prioritize peer-reviewed papers, preprints labeled as such, datasets, protocols, systematic reviews, replications, retractions/corrections, and domain consensus statements.

Output: research question, evidence body, methods and populations, effect sizes and uncertainty, replication state, limitations, consensus and live disputes.

Do not count papers as independent when they reuse the same dataset, cohort, lab, benchmark, or meta-analysis inputs.

## Comparative analysis

Freeze the comparison class and criteria before retrieval. Separate hard eligibility gates from weighted preferences and define the minimum acceptable outcome for each hard constraint. Prefer common-condition evidence; normalize units, versions, dates, workloads, transaction stage, price basis, and exclusions.

Write the eligibility gate, criteria matrix, and normalized cost table in `report.md`. Map their factual premises and conclusions into schema-defined claims, evidence, and coverage gaps; do not invent assessment fields. If no option passes every hard gate, output **no viable candidate within the comparison class**.

For live or transactional options:

1. Load `product-buying-research` when available; it owns exact-option, seller/provider, availability, checkout, and delivered-cost collection. Deep research imports that evidence and owns durable gating and synthesis.
2. Verify exact identity when it affects eligibility or value. Exclude unresolved identity that could fail a hard gate; otherwise rank only the lowest verified capability and preserve the contradiction.
3. Test simultaneous fit. Capacity, compatibility, required quality, operating limits, and logistics must hold for the complete workload at the same time.
4. Normalize decision-grade cost: required protection or service tier, taxes, fees, delivery or pickup, essential extras, refundability, included usage, and foreseeable operating cost. Headline prices at different transaction stages are not comparable.
5. Record observation time in the applicable source retrieval and `evidence.captured_at` records. Write the refresh trigger on the refresh-at-decision checklist in `report.md`; do not invent an assessment field. Stop before personal data, payment, terms acceptance, or transaction commit.
6. When a hard requirement changes, rerun the eligibility gate, workload fit, normalized totals, and ranking. If fresh post-cutoff evidence is required, create a dated successor and connect `lineage.supersedes` and `lineage.superseded_by` rather than revising the old cutoff.

Output: eligibility gate, criteria matrix, normalized cost table, evidence per criterion, tradeoffs, who should choose each option, sensitivity to changed priorities, unresolved identity or fit gaps, and a refresh-at-decision checklist.

A winner without a declared user, workload, budget, or objective is usually marketing wearing a table.

## Product landscape

Use for durable category understanding: technologies, major options, price/performance frontier, reliability and owner experience, repairability, ecosystem lock-in, premium alternatives, and category direction.

Output: category map, meaningful segments, decision criteria, option families, tradeoffs, value frontier, premium cases, and purchase-time facts that must be refreshed.

For an actual purchase recommendation, also load `product-buying-research`. It owns current exact SKU, seller, delivered price, availability, warranty, returns, and buying links. Deep research may supply the durable category report; product buying supplies the expiring transaction decision.

## Due diligence

Define the decision, materiality threshold, and red flags first. Prioritize primary legal/financial/technical records, ownership and dependency evidence, security and operational history, customer or counterparty concentration, and credible contradiction.

Output: thesis, verified facts, unresolved representations, red flags, dependency map, downside cases, evidence requests, and go/no-go conditions.

Do not turn absence of public evidence into proof that a risk is absent.
