#!/usr/bin/env python3
"""Install the canonical deep-research skill for supported agents."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills" / "deep-research"
CONSUMERS = {
    "claude": (".claude", "skills"),
    "codex": (".agents", "skills"),
    "opencode": (".config", "opencode", "skills"),
    "hermes": (".hermes", "skills", "research"),
}


class InstallError(RuntimeError):
    pass


def target_for(consumer: str, *, scope: str, home: Path, project: Path | None) -> Path:
    if scope == "project":
        if consumer == "hermes":
            raise InstallError("Hermes supports only user-scope installation")
        if project is None:
            raise InstallError("project scope requires --project")
        prefix = {
            "claude": (".claude", "skills"),
            "codex": (".agents", "skills"),
            "opencode": (".opencode", "skills"),
        }[consumer]
        return project.joinpath(*prefix, "deep-research")
    return home.joinpath(*CONSUMERS[consumer], "deep-research")


def source_files() -> list[Path]:
    files = sorted(path for path in SOURCE.rglob("*") if path.is_file())
    if not files or SOURCE / "SKILL.md" not in files:
        raise InstallError(f"canonical skill is incomplete: {SOURCE}")
    if any(path.is_symlink() for path in files):
        raise InstallError("canonical skill must contain regular files, not symlinks")
    return files


def expected_links(target: Path) -> dict[Path, Path]:
    return {
        target / path.relative_to(SOURCE): path.resolve()
        for path in source_files()
    }


def check_target(target: Path) -> list[str]:
    expected = expected_links(target)
    errors: list[str] = []
    if not target.is_dir() or target.is_symlink():
        return [f"missing managed skill directory: {target}"]
    actual_files = {path for path in target.rglob("*") if path.is_file() or path.is_symlink()}
    for path, source in expected.items():
        if not path.is_symlink():
            errors.append(f"missing managed link: {path}")
            continue
        try:
            resolved = path.resolve(strict=True)
        except FileNotFoundError:
            errors.append(f"broken managed link: {path}")
            continue
        if resolved != source:
            errors.append(f"misdirected managed link: {path} -> {resolved}")
    for path in sorted(actual_files - set(expected)):
        errors.append(f"unexpected file in managed skill: {path}")
    return errors


def refuse_unmanaged(target: Path) -> None:
    if not target.exists() and not target.is_symlink():
        return
    if not target.is_dir() or target.is_symlink():
        raise InstallError(f"refusing to replace unmanaged path: {target}")
    errors = check_target(target)
    if errors:
        raise InstallError(f"refusing to replace unmanaged or drifted skill: {target}")


def install_target(target: Path) -> None:
    refuse_unmanaged(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".deep-research-", dir=target.parent))
    try:
        for destination, source in expected_links(staging).items():
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.symlink_to(source)
        backup = target.with_name(target.name + ".old")
        if backup.exists() or backup.is_symlink():
            raise InstallError(f"stale installer backup requires review: {backup}")
        moved_old = False
        if target.exists():
            target.rename(backup)
            moved_old = True
        try:
            staging.rename(target)
        except Exception:
            if moved_old and backup.exists() and not target.exists():
                backup.rename(target)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def uninstall_target(target: Path) -> None:
    if not target.exists() and not target.is_symlink():
        return
    errors = check_target(target)
    if errors:
        raise InstallError(f"refusing to remove unmanaged or drifted skill: {target}")
    shutil.rmtree(target)


def parse_consumers(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        for item in value.split(","):
            item = item.strip().lower()
            if item == "all":
                item_values = list(CONSUMERS)
            elif item in CONSUMERS:
                item_values = [item]
            else:
                raise InstallError(f"unknown consumer: {item}")
            for consumer in item_values:
                if consumer not in result:
                    result.append(consumer)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "check", "uninstall"))
    parser.add_argument("--consumer", action="append", required=True, help="claude, codex, opencode, hermes, or all; repeatable/comma-separated")
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--home", type=Path, default=Path.home(), help="override user home for testing/bootstrap")
    parser.add_argument("--project", type=Path, help="project root for project scope")
    args = parser.parse_args(argv)

    consumers = parse_consumers(args.consumer)
    home = args.home.expanduser().resolve()
    project = args.project.expanduser().resolve() if args.project else None
    failures: list[str] = []
    for consumer in consumers:
        target = target_for(consumer, scope=args.scope, home=home, project=project)
        if args.action == "install":
            install_target(target)
            print(f"installed {consumer}: {target}")
        elif args.action == "uninstall":
            uninstall_target(target)
            print(f"uninstalled {consumer}: {target}")
        else:
            errors = check_target(target)
            if errors:
                failures.extend(f"{consumer}: {error}" for error in errors)
            else:
                print(f"clean {consumer}: {target}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except InstallError as exc:
        print(f"install error: {exc}", file=sys.stderr)
        raise SystemExit(2)
