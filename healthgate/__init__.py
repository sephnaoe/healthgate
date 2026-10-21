"""healthgate - declarative, registry-driven health-check engine.

A project declares its health checks in a single YAML file and gates
deployments/phases on those checks resolving to PASS or SKIPPED.
"""

from .engine import Engine
from .models import Finding, CheckResult, BaselineEntry, PhaseConfig, Config
from .cli import main

__all__ = [
    "Engine",
    "Finding",
    "CheckResult",
    "BaselineEntry",
    "PhaseConfig",
    "Config",
    "main",
]

__version__ = "0.1.0"
