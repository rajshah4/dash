"""Analyze query results and provide insights."""

from typing import Any

from agno.tools import tool


@tool
def analyze_results(
    results: list[dict[str, Any]],
    question: str,
    sql_query: str,
    context: str | None = None,
) -> str:
    """Analyze query results and provide insights.

    Args:
        results: Query results as list of dicts.
        question: Original user question.
        sql_query: SQL query that produced results.
        context: Optional additional context.

    Returns:
        Formatted analysis with findings and suggestions.
    """
    if not results:
        return f"""## No Results Found

The query returned no results. Possible causes:
- No data matching criteria
- Filter too restrictive
- Column type mismatch (e.g., position might be TEXT not INTEGER)

```sql
{sql_query}
```"""

    lines = ["## Analysis", ""]

    # Key findings
    lines.append(f"**Found {len(results)} result(s)**")
    first = results[0]

    # Highlight top result
    name_cols = [k for k in first if k.lower() in ("name", "driver", "team", "venue")]
    value_cols = [k for k in first if k.lower() in ("wins", "championships", "points", "count", "total")]
    if name_cols and value_cols:
        lines.append(f"Top: {first[name_cols[0]]} with {first[value_cols[0]]} {value_cols[0]}")
    lines.append("")

    # Results table (max 10 rows)
    display = results[:10]
    cols = list(display[0].keys())
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for row in display:
        lines.append("| " + " | ".join(str(row.get(c, ""))[:30] for c in cols) + " |")

    if len(results) > 10:
        lines.append(f"\n_Showing 10 of {len(results)} results_")

    if context:
        lines.extend(["", f"**Context:** {context}"])

    return "\n".join(lines)
