"""
Load Knowledge - Lists and validates knowledge files.

The OpenHands SDK version of Dash uses file-based knowledge
(loaded directly into the system prompt via context modules)
rather than a vector database.

This script validates that all knowledge files are present and loadable.

Usage:
    python -m dash.scripts.load_knowledge
"""

import json

from dash.context.business_rules import load_business_rules
from dash.context.semantic_model import load_table_metadata
from dash.paths import KNOWLEDGE_DIR, QUERIES_DIR

if __name__ == "__main__":
    print(f"Knowledge directory: {KNOWLEDGE_DIR}\n")

    # Tables
    tables = load_table_metadata()
    print(f"Tables: {len(tables)} loaded")
    for t in tables:
        print(f"  - {t['table_name']}: {t.get('description', '')[:60]}")
    print()

    # Business rules
    business = load_business_rules()
    print(f"Metrics: {len(business['metrics'])}")
    print(f"Business rules: {len(business['business_rules'])}")
    print(f"Common gotchas: {len(business['common_gotchas'])}")
    print()

    # Queries
    if QUERIES_DIR.exists():
        query_files = list(QUERIES_DIR.glob("*.sql")) + list(QUERIES_DIR.glob("*.json"))
        print(f"Saved queries: {len(query_files)} files")
        for f in sorted(query_files):
            if f.suffix == ".json":
                try:
                    data = json.loads(f.read_text())
                    print(f"  - {data.get('name', f.stem)}: {data.get('question', '')[:50]}")
                except (json.JSONDecodeError, OSError):
                    print(f"  - {f.name} (error reading)")
            else:
                print(f"  - {f.name}")
    else:
        print("Saved queries: (directory not found)")

    print("\nDone!")
