"""Check whether the private repo and public copy are safe to publish.

This script looks for files that should not be committed or exported, like real
resume text, generated results, cache files, tracker history, virtualenvs, and
Git metadata in the sanitized public copy.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PUBLIC_COPY = ROOT.parent / "job_tool_public"

BLOCKED_TRACKED_PATTERNS = (
    "jobs_cache.json",
    "resume_cyber.txt",
    "resume_it_support.txt",
    "results/current/",
    "results/diagnostics/",
    "results/archive/",
    "results/tracker/application_tracker.csv",
    "results/tracker/application_tracker.md",
    "results/tracker/application_tracker.txt",
    ".venv/",
    "venv/",
    "__pycache__/",
)

BLOCKED_PUBLIC_PATH_PARTS = (
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "current",
    "diagnostics",
    "archive",
)

BLOCKED_PUBLIC_FILE_NAMES = {
    "jobs_cache.json",
    "resume_cyber.txt",
    "resume_it_support.txt",
    "application_tracker.csv",
    "application_tracker.md",
    "application_tracker.txt",
}


def run_git_ls_files() -> list[str]:
    """Return tracked files, or an empty list if Git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return []

    if result.returncode != 0:
        return []

    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def check_tracked_files() -> list[str]:
    """Find private/generated files that are currently tracked by Git."""
    tracked_files = run_git_ls_files()
    if not tracked_files:
        return ["Could not inspect tracked files because `git` is not available on PATH."]

    problems = []
    for path in tracked_files:
        lowered = path.lower()
        if any(pattern.lower() in lowered for pattern in BLOCKED_TRACKED_PATTERNS):
            problems.append(f"Private/generated file is tracked: {path}")

    return problems


def check_public_copy(public_copy: Path) -> list[str]:
    """Find private/generated files inside the sanitized public copy."""
    problems = []
    if not public_copy.exists():
        problems.append(f"Public copy does not exist yet: {public_copy}")
        return problems

    for path in public_copy.rglob("*"):
        relative_parts = path.relative_to(public_copy).parts
        if relative_parts and relative_parts[0] == ".git":
            continue
        if any(part in BLOCKED_PUBLIC_PATH_PARTS for part in relative_parts):
            problems.append(f"Blocked folder/file appears in public copy: {path}")
            continue
        if path.is_file() and path.name in BLOCKED_PUBLIC_FILE_NAMES:
            problems.append(f"Blocked private file appears in public copy: {path}")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Check private repo and public copy safety.")
    parser.add_argument("--public-copy", default=str(DEFAULT_PUBLIC_COPY), help="Sanitized public copy folder.")
    parser.add_argument(
        "--skip-git",
        action="store_true",
        help="Skip tracked-file checks if Git is not available in this shell.",
    )
    args = parser.parse_args()

    problems: list[str] = []
    if not args.skip_git:
        problems.extend(check_tracked_files())
    problems.extend(check_public_copy(Path(args.public_copy)))

    if problems:
        print("Release safety check failed:")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("Release safety check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
