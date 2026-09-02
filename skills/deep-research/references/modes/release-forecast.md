# Release forecast

## Choose this mode when

The question is when a product, model, feature, or regulation is likely to ship, and what evidence supports the window. Also use for other dated-milestone forecasts (launch, approval, rollout) where the release ladder below applies.

## Evidence hierarchy

1. formal announcements with dates and scope;
2. release history and cadence of the same producer;
3. code, configuration, catalog, documentation, or app-store changes that are inspectable;
4. regulatory or partner filings and disclosures;
5. credible supply-chain, partner, or developer evidence with a visible path;
6. named reporting with stated sourcing;
7. clustered leaks and anonymous reports, grouped by underlying source;
8. speculation and wishful repetition, as evidence of expectation only.

## Decomposition pattern

Place every signal on the release ladder: (1) existence; (2) internal testing; (3) external alpha or partner access; (4) public preview; (5) API or product availability; (6) general availability; (7) regional or tier-complete rollout. State which rung the forecast concerns. Trace each rumor to its earliest visible evidence path. Record base rates from the producer's history, dependencies, and blockers.

## Mode gates

- The forecast is a window with low/central/high and stated basis, not a single date, unless formally committed.
- Rungs are not conflated; "launched" names the rung.
- Leak clusters are one independence group unless a distinct path is shown.
- Each hypothesis has update triggers that are observable.

## Output sections

- Verdict (window and rung)
- Release ladder status
- Evidence path for each signal
- Base rates and dependencies
- Blockers
- Earliest, central, and late cases
- Update triggers
- Gaps

## Completion criteria

At least one hypothesis with a probability range and named alternatives exists; every signal names its rung and evidence path; the forecast will be scored later via `resolution`, not edited.

## Pitfalls

- Reporting a date because many outlets repeated one leak.
- Treating internal testing as imminent availability.
- Editing a missed forecast into prescience. Preserve the miss.
