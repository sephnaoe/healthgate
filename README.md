# healthgate

Declarative, registry-driven health-check engine. A project declares its health
checks in a single YAML file and gates CI/deployment phases on checks resolving
to PASS or SKIPPED — with a baseline for known failures, a BUSY ≠ FAIL
distinction, and an exit-code taxonomy CI schedulers can branch on.

## Why this exists

Most projects have no systematic, version-controlled way to answer
"is my system healthy enough to deploy?" HealthGate makes the *set of checks
itself* the configuration artifact (`healthgate.yml`), so operational maturity
is readable, reviewable, and editable by anyone on the team.

The idea is ported from a production-grade maintenance layer I built for a
personal agent system, then generalized into a standalone, dependency-light
Python package. Nothing here is tied to that system — this is a clean,
interview-explainable implementation of the pattern.

## Key ideas

- **Phase-gating** — a phase is "done" only when its named checks all ran and
  resolved cleanly. "The test suite doesn't exist yet" is *unverified*, not
  green (exit 3).
- **Baseline for known failures** — suppress findings by check + code, each
  entry requiring a reason. A known-dirty area cannot hide *new* breakage.
- **BUSY ≠ FAIL** — when the owner's dev server is running, a scheduled run
  defers (exit 3 + "skipped") instead of turning red.
- **Exit-code taxonomy** — 0 OK, 1 fail, 2 usage, 3 incomplete. CI schedulers
  branch on these rather than parsing text.

## Quick start

```bash
pip install healthgate
```

Create `healthgate.yml`:

```yaml
project: my-app
phases:
  - name: ci
    gate: true
    checks:
      - check_disk
      - check_git_clean
  - name: deploy
    gate: true
    checks:
      - check_db
      - check_disk
```

Run it:

```bash
healthgate check --config healthgate.yml --phase ci
echo $?   # 0 = pass, 1 = fail, 3 = incomplete
```

Built-in checks: `check_db`, `check_disk`, `check_git_clean`. Add your own by
dropping `check_*` functions into a module and passing `--checks-module`.

## Baseline (known failures)

```bash
healthgate baseline --baseline baseline.yml \
  --add check_db=db-missing:provisioned-later \
  --write-baseline
```

Suppressed findings still appear in output (tagged `[known]`) but do not fail
the phase.

## CI

`.github/workflows/ci.yml` installs the package and runs `pytest` on every
push and pull request.

## License

MIT.
