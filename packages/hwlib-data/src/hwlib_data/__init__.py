"""hwlib-data: bundled component catalog as a PyPI data wheel.

Read-only access to the deterministic bundle (``library.json``,
``library.sqlite``, ``index.json``) shipped inside this package:

    from hwlib_data import data_path

    sqlite_path = data_path() / "library.sqlite"
    # use sqlite3, json, etc.

The data is staged into the wheel at build time by ``build_hook.py``,
which copies ``dist/library.*`` from the repo root. Consumers see a
self-contained package: ``pip install hwlib-data`` is enough.

Versioning: ``hwlib-data`` and ``hwlib-mcp`` are versioned independently
on purpose. Component-data updates (frequent) decouple from server-code
updates (infrequent).
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

__all__ = ["data_path"]


def data_path() -> Path:
    """Return the directory containing ``library.{json,sqlite,index.json}``.

    Resolves to the package's bundled ``data/`` directory regardless of
    install mode (wheel, sdist, editable). Returned path can be passed to
    ``sqlite3.connect`` / ``open`` / ``json.load`` directly.
    """
    return Path(str(files("hwlib_data") / "data"))
