# Scientific synthesis

## Choose this mode when

The question is what the scientific evidence says about a phenomenon, intervention, or claim: the state of evidence, effect sizes, replication, and live disputes. Load `arxiv` where the agent exposes it.

## Evidence hierarchy

1. systematic reviews and meta-analyses with inspectable inclusion criteria and heterogeneity reporting;
2. pre-registered trials or studies with published protocols;
3. peer-reviewed primary studies, with population, method, and effect size recorded;
4. replications and failed replications;
5. preprints, labeled as such, with version;
6. consensus statements from bodies with visible process;
7. retractions, corrections, and expressions of concern (these outrank the papers they modify);
8. press releases and science journalism, as claims about the paper, not evidence.

## Decomposition pattern

State the research question in PICO-like form where applicable (population, intervention or exposure, comparator, outcome). For each study cluster record method, population, sample size, effect size with interval, and funding or conflicts. Map dependence: shared datasets, cohorts, labs, and meta-analysis inputs form one independence group.

## Mode gates

- Effect sizes carry intervals and the population they were measured in.
- Retraction and correction status is checked for every load-bearing paper.
- Studies reusing a dataset, cohort, or lab are not counted as independent.
- Preprints are labeled and not described as findings of the peer-reviewed literature.

## Output sections

- Verdict
- Research question
- Evidence body (by study cluster)
- Methods, populations, and effect sizes
- Replication and retraction state
- Consensus and live disputes
- Limitations and confounders
- Gaps

## Completion criteria

Each load-bearing finding cites the study and its effect size, population, and dependence group; retraction status is recorded; disputes are presented with the strongest position on each side.

## Pitfalls

- Counting papers instead of independent evidence paths.
- Reporting a press-release headline as the paper's finding.
- Ignoring a correction because the original was more quotable.
