"""
Semantic Model
==============

Builds schema metadata from knowledge files for the Data Agent.

Loads:
- Table metadata from knowledge/tables/*.json
- Business definitions from knowledge/business/*.json

Produces a human-readable summary for the system prompt that includes
table descriptions, data quality notes, and business rules.
"""

import json
from pathlib import Path
from typing import Any

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
TABLES_DIR = KNOWLEDGE_DIR / "tables"
BUSINESS_DIR = KNOWLEDGE_DIR / "business"


def load_table_metadata() -> list[dict[str, Any]]:
    """Load table metadata from knowledge/tables/*.json files."""
    tables = []
    if not TABLES_DIR.exists():
        return tables

    for f in sorted(TABLES_DIR.glob("*.json")):
        with open(f) as fp:
            table = json.load(fp)
            tables.append(
                {
                    "table_name": table["table_name"],
                    "table_description": table["table_description"],
                    "use_cases": table.get("use_cases", []),
                    "data_quality_notes": table.get("data_quality_notes", []),
                    "columns": table.get("table_columns", []),
                }
            )
    return tables


def load_business_definitions() -> dict[str, Any]:
    """Load business definitions from knowledge/business/*.json files."""
    business = {
        "metrics": [],
        "business_rules": [],
        "common_gotchas": [],
    }

    if not BUSINESS_DIR.exists():
        return business

    for f in sorted(BUSINESS_DIR.glob("*.json")):
        with open(f) as fp:
            data = json.load(fp)
            if "metrics" in data:
                business["metrics"].extend(data["metrics"])
            if "business_rules" in data:
                business["business_rules"].extend(data["business_rules"])
            if "common_gotchas" in data:
                business["common_gotchas"].extend(data["common_gotchas"])

    return business


def build_semantic_model() -> dict[str, Any]:
    """Build complete semantic model from all knowledge files."""
    return {
        "tables": load_table_metadata(),
        "business": load_business_definitions(),
    }


def format_semantic_model_for_prompt(model: dict[str, Any]) -> str:
    """Format semantic model as human-readable text for system prompt."""
    lines = []

    # Tables section
    lines.append("## TABLES")
    lines.append("")

    for table in model.get("tables", []):
        lines.append(f"### {table['table_name']}")
        lines.append(f"{table['table_description']}")
        lines.append("")

        if table.get("use_cases"):
            lines.append("**Use cases:**")
            for use_case in table["use_cases"]:
                lines.append(f"- {use_case}")
            lines.append("")

        if table.get("data_quality_notes"):
            lines.append("**Data quality notes (IMPORTANT):**")
            for note in table["data_quality_notes"]:
                lines.append(f"- {note}")
            lines.append("")

        if table.get("columns"):
            lines.append("**Columns:**")
            for col in table["columns"]:
                col_type = col.get("type", "unknown")
                col_desc = col.get("description", "")
                lines.append(f"- `{col['name']}` ({col_type}): {col_desc}")
            lines.append("")

    # Business definitions section
    business = model.get("business", {})

    if business.get("metrics"):
        lines.append("## METRICS")
        lines.append("")
        for metric in business["metrics"]:
            lines.append(f"**{metric['name']}**: {metric['definition']}")
            lines.append(f"  - Table: {metric['table']}")
            lines.append(f"  - Calculation: {metric['calculation']}")
            lines.append("")

    if business.get("business_rules"):
        lines.append("## BUSINESS RULES")
        lines.append("")
        for rule in business["business_rules"]:
            lines.append(f"- {rule}")
        lines.append("")

    if business.get("common_gotchas"):
        lines.append("## COMMON GOTCHAS (READ CAREFULLY)")
        lines.append("")
        for gotcha in business["common_gotchas"]:
            lines.append(f"**{gotcha['issue']}**")
            lines.append(f"  - Tables: {', '.join(gotcha['tables_affected'])}")
            lines.append(f"  - Solution: {gotcha['solution']}")
            lines.append("")

    return "\n".join(lines)


# Build model at module load time
SEMANTIC_MODEL = build_semantic_model()
SEMANTIC_MODEL_STR = format_semantic_model_for_prompt(SEMANTIC_MODEL)
SEMANTIC_MODEL_JSON = json.dumps(SEMANTIC_MODEL, indent=2)
