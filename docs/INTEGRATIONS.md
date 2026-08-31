# Agent integrations

`deep-research` is an [Agent Skills](https://agentskills.io/) skill, not a product-specific plugin. The same canonical directory works in Hermes, Claude Code, Codex, and OpenCode.

## Why a skill rather than a plugin

Use a skill for a focused procedural capability made of instructions, references, and deterministic local scripts. Use a plugin when distribution also needs connectors, MCP servers, UI assets, hooks, or a bundle of several skills.

This project currently needs the first thing. Adding four plugin wrappers would create four release surfaces without adding research capability.

## User-wide installation

From a stable clone of this repository:

```bash
python3 tools/install-skill.py install --consumer claude
python3 tools/install-skill.py install --consumer codex
python3 tools/install-skill.py install --consumer opencode
python3 tools/install-skill.py install --consumer hermes
```

Or install all four:

```bash
python3 tools/install-skill.py install --consumer all
```

OpenCode also scans Claude and Codex skill roots. When all adapters are installed it may discover the same skill through multiple roots; every entry resolves to identical canonical files, and the native OpenCode adapter provides the explicit OpenCode location. This avoids divergent copies even on OpenCode versions whose duplicate-source precedence has changed.

The installer creates regular consumer directories containing leaf symlinks to this checkout. Keep the checkout in a stable location. It refuses to replace unmanaged or drifted content.

Verify without mutation:

```bash
python3 tools/install-skill.py check --consumer all
```

Remove only managed installations:

```bash
python3 tools/install-skill.py uninstall --consumer claude,codex,opencode
```

## Project-scoped installation

To expose the skill only inside one repository:

```bash
python3 tools/install-skill.py install \
  --scope project \
  --project /path/to/project \
  --consumer claude,codex,opencode
```

This creates:

- `.claude/skills/deep-research/`
- `.agents/skills/deep-research/`
- `.opencode/skills/deep-research/`

Project links point back to this framework checkout, so they are suited to a stable local setup. For a team repository, pin `deep-research` as a submodule and run the installer from that pinned checkout.

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
