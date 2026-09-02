# Mode reference files

One file per research mode. Every file uses the same skeleton so an agent can switch modes without relearning the layout:

1. **Choose this mode when** — the question shapes that belong here, and the nearest neighbours to consider instead.
2. **Evidence hierarchy** — what counts as primary in this mode, ordered from strongest to weakest.
3. **Decomposition pattern** — how to split the headline question into atomic claims for this mode.
4. **Mode gates** — checks that must pass before synthesis; failing a gate changes the verdict, not the wording.
5. **Output sections** — the `report.md` headings `reportctl.py init --mode` scaffolds; keep them unless a section is genuinely inapplicable, and say so if you drop one. A trailing parenthetical on a list entry (for example `Verdict (window and rung)`) is guidance about the section's content, not part of the heading; the framework test compares the heading text before the parenthetical.
6. **Completion criteria** — what must be true before the report leaves draft.
7. **Pitfalls** — the characteristic ways this mode goes wrong.

Modes change the evidence hierarchy and output shape. They never change citation, independence, cutoff, or validation requirements; those live in `METHODOLOGY.md`, `SCHEMA.md`, and the skill spine.

| Mode | File | Hypotheses expected |
|---|---|---|
| `general` | [general.md](general.md) | when the question is causal or forecast |
| `event-assessment` | [event-assessment.md](event-assessment.md) | yes |
| `historical-analysis` | [historical-analysis.md](historical-analysis.md) | yes, for causal questions |
| `technology-landscape` | [technology-landscape.md](technology-landscape.md) | rarely |
| `state-of-practice` | [state-of-practice.md](state-of-practice.md) | no |
| `market-analysis` | [market-analysis.md](market-analysis.md) | scenarios, not hypotheses |
| `company-research` | [company-research.md](company-research.md) | for strategy/motive questions |
| `entity-background` | [entity-background.md](entity-background.md) | no |
| `release-forecast` | [release-forecast.md](release-forecast.md) | required |
| `policy-analysis` | [policy-analysis.md](policy-analysis.md) | for effect forecasts |
| `legal-regulatory` | [legal-regulatory.md](legal-regulatory.md) | for outcome forecasts |
| `scientific-synthesis` | [scientific-synthesis.md](scientific-synthesis.md) | for live disputes |
| `security-incident` | [security-incident.md](security-incident.md) | yes, for attribution/cause |
| `comparative-analysis` | [comparative-analysis.md](comparative-analysis.md) | no; criteria matrix |
| `product-landscape` | [product-landscape.md](product-landscape.md) | no |
| `due-diligence` | [due-diligence.md](due-diligence.md) | downside scenarios |

If no mode fits, use `general` and borrow the nearest hierarchy explicitly in the report's contract section rather than inventing a hybrid silently.


The "Hypotheses expected" column describes the mode's usual shape. Independently of mode, any report containing a `forecast`-kind claim must carry at least one hypothesis with a probability range, because the validator scores forecasts through hypotheses; a scenario-style mode that ventures a forecast claim adds a hypothesis for it.
