# Releasing

This repository uses [Release Please](https://github.com/googleapis/release-please) and Semantic Versioning.

## Version meaning

The repository is released as one compatibility unit: methodology, schema, validator, CLI, and Hermes skill.

- **Before 1.0:** `fix:` and `feat:` bump the patch version; `!` or a `BREAKING CHANGE:` footer bumps the minor version.
- **At and after 1.0:** `fix:` bumps patch, `feat:` bumps minor, and a breaking change bumps major.
- `docs:`, `test:`, `ci:`, `chore:`, and `refactor:` do not independently create a release unless marked breaking.

## Workflow

1. Merge Conventional Commits into `main`.
2. Release Please maintains a release PR containing the proposed version, `CHANGELOG.md`, `version.txt`, and synchronized skill frontmatter.
3. Review the release PR like any other compatibility change.
4. Merge it when ready.
5. The same workflow validates the merged revision, then creates an immutable `vMAJOR.MINOR.PATCH` tag and GitHub Release.

Merging ordinary changes does **not** immediately publish a tag. The release PR is the human gate.

## Consumer policy

Consumers should pin an exact tag or commit. Do not make private report vaults or Hermes deployments float on `main`. Updating a consumer is a separate reviewed change with its own tests and readback.

## Security

The release workflow uses the repository-scoped `GITHUB_TOKEN` with job-level least privilege. The third-party Release Please action is pinned to a full commit SHA. No package-registry credential or personal access token is required.

GitHub suppresses follow-on workflow events created with `GITHUB_TOKEN`. This repository therefore runs validation **before** the Release Please job can create a tag. Release PRs contain only generated version and changelog changes and remain subject to human review.

## Bootstrap

`v0.1.0` was bootstrapped manually after the complete framework, public skill, real example, and release configuration passed validation. The project will move to `v1.0.0` deliberately when the schema, CLI, and skill behavior are ready for a stable compatibility promise. Later releases are produced by Release Please.
