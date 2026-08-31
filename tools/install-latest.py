#!/usr/bin/env python3
"""Install agent adapters from a published deep-research release."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_REMOTE = "https://github.com/atchisonbrent/deep-research.git"
TAG_RE = re.compile(r"^v\d+\.\d+\.\d+$")
GITHUB_REMOTE_RE = re.compile(
    r"^(?:https://|ssh://git@|git@)(?P<host>github\.com)[/:](?P<repository>[^/\s]+/[^/\s]+?)(?:\.git)?$"
)
CONSUMER_PATHS = {
    "claude": (".claude", "skills", "deep-research"),
    "codex": (".agents", "skills", "deep-research"),
    "opencode": (".config", "opencode", "skills", "deep-research"),
    "hermes": (".hermes", "skills", "research", "deep-research"),
}


class BootstrapError(RuntimeError):
    pass


def run(*args: str, cwd: Path | None = None, timeout: int = 120) -> str:
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise BootstrapError(f"command timed out: {' '.join(args)}") from exc
    if result.returncode:
        raise BootstrapError(result.stderr.strip() or f"command failed: {' '.join(args)}")
    return result.stdout.strip()


def repository_from_remote(remote: str) -> str:
    match = GITHUB_REMOTE_RE.fullmatch(remote)
    if not match:
        raise BootstrapError(
            "remote must identify a github.com owner/repository; custom hosts require a reviewed bootstrap"
        )
    return match.group("repository").removesuffix(".git")


def latest_release_tag(repository: str, api_url: str = "https://api.github.com") -> str:
    request = urllib.request.Request(
        f"{api_url.rstrip('/')}/repos/{repository}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "deep-research-installer"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        raise BootstrapError(
            f"cannot resolve latest published release: GitHub returned HTTP {exc.code}"
        ) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise BootstrapError(f"cannot resolve latest published release: {exc}") from exc
    tag = payload.get("tag_name") if isinstance(payload, dict) else None
    if not isinstance(tag, str) or not TAG_RE.fullmatch(tag):
        raise BootstrapError(f"latest release returned an invalid tag: {tag!r}")
    return tag


def remote_tag_commit(remote: str, tag: str) -> str:
    output = run(
        "git",
        "ls-remote",
        "--tags",
        remote,
        f"refs/tags/{tag}",
        f"refs/tags/{tag}^{{}}",
    )
    refs: dict[str, str] = {}
    for line in output.splitlines():
        sha, ref = line.split("\t", 1)
        refs[ref] = sha
    commit = refs.get(f"refs/tags/{tag}^{{}}") or refs.get(f"refs/tags/{tag}")
    if not commit or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise BootstrapError(f"remote does not expose release tag {tag}")
    return commit


def verify_release_checkout(destination: Path, remote: str, tag: str, commit: str) -> None:
    if not (destination / ".git").is_dir():
        raise BootstrapError(f"release destination is not a Git checkout: {destination}")
    configured = run("git", "remote", "get-url", "origin", cwd=destination)
    if configured != remote:
        raise BootstrapError(f"release checkout has unexpected origin: {configured}")
    if run("git", "status", "--porcelain", cwd=destination):
        raise BootstrapError(f"release checkout is dirty: {destination}")
    if run("git", "describe", "--tags", "--exact-match", "HEAD", cwd=destination) != tag:
        raise BootstrapError(f"release checkout does not match {tag}: {destination}")
    if run("git", "rev-parse", "HEAD", cwd=destination) != commit:
        raise BootstrapError(f"cached {tag} does not match the remote release commit")


def ensure_release_checkout(remote: str, root: Path, tag: str) -> Path:
    commit = remote_tag_commit(remote, tag)
    releases = root / "releases"
    destination = releases / tag
    if destination.exists():
        verify_release_checkout(destination, remote, tag, commit)
        return destination

    releases.mkdir(parents=True, exist_ok=True)
    staging_root = Path(tempfile.mkdtemp(prefix=f".{tag}-", dir=releases))
    staging = staging_root / "checkout"
    try:
        run(
            "git",
            "clone",
            "--quiet",
            "--filter=blob:none",
            "--single-branch",
            "--branch",
            tag,
            remote,
            str(staging),
            timeout=300,
        )
        verify_release_checkout(staging, remote, tag, commit)
        try:
            staging.rename(destination)
        except OSError:
            if not destination.exists():
                raise
            verify_release_checkout(destination, remote, tag, commit)
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root)
    return destination


def parse_consumers(values: list[str] | None) -> list[str]:
    result: list[str] = []
    for value in values or ["all"]:
        for item in value.split(","):
            item = item.strip().lower()
            choices = list(CONSUMER_PATHS) if item == "all" else [item]
            for consumer in choices:
                if consumer not in CONSUMER_PATHS:
                    raise BootstrapError(f"unknown consumer: {consumer}")
                if consumer not in result:
                    result.append(consumer)
    return result


def consumer_target(
    consumer: str, *, scope: str, home: Path, project: Path | None
) -> Path:
    if scope == "user":
        return home.joinpath(*CONSUMER_PATHS[consumer])
    if project is None:
        raise BootstrapError("project scope requires --project")
    if consumer == "hermes":
        raise BootstrapError("Hermes supports only user-scope installation")
    prefix = {
        "claude": (".claude", "skills", "deep-research"),
        "codex": (".agents", "skills", "deep-research"),
        "opencode": (".opencode", "skills", "deep-research"),
    }[consumer]
    return project.joinpath(*prefix)


def owning_checkout(
    consumers: list[str], *, scope: str, home: Path, project: Path | None
) -> Path | None:
    checkouts: set[Path] = set()
    for consumer in consumers:
        target = consumer_target(consumer, scope=scope, home=home, project=project)
        skill = target / "SKILL.md"
        if not skill.exists() and not skill.is_symlink():
            continue
        if not skill.is_symlink():
            raise BootstrapError(f"installed skill is not managed: {skill}")
        try:
            resolved = skill.resolve(strict=True)
        except FileNotFoundError as exc:
            raise BootstrapError(f"installed skill link is broken: {skill}") from exc
        if resolved.parts[-3:] != ("skills", "deep-research", "SKILL.md"):
            raise BootstrapError(f"installed skill has unexpected provenance: {skill} -> {resolved}")
        checkout = resolved.parents[2]

        if run("git", "status", "--porcelain", cwd=checkout):
            raise BootstrapError(f"installed release checkout is dirty: {checkout}")
        tag = run("git", "describe", "--tags", "--exact-match", "HEAD", cwd=checkout)
        if not TAG_RE.fullmatch(tag):
            raise BootstrapError(f"installed checkout is not an exact release: {checkout}")
        checkouts.add(checkout)
    if len(checkouts) > 1:
        raise BootstrapError("selected consumers point to different releases; reconcile explicitly")
    return next(iter(checkouts)) if checkouts else None


def default_install_root(home: Path) -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg).expanduser() if xdg else home / ".local" / "share"
    return base / "deep-research"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=("install", "check", "uninstall"), default="install")
    parser.add_argument("--consumer", action="append", help="consumer(s); defaults to all")
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--project", type=Path)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--install-root", type=Path)
    parser.add_argument("--tag", help="install an exact published release instead of latest")
    parser.add_argument("--remote", default=DEFAULT_REMOTE)
    parser.add_argument("--api-url", default="https://api.github.com", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    consumers = parse_consumers(args.consumer)
    home = args.home.expanduser().resolve()
    project = args.project.expanduser().resolve() if args.project else None
    if project is not None and args.scope != "project":
        raise BootstrapError("--project requires --scope project")
    install_root = (
        args.install_root.expanduser().resolve()
        if args.install_root
        else default_install_root(home).resolve()
    )

    if args.action == "install":
        if args.tag and not TAG_RE.fullmatch(args.tag):
            raise BootstrapError(f"invalid release tag: {args.tag}")
        repository = repository_from_remote(args.remote)
        tag = args.tag or latest_release_tag(repository, args.api_url)
        checkout = ensure_release_checkout(args.remote, install_root, tag)
    else:
        if args.tag:
            raise BootstrapError("--tag is valid only with install")
        checkout = owning_checkout(
            consumers, scope=args.scope, home=home, project=project
        )
        if checkout is None:
            checkout = Path(__file__).resolve().parents[1]
            tag = "not-installed"
        else:
            tag = run("git", "describe", "--tags", "--exact-match", "HEAD", cwd=checkout)

    installer = Path(__file__).resolve().with_name("install-skill.py")
    command = [
        sys.executable,
        str(installer),
        args.action,
        "--source",
        str(checkout / "skills" / "deep-research"),
    ]
    for consumer in consumers:
        command.extend(["--consumer", consumer])
    command.extend(["--scope", args.scope, "--home", str(home)])
    if project:
        command.extend(["--project", str(project)])
    result = subprocess.run(command, check=False)
    verb = {"install": "installed", "check": "checked", "uninstall": "uninstalled"}[args.action]
    if result.returncode == 0 and tag == "not-installed":
        print("no managed deep-research installation found")
    elif result.returncode == 0:
        print(f"{verb} deep-research {tag} from {checkout}")
    return result.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BootstrapError as exc:
        print(f"bootstrap error: {exc}", file=sys.stderr)
        raise SystemExit(2)
