"""Fuzzy-match suggestion engine for ``ComponentNotFound`` errors.

When an agent hallucinates a slug from training data —
``sensors/sensirion/sht40`` instead of ``sht41`` — the response includes
the closest existing IDs so the agent learns the right one in a single
round-trip instead of retrying the same wrong ID three times.

stdlib's ``difflib.get_close_matches`` does this in 8 lines; we don't
need Levenshtein, ratcliff-obershelp is plenty for component slugs.
"""

from __future__ import annotations

import difflib
from collections.abc import Iterable


def suggest_close_ids(
    target_id: str,
    all_ids: Iterable[str],
    n: int = 3,
    cutoff: float = 0.6,
) -> list[str]:
    """Return up to *n* component IDs from *all_ids* that look most like *target_id*.

    *cutoff* is the minimum similarity ratio (0.0–1.0); 0.6 catches typos
    and near-misses without flooding the response with unrelated IDs.
    """
    return difflib.get_close_matches(target_id, list(all_ids), n=n, cutoff=cutoff)
