"""hw-registry pin-conflict graph validator."""

from .diagnostic import Diagnostic
from .errors import (
    BundleNotBuilt,
    ConflictsError,
    SystemYamlError,
    UnresolvedComponentRef,
)
from .graph import build_graph
from .loader import ComponentPlacement, System, load_system
from .rules import ALL_RULES, run_all
from .sarif import to_sarif

__all__ = [
    "ALL_RULES",
    "BundleNotBuilt",
    "ComponentPlacement",
    "ConflictsError",
    "Diagnostic",
    "System",
    "SystemYamlError",
    "UnresolvedComponentRef",
    "build_graph",
    "load_system",
    "run_all",
    "to_sarif",
]
