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

Freeze the comparison class and criteria before retrieval. Prefer common-condition evidence; normalize units, versions, dates, workloads, price basis, and exclusions.

Output: criteria matrix, evidence per criterion, tradeoffs, who should choose each option, sensitivity to changed priorities, unresolved gaps.

A winner without a declared user, workload, budget, or objective is usually marketing wearing a table.

## Product landscape

Use for durable category understanding: technologies, major options, price/performance frontier, reliability and owner experience, repairability, ecosystem lock-in, premium alternatives, and category direction.

Output: category map, meaningful segments, decision criteria, option families, tradeoffs, value frontier, premium cases, and purchase-time facts that must be refreshed.

For an actual purchase recommendation, also load `product-buying-research`. It owns current exact SKU, seller, delivered price, availability, warranty, returns, and buying links. Deep research may supply the durable category report; product buying supplies the expiring transaction decision.

## Due diligence

Define the decision, materiality threshold, and red flags first. Prioritize primary legal/financial/technical records, ownership and dependency evidence, security and operational history, customer or counterparty concentration, and credible contradiction.

Output: thesis, verified facts, unresolved representations, red flags, dependency map, downside cases, evidence requests, and go/no-go conditions.

Do not turn absence of public evidence into proof that a risk is absent.
