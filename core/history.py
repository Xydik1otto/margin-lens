"""Batch calculation history: margin trend over saved batch runs.

The SPA stores batch runs in IndexedDB (store "batches"); this module holds
the tested logic that summarizes a run and derives the margin trend across
runs, so the numbers shown in the UI can never drift from the tested ones.
"""

from __future__ import annotations


def avg_margin(results: list[dict | float]) -> float:
    """Average margin (%) across batch rows.

    Accepts either margin numbers or result dicts with a ``margin`` key
    (the JS result shape). Empty input -> 0.0.
    """
    vals = [r if isinstance(r, (int, float)) else float(r.get("margin", 0.0) or 0.0)
            for r in results]
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def margin_trend(history: list[dict], eps: float = 0.05) -> dict:
    """Margin trend across batch runs (oldest -> newest).

    ``history`` entries need ``ts`` and ``avg_margin``; they are sorted by
    ``ts`` here, so the caller can pass them in any order.

    Returns::

        {
            "points":     [(ts, avg_margin), ...] in chronological order,
            "first":      oldest avg_margin,
            "last":       newest avg_margin,
            "delta_pp":   last - first (percentage points, rounded),
            "direction":  "up" | "down" | "flat" | "none",
        }

    ``direction`` is "none" with fewer than 2 runs (nothing to compare);
    deltas within ``eps`` percentage points count as "flat".
    """
    pts = sorted(((float(h["ts"]), float(h["avg_margin"])) for h in history),
                 key=lambda p: p[0])
    if not pts:
        return {"points": [], "first": None, "last": None,
                "delta_pp": 0.0, "direction": "none"}
    first, last = pts[0][1], pts[-1][1]
    delta = round(last - first, 2)
    if len(pts) < 2 or abs(delta) <= eps:
        direction = "flat"
    elif delta > 0:
        direction = "up"
    else:
        direction = "down"
    return {"points": pts, "first": first, "last": last,
            "delta_pp": delta, "direction": direction}


def summarize_batch(rows: list[dict]) -> dict:
    """One summary record for a batch run, as stored in IndexedDB.

    Each row is a calculated batch line: ``{name, platform, revenue, fees,
    net, margin}`` (margin in %). The summary is what the history list shows
    and what the trend is computed over.
    """
    return {
        "count": len(rows),
        "avg_margin": avg_margin(rows),
        "total_net": round(sum(float(r.get("net", 0.0)) for r in rows), 2),
        "best": max(rows, key=lambda r: float(r.get("margin", 0.0)))["name"] if rows else None,
    }
