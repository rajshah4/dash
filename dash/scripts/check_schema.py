"""Schema drift detection (Layer 1 safety check).

Compares the knowledge/tables/*.json metadata against the live database
schema and reports mismatches: missing tables, new tables, type changes,
column additions/removals.

Usage:
    python -m dash.scripts.check_schema
    python -m dash.scripts.check_schema --fix  # auto-update JSON files
"""

import argparse
import json
import sys

from sqlalchemy import create_engine, inspect

from dash.context.semantic_model import load_table_metadata
from dash.paths import TABLES_DIR
from db import db_url


def check_schema(fix: bool = False) -> int:
    """Compare knowledge JSONs against live schema. Returns count of issues."""
    engine = create_engine(db_url)
    insp = inspect(engine)

    live_tables = set(insp.get_table_names())
    knowledge = load_table_metadata()
    knowledge_tables = {t["table_name"] for t in knowledge}

    issues = 0

    # ── Tables in knowledge but not in DB ──
    for name in sorted(knowledge_tables - live_tables):
        print(f"❌ MISSING TABLE: '{name}' is in knowledge but not in the database")
        issues += 1

    # ── Tables in DB but not in knowledge ──
    for name in sorted(live_tables - knowledge_tables):
        print(f"➕ NEW TABLE: '{name}' is in the database but has no knowledge file")
        if fix:
            _create_knowledge_file(name, insp)
            print(f"   → Created {TABLES_DIR / f'{name}.json'}")
        issues += 1

    # ── Column-level checks for known tables ──
    for table_meta in knowledge:
        tname = table_meta["table_name"]
        if tname not in live_tables:
            continue

        live_cols = {c["name"]: str(c["type"]) for c in insp.get_columns(tname)}
        known_cols = {}
        for col in table_meta.get("table_columns", []):
            known_cols[col["name"]] = col.get("type", "unknown")

        if not known_cols:
            # Knowledge file doesn't track columns — skip column checks
            continue

        # Missing columns (in knowledge but not in DB)
        for col_name in sorted(set(known_cols) - set(live_cols)):
            print(f"  ⚠️  {tname}.{col_name}: in knowledge but not in database")
            issues += 1

        # New columns (in DB but not in knowledge)
        for col_name in sorted(set(live_cols) - set(known_cols)):
            print(f"  ➕ {tname}.{col_name}: in database ({live_cols[col_name]}) but not in knowledge")
            issues += 1

        # Type mismatches
        for col_name in sorted(set(known_cols) & set(live_cols)):
            known_type = known_cols[col_name].lower()
            live_type = live_cols[col_name].lower()
            # Fuzzy match — "text" matches "TEXT", "int" matches "INTEGER" or "BIGINT"
            if not _types_match(known_type, live_type):
                print(f"  🔄 {tname}.{col_name}: knowledge says '{known_type}', database says '{live_type}'")
                issues += 1

    engine.dispose()

    if issues == 0:
        print("✅ Schema is in sync — no drift detected.")
    else:
        print(f"\n{'=' * 40}")
        print(f"Found {issues} issue(s).")
        if not fix:
            print("Run with --fix to auto-create missing knowledge files.")

    return issues


def _types_match(known: str, live: str) -> bool:
    """Fuzzy-match column types between knowledge and live schema."""
    # Normalize common type aliases
    aliases: dict[str, set[str]] = {
        "int": {"integer", "bigint", "int4", "int8", "smallint", "int"},
        "text": {"text", "varchar", "character varying", "char"},
        "float": {"float", "double precision", "real", "numeric", "decimal", "float8", "float4"},
        "bool": {"boolean", "bool"},
        "date": {"date"},
        "timestamp": {"timestamp", "timestamp without time zone", "timestamp with time zone", "timestamptz"},
    }
    for _canonical, variants in aliases.items():
        if known in variants and live in variants:
            return True
    # Exact match as fallback
    return known == live


def _create_knowledge_file(table_name: str, insp) -> None:
    """Auto-create a knowledge JSON file from live schema."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    cols = insp.get_columns(table_name)
    pk = insp.get_pk_constraint(table_name)

    table_columns = []
    for c in cols:
        col_info: dict = {
            "name": c["name"],
            "type": str(c["type"]).lower(),
            "description": "",  # placeholder for human annotation
        }
        table_columns.append(col_info)

    metadata = {
        "table_name": table_name,
        "table_description": f"Auto-discovered table: {table_name}",
        "use_cases": [],
        "data_quality_notes": [],
        "table_columns": table_columns,
    }

    if pk and pk.get("constrained_columns"):
        metadata["primary_key"] = pk["constrained_columns"]

    filepath = TABLES_DIR / f"{table_name}.json"
    with open(filepath, "w") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check schema drift between knowledge and database")
    parser.add_argument("--fix", action="store_true", help="Auto-create missing knowledge files")
    args = parser.parse_args()

    issues = check_schema(fix=args.fix)
    sys.exit(1 if issues > 0 else 0)


if __name__ == "__main__":
    main()
