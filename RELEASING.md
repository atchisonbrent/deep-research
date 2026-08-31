# Releasing

This repository uses an eager, self-contained Semantic Versioning workflow implemented by `tools/release.py`.

## Version meaning

The repository is released as one compatibility unit: methodology, schema, validator, CLI, and Hermes skill.

- **Before 1.0:** `fix:` and `feat:` bump the patch version; `!` or a `BREAKING CHANGE:` footer bumps the minor version.
- **At and after 1.0:** `fix:` bumps patch, `feat:` bumps minor, and a breaking change bumps major.
- `docs:`, `test:`, `ci:`, `chore:`, and `refactor:` do not independently create a release unless marked breaking.

## Workflow

1. A Conventional Commit lands on `main`.
2. The public test suite, fixture validation, real-example validation, and sensitive-content scan pass.
3. The release job checks that it still owns the current `main` revision; a superseded workflow exits without publishing.
4. `tools/release.py` examines releasable commits since the latest reachable `vMAJOR.MINOR.PATCH` tag.
5. If no `feat`, `fix`, or breaking change exists, the job exits without a tag.
6. Otherwise it updates `CHANGELOG.md`, `release.json`, `version.txt`, and the Hermes skill frontmatter.
7. The workflow reruns tests and validators against the generated release mutation.
8. It creates a release commit, annotated tag, and GitHub Release atomically.

There is no release PR and no routine human gate. Validation is the gate.

## Consumer policy

Consumers should pin an exact tag or commit. Do not make private report vaults or Hermes deployments float on `main`. Updating a consumer is a separate validated change with its own tests and readback.

## Security and race handling

The release job uses the repository-scoped `GITHUB_TOKEN` with only `contents: write`. It has no package-registry credential or personal access token and invokes no third-party release action.

GitHub suppresses follow-on workflow events created with `GITHUB_TOKEN`; the current job therefore validates the generated release mutation before committing it. The release commit includes `[skip ci]` as an additional recursion guard.

Release jobs serialize through a dedicated concurrency group. Before planning, each job fetches `origin/main` and declines to release if its triggering revision has already been superseded. The final commit and tag push is atomic; a concurrent remote update fails closed rather than producing a tag for the wrong tree.

The GitHub Release API call necessarily follows the atomic Git push. If that final API call fails after the tag exists, manually dispatch the `validate` workflow on `main`. Every current release run reconciles the latest reachable version tag with its GitHub Release before planning anything newer. It creates only a missing GitHub Release; it never moves or recreates a tag.

The canonical publish job is explicitly gated to `atchisonbrent/deep-research`. Forks retain validation but do not unexpectedly publish releases unless their owners deliberately replace that gate. Under closely spaced pushes, stale workflows exit and a later current workflow may aggregate several releasable commits into one version; no commit is tagged against the wrong tree.

## Local inspection

```bash
python3 tools/release.py plan
```

`plan` is read-only. `apply` mutates release files and is reserved for the validated CI release job or an explicitly controlled recovery.

## Bootstrap

`v0.1.0` was bootstrapped manually after the complete framework, public skill, real example, and release configuration passed validation. The project will move to `v1.0.0` deliberately when the schema, CLI, and skill behavior are ready for a stable compatibility promise. Later releasable changes publish eagerly after validation.
