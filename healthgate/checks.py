"""Built-in health checks. Each check takes a root Path and returns list[Finding]."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List

from .models import Finding

OK = "ok"
FAIL = "fail"
WARN = "warn"
INFO = "info"


def check_db(root: Path) -> List[Finding]:
    """Verify a configured sqlite database file exists and is readable."""
    db = root / "healthgate.db"
    if not db.exists():
        return [Finding("check_db", "db-missing", FAIL,
                        "database file healthgate.db not found",
                        "run migrations or create healthgate.db at project root")]
    try:
        db.stat()
    except OSError as exc:
        return [Finding("check_db", "db-unreadable", FAIL,
                        f"database file unreadable: {exc}",
                        "fix file permissions on healthgate.db")]
    return [Finding("check_db", "db-ok", INFO, "database present and readable")]


def check_disk(root: Path) -> List[Finding]:
    """Ensure free disk space on the project drive is above 1 GB."""
    try:
        total, used, free = shutil.disk_usage(root)
    except OSError as exc:
        return [Finding("check_disk", "disk-error", FAIL,
                        f"cannot read disk usage: {exc}",
                        "verify the project path is accessible")]
    free_gb = free / (1024 ** 3)
    if free_gb < 1.0:
        return [Finding("check_disk", "disk-low", FAIL,
                        f"only {free_gb:.2f} GB free on {root}",
                        "free up disk space before deploying")]
    return [Finding("check_disk", "disk-ok", INFO,
                    f"{free_gb:.2f} GB free on {root}")]


def check_git_clean(root: Path) -> List[Finding]:
    """Ensure the working tree has no uncommitted changes."""
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        return [Finding("check_git_clean", "git-error", FAIL,
                        f"git unavailable: {exc}",
                        "install git or run from a git repository")]
    if out.returncode != 0:
        return [Finding("check_git_clean", "git-error", FAIL,
                        f"git status failed (rc={out.returncode}): {out.stderr.strip()}",
                        "run from inside a git repository")]
    if out.stdout.strip():
        return [Finding("check_git_clean", "git-dirty", FAIL,
                        "working tree has uncommitted changes",
                        "commit or stash changes before deploying")]
    return [Finding("check_git_clean", "git-clean", INFO, "working tree clean")]


BUILTIN = {
    "check_db": check_db,
    "check_disk": check_disk,
    "check_git_clean": check_git_clean,
}
