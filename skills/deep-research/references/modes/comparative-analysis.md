# Comparative analysis

## Choose this mode when

A specific choice must be made among named options—vehicles, laptops, vendors, architectures, plans—against declared requirements. Use `product-landscape` for durable category understanding without a live choice; use `technology-landscape` when comparing technologies rather than selectable options. For live purchases, load `product-buying-research` when available: it owns exact option, seller or provider, availability, checkout, and delivered-cost collection, while this mode owns the eligibility gate and synthesis.

## Evidence hierarchy

1. authoritative specifications and primary identifiers (manufacturer specification tables, VIN or serial decoders, official configuration records);
2. common-condition measurements from an inspectable method;
3. first-party listings, catalogs, and quotes, for identity and price at a stated stage;
4. owner, operator, and reviewer reports with the workload stated;
5. platform categories, badges, titles, and seller assertions, as claims requiring verification.

## Decomposition pattern

Freeze the comparison contract before retrieval: **hard constraints**, **soft preferences**, **minimum acceptable outcomes**, the **complete simultaneous workload** (all people, cargo, compatibility, operating, and quality requirements that must hold at once), and the **common transaction basis**. Then build the criteria matrix. A criterion is load-bearing when a material change in it could change a gate outcome or the verdict; list those explicitly. Put the contract, matrix, and normalized cost table in `report.md`; represent their factual premises and conclusions with schema-defined claims, evidence, and coverage gaps in `assessment.json`. Do not invent assessment fields.

## Mode gates

**Eligibility gate.** Before ranking anything, remove candidates that fail a hard requirement. Evaluate the complete simultaneous workload, not isolated specifications: nominal capacity or a benchmark does not prove workload fit. If nothing passes, report **no viable candidate within the comparison class** instead of manufacturing a winner, and represent that as an inference over one evidenced gate-failure claim per candidate.

**Symmetric matrix.** For every retained candidate and load-bearing criterion, record exactly one of: (1) a value on the common unit, scope, and measurement basis; (2) a value normalized to that basis with the conversion or bounding rationale visible; (3) `N/A` with a reason the criterion does not apply; or (4) an unresolved gap. Never rank a measured value against silence. Record each unresolved cell in `assessment.json.coverage_gaps` as a structured gap, for example `{"kind": "matrix-cell", "candidate": "X", "criterion": "price basis", "description": "no delivered-cost data at cutoff"}`. If unresolved cells total more than half of the load-bearing criteria, report **insufficient evidence to rank** and list the retained candidates and the missing evidence.

**Proxies and bounds.** A proxy for the user's real concern may be displayed with its limitations named, but it carries ranking weight only when every retained candidate has a proxy on one shared, mutually comparable basis. A conservative lower bound carries weight only when its basis is condition-independent or demonstrably dominates the common condition. An `N/A` cell on a load-bearing criterion carries no weight; on a hard requirement it is a re-check signal, not a pass. Include deltas from a declared baseline when they make material differences legible.

**Identity.** Treat identity as load-bearing when exact model, trim, generation, configuration, seller, provider, or service tier affects eligibility or value. Compare the listing label with authoritative specifications and inspectable identifiers. A platform category, badge, or seller assertion is not authentication. Exclude an option when unresolved identity could make it fail a hard requirement; otherwise rank it only under the lowest verified capability and preserve the contradiction as a coverage gap.

**Cost basis.** Normalize dates or quantity, required protection or service tier, taxes, delivery or pickup, mandatory fees, essential extras, refundability, included usage, and foreseeable operating cost. A listed price may be registered with its scope, but it cannot support a load-bearing ranking until the common transaction basis is established. Never rank a pre-tax teaser against an all-in protected total. Stop before personal data, payment, terms acceptance, or any transaction commit.

**Requirement change.** If the user changes a hard requirement, intended use, workload, budget basis, or mandatory feature after synthesis, discard the stale verdict and rerun the eligibility gate, workload fit, normalized totals, and ranking. If no post-cutoff evidence is needed, update the draft without moving its cutoff. If it is needed, create a dated successor and connect `lineage.supersedes` and `lineage.superseded_by`.

## Output sections

- Verdict
- Comparison contract (hard constraints, soft preferences, workload, cost basis)
- Eligibility gate
- Criteria matrix
- Normalized cost table
- Identity and fit gaps
- Who should choose each option
- Sensitivity to changed priorities
- Refresh-at-decision checklist

## Completion criteria

Every retained candidate/load-bearing-criterion cell is a common-basis value, declared normalization, justified `N/A`, or named `coverage_gaps` entry; consequential identities are verified, conservatively bounded, or excluded; costs share one decision-grade basis; every data-bearing matrix and cost-table row is cited at the narrowest honest scope.

## Pitfalls

- **Advertised capacity is not workload fit.** Test all simultaneous constraints.
- **A shared table can still be asymmetric.** Proxy-only cells are not secretly evidence.
- **Headline prices are not comparable totals.**
- **Catalog identity can be wrong.** Verify consequential identities against primary identifiers.
- **A requirement change invalidates more than one sentence.** Re-gate, do not append a caveat.
- A winner without a declared user, workload, budget, or objective is usually marketing wearing a table.
