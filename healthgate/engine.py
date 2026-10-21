"""Core engine: load config, run checks, apply baseline, gate phases."""

from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

from .checks import BUILTIN
from .baseline import Baseline
from .models import (
    Finding,
    CheckResult,
    BaselineEntry,
    PhaseConfig,
    Config,
    SEVERITIES,
)

OK = 0
FAIL = 1
USAGE = 2
INCOMPLETE = 3


class Engine:
    def __init__(self, root: Path, checks: Optional[Dict[str, Callable]] = None):
        self.root = root
        self.checks: Dict[str, Callable] = dict(BUILTIN)
        if checks:
            self.checks.update(checks)
        self.baseline = Baseline()
        self._latency: Dict[str, float] = {}

    # ---- configuration -------------------------------------------------
    def load_config(self, path: Path) -> Config:
        if yaml is None:
            raise RuntimeError("PyYAML is required to read config files")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        phases = [
            PhaseConfig(
                name=p.get("name", "phase"),
                checks=list(p.get("checks", [])),
                gate=bool(p.get("gate", True)),
            )
            for p in data.get("phases", [])
        ]
        return Config(project=data.get("project", ""), phases=phases, checks=data.get("checks", {}))

    def load_checks_module(self, module_path: Optional[Path]) -> None:
        if not module_path or not module_path.exists():
            return
        spec = importlib.util.spec_from_file_location("healthgate_user_checks", module_path)
        if spec is None or spec.loader is None:
            return
        module = importlib.util.module_from_spec(spec)
        sys.modules["healthgate_user_checks"] = module
        spec.loader.exec_module(module)
        for name in dir(module):
            obj = getattr(module, name)
            if callable(obj) and name.startswith("check_"):
                self.checks[name] = obj

    # ---- baseline ------------------------------------------------------
    def load_baseline(self, path: Optional[Path]) -> None:
        self.baseline = Baseline.from_file(path) if path else Baseline()

    def add_baseline(self, check: str, code: str, reason: str) -> None:
        self.baseline.add(check, code, reason)

    # ---- execution -----------------------------------------------------
    def run_check(self, name: str) -> CheckResult:
        result = CheckResult(name=name)
        fn = self.checks.get(name)
        if fn is None:
            result.error = f"unknown check: {name}"
            return result
        start = time.perf_counter()
        try:
            raw = fn(self.root)
            result.findings = list(raw)
            result.ran = True
        except Exception as exc:  # noqa: BLE001 - a check must never kill the run
            result.error = str(exc)
        finally:
            self._latency[name] = time.perf_counter() - start
        # tag suppressed findings as known
        for finding in result.findings:
            reason = self.baseline.suppress(result.name, finding.code)
            if reason is not None:
                finding.known = True  # type: ignore[attr-defined]
                finding.message = f"[baseline: {reason}] {finding.message}"
        return result

    def run_phase(self, phase: PhaseConfig, busy: bool = False) -> Tuple[List[CheckResult], int]:
        results: List[CheckResult] = []
        worst = OK
        for name in phase.checks:
            if busy:
                results.append(CheckResult(name=name, ran=False))
                worst = max(worst, INCOMPLETE)
                continue
            result = self.run_check(name)
            results.append(result)
            if result.error or not result.ran:
                worst = max(worst, INCOMPLETE)
            elif result.failed:
                worst = max(worst, FAIL)
        if busy:
            worst = INCOMPLETE
        return results, worst

    def run_config(self, config: Config, phase_name: Optional[str], busy: bool = False) -> Tuple[dict, int]:
        if phase_name:
            phases = [p for p in config.phases if p.name == phase_name]
            if not phases:
                raise ValueError(f"phase not found: {phase_name}")
        else:
            phases = config.phases or []
        report = {"project": config.project, "phases": []}
        overall = OK
        for phase in phases:
            results, verdict = self.run_phase(phase, busy=busy)
            overall = max(overall, verdict)
            report["phases"].append(
                {
                    "name": phase.name,
                    "verdict": verdict,
                    "gate": phase.gate,
                    "checks": [self._check_report(r) for r in results],
                }
            )
        return report, overall

    def _check_report(self, result: CheckResult) -> dict:
        return {
            "name": result.name,
            "ran": result.ran,
            "error": result.error,
            "verdict": INCOMPLETE if (result.error or not result.ran) else (FAIL if result.failed else OK),
            "findings": [
                {
                    "code": f.code,
                    "severity": f.severity,
                    "message": f.message,
                    "known": getattr(f, "known", False),
                    "remediation": f.remediation,
                }
                for f in result.findings
            ],
        }

    # ---- drift ---------------------------------------------------------
    def drift(self, config: Config) -> List[str]:
        """Return config-referenced check names that are not registered."""
        missing: List[str] = []
        for phase in config.phases:
            for name in phase.checks:
                if name not in self.checks:
                    missing.append(name)
        return missing
