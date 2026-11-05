"""Markdown table export: results formatted for posts and reports.

The SPA copies the results table to the clipboard as GitHub-flavored
Markdown; this module holds the tested escaping/rendering logic.
"""

from __future__ import annotations


def md_escape(cell: str) -> str:
    """Escape a cell for a GFM table (pipes, newlines)."""
    return str(cell).replace("|", "\\|").replace("\n", " ")


def markdown_table(headers: list[str], rows: list[list]) -> str:
    """Render a GitHub-flavored Markdown table.

    Numbers are passed through as-is; every cell is escaped with
    :func:`md_escape`. An empty rows list still yields a valid header block.
    """
    head = "| " + " | ".join(md_escape(h) for h in headers) + " |"
    sep = "|" + "|".join("---" for _ in headers) + "|"
    body = ["| " + " | ".join(md_escape(c) for c in row) + " |" for row in rows]
    return "\n".join([head, sep] + body)


def batch_results_markdown(rows: list[dict], title: str = "Margin Lens — результати") -> str:
    """Batch results as a Markdown table (name/platform/revenue/fees/net/margin)."""
    headers = ["Назва", "Платформа", "Revenue", "Збори", "Net", "Margin %"]
    lines = [f"## {title}", ""]
    table_rows = [
        [r.get("name", ""), r.get("platform", ""),
         f"{float(r.get('revenue', 0.0)):.2f}",
         f"{float(r.get('fees', 0.0)):.2f}",
         f"{float(r.get('net', 0.0)):.2f}",
         f"{float(r.get('margin', 0.0)):.1f}"]
        for r in rows
    ]
    return "\n".join(lines + [markdown_table(headers, table_rows), ""])


def compare_results_markdown(rows: list[dict], title: str = "Margin Lens — порівняння каналів") -> str:
    """Channel comparison as a Markdown table (platform/fees/vat/net/margin/breakeven)."""
    headers = ["Канал", "Збори", "VAT", "Net", "Margin %", "Breakeven"]
    table_rows = []
    for r in rows:
        be = r.get("breakeven")
        table_rows.append([
            r.get("platform", ""),
            f"{float(r.get('fees', 0.0)):.2f}",
            f"{float(r.get('vat', 0.0)):.2f}",
            f"{float(r.get('net', 0.0)):.2f}",
            f"{float(r.get('margin', 0.0)):.2f}",
            "—" if be is None else f"{float(be):.2f}",
        ])
    return "\n".join([f"## {title}", "", markdown_table(headers, table_rows), ""])
