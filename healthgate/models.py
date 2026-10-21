from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

SEVERITIES = ("fail", "warn", "info")


@dataclass
class Finding:
    check: str
    code: str
    severity: str
    message: str
    remediation: Optional[str] = None
    known: bool = False


@dataclass
class CheckResult:
    name: str
    findings: List[Finding] = field(default_factory=list)
    ran: bool = False
    error: Optional[str] = None

    @property
    def failed(self) -> bool:
        return any(f.severity == "fail" and not getattr(f, "known", False) for f in self.findings)


@dataclass
class BaselineEntry:
    check: str
    codes: List[str]
    reason: str


@dataclass
class PhaseConfig:
    name: str
    checks: List[str]
    gate: bool = True


@dataclass
class Config:
    project: str
    phases: List[PhaseConfig]
    checks: dict
