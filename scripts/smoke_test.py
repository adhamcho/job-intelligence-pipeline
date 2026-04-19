"""Run quick project checks without doing a full job scrape.

This script is for fast confidence checks before committing or preparing a
public copy. It checks Python syntax, verifies core modules import, and runs
the release safety checks. In the private repo it also rebuilds the sanitized
public folder. In the public repo it validates the current checkout directly.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
}


def is_public_repo() -> bool:
    """Return True when running from the sanitized public repo."""
    return ROOT.name.endswith("_public")


def project_python_files() -> list[Path]:
    """Return project Python files while skipping generated and environment folders."""
    files: list[Path] = []
    for path in ROOT.rglob("*.py"):
        relative_parts = path.relative_to(ROOT).parts
        if any(part in SKIP_DIRS for part in relative_parts):
            continue
        files.append(path)
    return sorted(files)


def remove_pycache_dirs() -> None:
    """Remove Python bytecode caches created by local runs."""
    for path in ROOT.rglob("__pycache__"):
        if path.is_dir():
            for child in path.iterdir():
                if child.is_file():
                    child.unlink()
            path.rmdir()


def compile_project() -> None:
    """Fail early if any Python file has a syntax error."""
    for path in project_python_files():
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
    print("Python compile check passed.")


def import_core_modules() -> None:
    """Fail early if the refactored module imports are broken."""
    sys.path.insert(0, str(ROOT))
    __import__("main")
    __import__("pipeline.ranking")
    __import__("pipeline.queue_ops")
    __import__("pipeline.tracker_ops")
    __import__("intake.extended_collectors")
    print("Core import check passed.")


def run_command(command: list[str]) -> None:
    """Run one validation command and stop the smoke test if it fails."""
    result = subprocess.run(command, cwd=ROOT, text=True, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    remove_pycache_dirs()
    compile_project()
    import_core_modules()
    remove_pycache_dirs()
    if is_public_repo():
        print("Public repo validation passed.")
    else:
        run_command([sys.executable, "scripts/make_public_release.py", "--clean"])
        run_command([sys.executable, "scripts/check_release_safety.py", "--skip-git"])
    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
