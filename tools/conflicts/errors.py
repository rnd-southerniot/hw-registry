"""Named exceptions raised by the pin-conflict checker."""

from __future__ import annotations


class ConflictsError(Exception):
    """Base for all conflict-checker-emitted errors."""


class BundleNotBuilt(ConflictsError):
    """``dist/library.sqlite`` was not found; the caller must build the bundle first."""


class UnresolvedComponentRef(ConflictsError):
    """A ``components[].ref`` in the system YAML does not match any bundled component."""


class SystemYamlError(ConflictsError):
    """The system YAML failed structural validation (missing keys, wrong shape)."""
