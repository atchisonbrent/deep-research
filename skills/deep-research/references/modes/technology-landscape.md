# Technology landscape

## Choose this mode when

The question is what a technology is, how mature it is, what it can and cannot do today, what the alternatives are, and where it is heading. Use `state-of-practice` when the question is how practitioners actually deploy or operate it; use `comparative-analysis` when a specific choice between named options must be made.

## Evidence hierarchy

1. official technical documentation, specifications, and standards;
2. code, release history, issue trackers, and changelogs;
3. reproducible benchmarks with harness, version, hardware, and prompts or inputs disclosed;
4. architecture papers and technical reports;
5. operator and adopter reports with enough detail to inspect;
6. independent experts with demonstrated domain experience;
7. vendor marketing, analyst quadrants, and star counts, as claims only.

## Decomposition pattern

Split capability into: specified, demonstrated (demo or paper), shipped (generally available), and operated at scale by third parties. For each, note version and date. Separate the technology from its dominant vendor. List bottlenecks as claims with evidence rather than as narrative.

## Mode gates

- Every benchmark comparison records harness, version, hardware, inputs, scoring, and comparison conditions; incomparable results are not ranked.
- Demo, preview, and general availability are not conflated.
- Adoption evidence names who, at what scale, in production or trial.

## Output sections

- Verdict
- State of the technology
- Capability boundaries and maturity
- Deployment reality
- Alternatives and tradeoffs
- Unresolved bottlenecks
- Trajectory and update triggers
- Gaps

## Completion criteria

A reader can tell what is specified, demonstrated, shipped, and operated; each capability boundary cites inspectable evidence; trajectory statements are labeled forecast with triggers.

## Pitfalls

- Equating a demo with a product, a benchmark with general performance, a repository star count with adoption, or a specification with operational reliability.
- Letting the vendor define the category.
- Treating a roadmap as a delivery.
