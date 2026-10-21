"""Command-line interface for healthgate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from .engine import Engine, OK, FAIL, USAGE, INCOMPLETE
from .models import Config


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="healthgate",
        description="Declarative health-check engine. Gate project phases on checks that resolve to PASS/SKIPPED.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="run checks for a phase and exit with a status code")
    p_check.add_argument("--config", required=True, help="path to healthgate.yml")
    p_check.add_argument("--phase", help="phase name to run (default: all phases)")
    p_check.add_argument("--root", default=".", help="project root (default: current dir)")
    p_check.add_argument("--busy", action="store_true", help="simulate busy owner: defer all checks (exit 3)")
    p_check.add_argument("--json", action="store_true", help="emit JSON report instead of human text")
    p_check.add_argument("--checks-module", help="optional Python file with extra check_* functions")

    p_list = sub.add_parser("list", help="list checks and phases from a config")
    p_list.add_argument("--config", required=True)
    p_list.add_argument("--root", default=".")

    p_base = sub.add_parser("baseline", help="manage the known-failure baseline")
    p_base.add_argument("--config", required=True)
    p_base.add_argument("--baseline", required=True, help="baseline.yml path")
    p_base.add_argument("--add", nargs="+", help="suppress a finding: CHECK=CODE:REASON")
    p_base.add_argument("--write-baseline", action="store_true", help="write baseline file after changes")

    p_drift = sub.add_parser("drift", help="report config-referenced checks that are not registered")
    p_drift.add_argument("--config", required=True)
    p_drift.add_argument("--root", default=".")
    p_drift.add_argument("--checks-module")

    return parser


def _render_text(report: dict) -> str:
    lines: List[str] = [f"project: {report.get('project', '')}"]
    for phase in report.get("phases", []):
        lines.append(f"phase {phase['name']}: {'PASS' if phase['verdict'] == OK else 'FAIL' if phase['verdict'] == FAIL else 'INCOMPLETE'}")
        for check in phase.get("checks", []):
            status = "ran" if check["ran"] else "deferred"
            if check["error"]:
                status = f"error({check['error']})"
            lines.append(f"  {check['name']}: {status}")
            for f in check.get("findings", []):
                tag = " [known]" if f.get("known") else ""
                lines.append(f"    - {f['code']} ({f['severity']}): {f['message']}{tag}")
    return "\n".join(lines)


def _cmd_check(args: argparse.ArgumentParser, engine: Engine) -> int:
    config = engine.load_config(Path(args.config))
    engine.load_checks_module(Path(args.checks_module) if args.checks_module else None)
    report, verdict = engine.run_config(config, args.phase, busy=args.busy)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(_render_text(report))
    return verdict


def _cmd_list(args: argparse.ArgumentParser, engine: Engine) -> int:
    config = engine.load_config(Path(args.config))
    engine.load_checks_module(Path(args.checks_module) if getattr(args, "checks_module", None) else None)
    print(f"project: {config.project}")
    print(f"registered checks: {', '.join(sorted(engine.checks)) or '(none)'}")
    for phase in config.phases:
        print(f"phase {phase.name}: {', '.join(phase.checks) or '(no checks)'}  gate={phase.gate}")
    return OK


def _cmd_baseline(args: argparse.ArgumentParser, engine: Engine) -> int:
    baseline_path = Path(args.baseline)
    engine.load_baseline(baseline_path if baseline_path.exists() else None)
    if args.add:
        for item in args.add:
            if "=" not in item or ":" not in item.split("=", 1)[1]:
                print(f"invalid --add item (use CHECK=CODE:REASON): {item}", file=sys.stderr)
                return USAGE
            check, rest = item.split("=", 1)
            code, reason = rest.split(":", 1)
            engine.add_baseline(check, code, reason)
            print(f"baseline: {check}/{code} suppressed -> {reason}")
    if args.write_baseline:
        engine.baseline.write(baseline_path)
        print(f"wrote baseline to {baseline_path}")
    else:
        print(json.dumps(engine.baseline.to_dict(), indent=2))
    return OK


def _cmd_drift(args: argparse.ArgumentParser, engine: Engine) -> int:
    config = engine.load_config(Path(args.config))
    engine.load_checks_module(Path(args.checks_module) if args.checks_module else None)
    missing = engine.drift(config)
    if missing:
        print("drift: referenced but not registered:")
        for name in missing:
            print(f"  - {name}")
        return FAIL
    print("drift: all referenced checks are registered")
    return OK


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    engine = Engine(root=Path(args.root))
    if args.command == "check":
        return _cmd_check(args, engine)
    if args.command == "list":
        return _cmd_list(args, engine)
    if args.command == "baseline":
        return _cmd_baseline(args, engine)
    if args.command == "drift":
        return _cmd_drift(args, engine)
    parser.print_help()
    return USAGE


if __name__ == "__main__":
    sys.exit(main())
