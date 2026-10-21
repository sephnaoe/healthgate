"""Known-failure baseline: scoped suppression of findings by check + code."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - yaml optional for baseline authoring
    yaml = None


@dataclass
class Baseline:
    entries: Dict[str, "Entry"] = field(default_factory=dict)

    @dataclass
    class Entry:
        check: str
        codes: List[str]
        reason: str

    def suppress(self, check: str, code: str) -> Optional[str]:
        entry = self.entries.get(check)
        if entry is not None and code in entry.codes:
            return entry.reason
        return None

    def add(self, check: str, code: str, reason: str) -> None:
        entry = self.entries.get(check)
        if entry is None:
            self.entries[check] = self.Entry(check=check, codes=[code], reason=reason)
            return
        if code not in entry.codes:
            entry.codes.append(code)

    def to_dict(self) -> dict:
        return {
            "baseline": [
                {"check": e.check, "codes": list(e.codes), "reason": e.reason}
                for e in self.entries.values()
            ]
        }

    @classmethod
    def from_file(cls, path: Path) -> "Baseline":
        baseline = cls()
        if not path.exists() or yaml is None:
            return baseline
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for item in data.get("baseline", []):
            for code in item.get("codes", []):
                baseline.add(item["check"], code, item.get("reason", ""))
        return baseline

    def write(self, path: Path) -> None:
        if yaml is None:
            raise RuntimeError("PyYAML required to write baseline file")
        path.write_text(yaml.safe_dump(self.to_dict(), sort_keys=False), encoding="utf-8")
