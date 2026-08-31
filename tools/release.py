#!/usr/bin/env python3
"""Plan and apply eager SemVer releases from Conventional Commits."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "version.txt"
SKILL_FILE = ROOT / "skills" / "deep-research" / "SKILL.md"
CHANGELOG_FILE = ROOT / "CHANGELOG.md"
MANIFEST_FILE = ROOT / "release.json"
SEMVER_RE = re.compile(r"^(?:v)?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
HEADER_RE = re.compile(r"^(?P<type>[a-z][a-z0-9-]*)(?:\([^\n)]+\))?(?P<breaking>!)?: (?P<subject>.+)$")
RELEASE_TYPES = {"feat", "fix"}
SECTION_NAMES = {"feat": "Features", "fix": "Bug Fixes"}


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "Version":
        match = SEMVER_RE.fullmatch(value.strip())
        if not match:
            raise ValueError(f"invalid semantic version: {value!r}")
        return cls(*(int(part) for part in match.groups()))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def bump(self, level: str) -> "Version":
        if level == "major":
            return Version(self.major + 1, 0, 0)
        if level == "minor":
            return Version(self.major, self.minor + 1, 0)
        if level == "patch":
            return Version(self.major, self.minor, self.patch + 1)
        raise ValueError(f"unknown bump level: {level}")


@dataclass(frozen=True)
class Commit:
    sha: str
    message: str

    @property
    def header(self) -> str:
        return self.message.splitlines()[0].strip()

    @property
    def parsed(self) -> re.Match[str] | None:
        return HEADER_RE.match(self.header)

    @property
    def breaking(self) -> bool:
        match = self.parsed
        return bool(match and match.group("breaking")) or bool(
            re.search(r"(?m)^BREAKING[ -]CHANGE:\s+", self.message)
        )

    @property
    def kind(self) -> str | None:
        match = self.parsed
        return match.group("type") if match else None

    @property
    def subject(self) -> str:
        match = self.parsed
        return match.group("subject") if match else self.header


@dataclass(frozen=True)
class Plan:
    current: Version
    next_version: Version | None
    bump: str | None
    commits: tuple[Commit, ...]
    base_tag: str

    @property
    def release(self) -> bool:
        return self.next_version is not None


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def latest_release_tag() -> str:
    tags = []
    for raw in git("tag", "--merged", "HEAD", "--list", "v[0-9]*.[0-9]*.[0-9]*").splitlines():
        try:
            tags.append((Version.parse(raw), raw))
        except ValueError:
            continue
    if not tags:
        raise RuntimeError("no reachable vMAJOR.MINOR.PATCH release tag")
    return max(tags)[1]


def commits_since(tag: str) -> tuple[Commit, ...]:
    raw = subprocess.run(
        ["git", "log", "--reverse", "--format=%H%x00%B%x00%x1e", f"{tag}..HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    commits: list[Commit] = []
    for record in raw.split("\x1e"):
        record = record.strip("\n\x00 ")
        if not record:
            continue
        sha, message = record.split("\x00", 1)
        commits.append(Commit(sha=sha.strip(), message=message.strip()))
    return tuple(commits)


def bump_for(current: Version, commits: Iterable[Commit]) -> str | None:
    commits = tuple(commits)
    if any(commit.breaking for commit in commits):
        return "minor" if current.major == 0 else "major"
    kinds = {commit.kind for commit in commits}
    if current.major == 0:
        return "patch" if kinds & RELEASE_TYPES else None
    if "feat" in kinds:
        return "minor"
    if "fix" in kinds:
        return "patch"
    return None


def make_plan() -> Plan:
    current = Version.parse(VERSION_FILE.read_text(encoding="utf-8"))
    base_tag = latest_release_tag()
    tagged = Version.parse(base_tag)
    if current != tagged:
        raise RuntimeError(f"version.txt ({current}) does not match latest tag ({tagged})")
    commits = commits_since(base_tag)
    bump = bump_for(current, commits)
    return Plan(current, current.bump(bump) if bump else None, bump, commits, base_tag)


def release_commits(plan: Plan) -> tuple[Commit, ...]:
    return tuple(
        commit for commit in plan.commits if commit.breaking or commit.kind in RELEASE_TYPES
    )


def notes(plan: Plan) -> str:
    if not plan.release or plan.next_version is None:
        return ""
    grouped: dict[str, list[Commit]] = {"breaking": [], "feat": [], "fix": []}
    for commit in release_commits(plan):
        if commit.breaking:
            grouped["breaking"].append(commit)
        elif commit.kind in grouped:
            grouped[commit.kind].append(commit)
    lines = [f"## deep-research v{plan.next_version}", ""]
    for key, heading in (
        ("breaking", "Breaking Changes"),
        ("feat", "Features"),
        ("fix", "Bug Fixes"),
    ):
        if not grouped[key]:
            continue
        lines.extend([f"### {heading}", ""])
        for commit in grouped[key]:
            lines.append(f"- {commit.subject} (`{commit.sha[:7]}`)")
        lines.append("")
    lines.extend(
        [
            "### Compatibility",
            "",
            "Consumers should pin this tag or its exact commit and update through a separately validated consumer change.",
            "",
        ]
    )
    return "\n".join(lines)


def changelog_entry(plan: Plan) -> str:
    if not plan.release or plan.next_version is None:
        return ""
    grouped: dict[str, list[Commit]] = {"breaking": [], "feat": [], "fix": []}
    for commit in release_commits(plan):
        if commit.breaking:
            grouped["breaking"].append(commit)
        elif commit.kind in grouped:
            grouped[commit.kind].append(commit)
    lines = [f"## [{plan.next_version}] - {date.today().isoformat()}", ""]
    for key, heading in (
        ("breaking", "Breaking Changes"),
        ("feat", SECTION_NAMES["feat"]),
        ("fix", SECTION_NAMES["fix"]),
    ):
        if grouped[key]:
            lines.extend([f"### {heading}", ""])
            lines.extend(f"- {commit.subject}" for commit in grouped[key])
            lines.append("")
    return "\n".join(lines)


def repository_url() -> str:
    repository = os.environ.get("GITHUB_REPOSITORY")
    if repository:
        server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
        return f"{server}/{repository}"
    remote = git("remote", "get-url", "origin")
    match = re.search(r"github\.com[:/](?P<path>[^\s]+?)(?:\.git)?$", remote)
    if not match:
        raise RuntimeError("cannot derive GitHub repository URL from origin")
    return f"https://github.com/{match.group('path').removesuffix('.git')}"


def replace_once(path: Path, pattern: str, replacement: str) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"expected exactly one version marker in {path}")
    path.write_text(updated, encoding="utf-8")


def apply(plan: Plan, notes_path: Path | None = None) -> None:
    if not plan.release or plan.next_version is None:
        raise RuntimeError("plan contains no release")
    version = str(plan.next_version)
    VERSION_FILE.write_text(version + "\n", encoding="utf-8")
    replace_once(
        SKILL_FILE,
        r'^  version: "\d+\.\d+\.\d+" # x-release-version$',
        f'  version: "{version}" # x-release-version',
    )
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    manifest["version"] = version
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    changelog = CHANGELOG_FILE.read_text(encoding="utf-8")
    marker = "\n## ["
    index = changelog.find(marker)
    if index < 0:
        raise RuntimeError("CHANGELOG.md has no release insertion point")
    updated = changelog[: index + 1] + "\n" + changelog_entry(plan) + changelog[index + 1 :]
    updated = updated.rstrip() + (
        f"\n[{version}]: {repository_url()}/releases/tag/v{version}\n"
    )
    CHANGELOG_FILE.write_text(updated, encoding="utf-8")
    if notes_path:
        notes_path.write_text(notes(plan), encoding="utf-8")


def plan_dict(plan: Plan) -> dict[str, object]:
    return {
        "release": plan.release,
        "current": str(plan.current),
        "next": str(plan.next_version) if plan.next_version else None,
        "bump": plan.bump,
        "base_tag": plan.base_tag,
        "commits": [commit.sha for commit in release_commits(plan)],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan_parser = sub.add_parser("plan")
    plan_parser.add_argument("--github-output", type=Path)
    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument("--notes", type=Path)
    args = parser.parse_args(argv)

    plan = make_plan()
    if args.command == "plan":
        payload = plan_dict(plan)
        print(json.dumps(payload, sort_keys=True))
        if args.github_output:
            with args.github_output.open("a", encoding="utf-8") as handle:
                handle.write(f"release={'true' if plan.release else 'false'}\n")
                handle.write(f"version={payload['next'] or ''}\n")
                handle.write(f"base_tag={payload['base_tag']}\n")
        return 0
    apply(plan, args.notes)
    print(json.dumps(plan_dict(plan), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"release error: {exc}", file=sys.stderr)
        raise SystemExit(2)
