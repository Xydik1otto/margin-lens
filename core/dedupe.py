"""Duplicate detection: the same product listed on multiple platforms.

Sellers routinely list one item on Etsy + Depop + Poshmark; this module finds
those duplicate listings in a batch so they can be compared side-by-side in
one click (which platform actually nets more for the same product?).

Matching is intentionally conservative: normalized-name equality, not fuzzy
matching — a wrong "duplicate" is worse than a missed one.
"""

from __future__ import annotations

import re
from collections import defaultdict

_WORD_RE = re.compile(r"[a-z0-9а-яїієґё]+", re.IGNORECASE)
_MULTI_SPACE = re.compile(r"\s+")


def normalize_name(name: str, min_len: int = 3) -> str:
    """Canonical form of a listing title for duplicate matching.

    Lowercase, strip punctuation/symbols, collapse whitespace. Tokens shorter
    than ``min_len`` characters are dropped ("vintage tee, L" -> "vintage tee").
    Returns "" when nothing meaningful remains (such items never match).
    """
    words = _WORD_RE.findall((name or "").lower())
    return _MULTI_SPACE.sub(" ", " ".join(w for w in words if len(w) >= min_len)).strip()


def find_duplicates(items: list[dict]) -> list[list[dict]]:
    """Group batch rows that share the same normalized product name.

    Each item needs at least ``name``; rows with an empty normalized name are
    never grouped. Returns groups of 2+ items, sorted by group size
    (largest first), each group's items in input order.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        key = normalize_name(it.get("name", ""))
        if key:
            groups[key].append(it)
    out = [g for g in groups.values() if len(g) >= 2]
    out.sort(key=lambda g: (-len(g), g[0].get("name", "")))
    return out


def best_platform(group: list[dict], key: str = "net") -> dict | None:
    """The row with the highest ``net`` (or any numeric key) in a group."""
    if not group:
        return None
    return max(group, key=lambda r: float(r.get(key, 0.0) or 0.0))


def group_spread(group: list[dict]) -> float:
    """Net-profit spread across the group (best - worst), rounded to cents."""
    nets = [float(r.get("net", 0.0) or 0.0) for r in group]
    return round(max(nets) - min(nets), 2) if nets else 0.0
