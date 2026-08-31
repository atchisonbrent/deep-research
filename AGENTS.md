# Research Reports Repository

## Purpose

This public repository owns the reusable deep-research methodology, schema, standard-library tooling, tests, and CI. Actual report archives may be public or private consumer repositories pinned to an exact framework revision.

## Hard boundaries

- Never convert outlet reputation into a universal truth score.
- Assess source reliability separately from the credibility of a particular claim.
- Treat syndicated reports, shared anonymous officials, copied wire stories, and common upstream documents as one independence cluster unless evidence shows otherwise.
- Record authors only when the byline is visible. Record expertise or track record only with retrievable evidence; `unknown` is preferable to invented biography.
- Separate observed facts, attributed claims, inference, forecast, and unknowns.
- Use probability **ranges**, not faux-precise point estimates, for contested hypotheses.
- Preserve the report cutoff. Later knowledge belongs in a dated update, not a silent rewrite.
- Never commit credentials, private personal data, classified/leaked secret material, or full copyrighted article dumps.

## Report contract

Every published report directory contains:

- `report.md`
- `assessment.json`
- `sources-ledger.json`

Run before commit:

```bash
python3 tools/reportctl.py validate <report-directory>
python3 tools/reportctl.py validate examples/iran-war-six-month-assessment
python3 tools/install-skill.py check --consumer all --home <test-home>
python3 -m unittest discover -s tests -v
git diff --check
```

A report is not complete merely because Markdown renders. The structured claim and evidence ledger must validate, citations must resolve, and any forecast or causal probability ranges must identify their basis and update triggers.
