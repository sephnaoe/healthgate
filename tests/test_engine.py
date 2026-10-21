from pathlib import Path
from healthgate.engine import Engine
from healthgate.models import Config
from healthgate.checks import BUILTIN


def test_check_db_missing(tmp_path):
    engine = Engine(root=tmp_path)
    result = engine.run_check("check_db")
    assert not result.ran is False
    assert result.failed
    assert any(f.code == "db-missing" for f in result.findings)


def test_check_db_present(tmp_path):
    (tmp_path / "healthgate.db").write_text("x")
    engine = Engine(root=tmp_path)
    result = engine.run_check("check_db")
    assert result.failed is False
    assert any(f.code == "db-ok" for f in result.findings)


def test_check_disk_ok(tmp_path):
    engine = Engine(root=tmp_path)
    result = engine.run_check("check_disk")
    assert not result.failed


def _init_git(tmp_path):
    import subprocess
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t"], cwd=tmp_path, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "t"], cwd=tmp_path, capture_output=True
    )


def test_check_git_clean_clean(tmp_path):
    _init_git(tmp_path)
    engine = Engine(root=tmp_path)
    result = engine.run_check("check_git_clean")
    assert result.failed is False


def test_check_git_clean_dirty(tmp_path):
    _init_git(tmp_path)
    (tmp_path / "dirty.txt").write_text("x")
    engine = Engine(root=tmp_path)
    result = engine.run_check("check_git_clean")
    assert result.failed


def test_unknown_check_is_incomplete(tmp_path):
    engine = Engine(root=tmp_path)
    result = engine.run_check("no_such_check")
    assert not result.ran
    assert result.error is not None


def test_baseline_suppresses_finding(tmp_path):
    engine = Engine(root=tmp_path)
    engine.add_baseline("check_db", "db-missing", "known deployment target, provisioned later")
    result = engine.run_check("check_db")
    assert result.failed is False
    assert any(getattr(f, "known", False) for f in result.findings)


def test_run_phase_busy_is_incomplete(tmp_path):
    engine = Engine(root=tmp_path)
    config = Config(project="p", phases=[], checks={})
    from healthgate.models import PhaseConfig
    config.phases = [PhaseConfig(name="ci", checks=["check_disk"], gate=True)]
    report, verdict = engine.run_config(config, None, busy=True)
    assert verdict == 3


def test_drift_flags_missing_check(tmp_path):
    engine = Engine(root=tmp_path)
    config = Config(project="p", phases=[], checks={})
    from healthgate.models import PhaseConfig
    config.phases = [PhaseConfig(name="ci", checks=["check_disk", "ghost_check"], gate=True)]
    missing = engine.drift(config)
    assert "ghost_check" in missing
