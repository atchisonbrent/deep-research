# Agent integrations

`deep-research` is an [Agent Skills](https://agentskills.io/) skill, not a product-specific plugin. The same canonical directory works in Hermes, Claude Code, Codex, and OpenCode.

## Why a skill rather than a plugin

Use a skill for a focused procedural capability made of instructions, references, and deterministic local scripts. Use a plugin when distribution also needs connectors, MCP servers, UI assets, hooks, or a bundle of several skills.

This project currently needs the first thing. Adding four plugin wrappers would create four release surfaces without adding research capability.

## User-wide installation from the latest release

From any clone of this repository, install all consumers from the latest **published GitHub Release**:

```bash
python3 tools/install-latest.py
```

Or select consumers:

```bash
python3 tools/install-latest.py --consumer claude
python3 tools/install-latest.py --consumer codex --consumer opencode
```

The bootstrapper resolves GitHub's latest published release, verifies the tag against the remote commit, clones that exact tag into a versioned stable directory under `~/.local/share/deep-research/releases/<tag>/`, and invokes the release's own installer. Updating repeats the command: a new release gets a new checkout, consumer links move atomically, and the previous release remains available.

Roll back explicitly to any still-published release:

```bash
python3 tools/install-latest.py --tag v0.1.2 --consumer all
```

Cached checkouts are rechecked for a clean working tree, exact tag, expected origin, and agreement with the remote tag's commit before reuse. `check` and `uninstall` instead resolve the release that owns the installed links and work offline; they do not silently switch to whatever release became latest afterward.

Install and rollback require network access even when a same-named checkout is cached, because the bootstrapper re-verifies the tag against the remote commit. Override the versioned checkout root with `--install-root /path` when the XDG/default location is unsuitable.

`tools/install-skill.py` is the lower-level installer for an already selected Git checkout. It refuses to install from an untagged development revision by default. Maintainers testing unpublished changes must opt in explicitly with `--allow-unreleased`. GitHub-generated source archives do not contain `.git` metadata, so use `install-latest.py` or a tagged Git checkout rather than a release tarball for managed link installation.

OpenCode also scans Claude and Codex skill roots. When all adapters are installed it may discover the same skill through multiple roots; every entry resolves to identical canonical files, and the native OpenCode adapter provides the explicit OpenCode location. This avoids divergent copies even on OpenCode versions whose duplicate-source precedence has changed.

The installer creates regular consumer directories containing leaf symlinks to the selected release checkout. It refuses to replace unmanaged or drifted content.

If consumers intentionally point at different versions, operate on them separately (`check --consumer claude`, then `check --consumer codex`, and likewise for uninstall) or run one explicit `install-latest.py --tag <tag> --consumer all` to reconcile them to a single release.

### Refusal recovery

Refusal is deliberate: the installer will not erase a modified release checkout, broken link, or unmanaged target. Inspect the reported path first. Preserve any local work outside the managed release cache. For a damaged cached checkout, remove or move only the named `~/.local/share/deep-research/releases/<tag>/` directory and rerun `install-latest.py`; for broken or unmanaged consumer links, move the reported `deep-research` consumer directory aside, verify its contents, then reinstall. Do not recursively delete an agent's entire `skills/` directory.

Verify without mutation:

```bash
python3 tools/install-latest.py check --consumer all
```

Remove only managed installations:

```bash
python3 tools/install-latest.py uninstall --consumer claude,codex,opencode
```

## Project-scoped installation

To expose the skill only inside one repository:

```bash
python3 tools/install-latest.py \
  --scope project \
  --project /path/to/project \
  --consumer claude,codex,opencode
```

This creates:

- `.claude/skills/deep-research/`
- `.agents/skills/deep-research/`
- `.opencode/skills/deep-research/`

Project links point back to the selected release checkout. For a team repository, pin `deep-research` as a submodule at an exact release tag and run that release's lower-level installer.

## Invocation

- **Claude Code:** `/deep-research <question>` or ask naturally.
- **Codex:** `$deep-research <question>` or ask naturally.
- **OpenCode:** ask naturally; the agent loads `deep-research` through its skill tool.
- **Hermes:** `/deep-research <question>` or ask naturally.

Codex-specific presentation metadata lives in `skills/deep-research/agents/openai.yaml`; it does not fork the research instructions.

## Runtime contract

The skill resolves a report vault in this order:

1. product-injected `deep_research.repository` configuration when available;
2. `DEEP_RESEARCH_REPOSITORY` environment variable;
3. the current repository when it contains `tools/reportctl.py`;
4. `~/workspace/research-reports`.

A separate vault may pin this repository under `framework/`. The skill detects both layouts.

Product tool names differ, but the contract does not:

- search the web for discovery;
- extract or fetch the actual page before treating it as evidence;
- use the shell for `reportctl.py`;
- write only inside the selected report vault;
- validate before publication;
- never copy credentials or full copyrighted source dumps into reports.

If an agent lacks web retrieval, it must stop with a coverage gap rather than fabricate evidence.
