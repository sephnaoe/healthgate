import json
import subprocess
import sys
from pathlib import Path

MODULE = [sys.executable, "-m", "healthgate"]


def run(args, root):
    return subprocess.run(MODULE + args, cwd=root, capture_output=True, text=True)


def test_check_exit_pass(tmp_path):
    import subprocess
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t"], cwd=tmp_path, capture_output=True
    )
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, capture_output=True)
    (tmp_path / "healthgate.yml").write_text(
        "project: t\nphases:\n  - name: ci\n    checks:\n      - check_disk\n      - check_git_clean\n"
    )
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True
    )
    res = run(["check", "--config", "healthgate.yml", "--phase", "ci"], tmp_path)
    assert res.returncode == 0, res.stderr


def test_check_exit_fail(tmp_path):
    (tmp_path / "healthgate.yml").write_text(
        "project: t\nphases:\n  - name: ci\n    checks:\n      - check_db\n"
    )
    res = run(["check", "--config", "healthgate.yml", "--phase", "ci"], tmp_path)
    assert res.returncode == 1, res.stderr


def test_check_busy_exit_3(tmp_path):
    (tmp_path / "healthgate.yml").write_text(
        "project: t\nphases:\n  - name: ci\n    checks:\n      - check_disk\n"
    )
    res = run(["check", "--config", "healthgate.yml", "--phase", "ci", "--busy"], tmp_path)
    assert res.returncode == 3, res.stderr


def test_check_json(tmp_path):
    (tmp_path / "healthgate.yml").write_text(
        "project: t\nphases:\n  - name: ci\n    checks:\n      - check_disk\n"
    )
    res = run(["check", "--config", "healthgate.yml", "--phase", "ci", "--json"], tmp_path)
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["project"] == "t"
    assert data["phases"][0]["name"] == "ci"


def test_drift_clean(tmp_path):
    (tmp_path / "healthgate.yml").write_text(
        "project: t\nphases:\n  - name: ci\n    checks:\n      - check_disk\n"
    )
    res = run(["drift", "--config", "healthgate.yml"], tmp_path)
    assert res.returncode == 0, res.stderr


def test_list(tmp_path):
    (tmp_path / "healthgate.yml").write_text(
        "project: t\nphases:\n  - name: ci\n    checks:\n      - check_disk\n"
    )
    res = run(["list", "--config", "healthgate.yml"], tmp_path)
    assert res.returncode == 0
    assert "check_disk" in res.stdout
