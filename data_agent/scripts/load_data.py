"""
Load F1 Data
============

Downloads Formula 1 data (1950-2020) from S3 and loads it into PostgreSQL.

Usage:
    python -m data_agent.scripts.load_data

This script downloads CSV files from a public S3 bucket and loads them
into the PostgreSQL database used by the Data Agent.
"""

import sys
from io import StringIO

import pandas as pd
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import db_url from the db module
try:
    from db import db_url

    DB_URL = db_url
except ImportError:
    # Fallback for standalone execution
    DB_URL = "postgresql+psycopg://ai:ai@localhost:5432/ai"

S3_URI = "https://agno-public.s3.amazonaws.com/f1"

FILES_TO_TABLES = {
    f"{S3_URI}/constructors_championship_1958_2020.csv": "constructors_championship",
    f"{S3_URI}/drivers_championship_1950_2020.csv": "drivers_championship",
    f"{S3_URI}/fastest_laps_1950_to_2020.csv": "fastest_laps",
    f"{S3_URI}/race_results_1950_to_2020.csv": "race_results",
    f"{S3_URI}/race_wins_1950_to_2020.csv": "race_wins",
}


def load_f1_data(verbose: bool = True) -> bool:
    """Load F1 data from S3 into PostgreSQL.

    Args:
        verbose: Print progress messages.

    Returns:
        True if all tables loaded successfully, False otherwise.
    """
    from sqlalchemy import create_engine

    engine = create_engine(DB_URL)

    success = True
    for file_path, table_name in FILES_TO_TABLES.items():
        try:
            if verbose:
                print(f"Downloading {table_name}...", end=" ", flush=True)

            response = requests.get(file_path, verify=False, timeout=30)
            response.raise_for_status()

            df = pd.read_csv(StringIO(response.text))

            if verbose:
                print(f"Loading ({len(df)} rows)...", end=" ", flush=True)

            df.to_sql(table_name, engine, if_exists="replace", index=False)

            if verbose:
                print("Done")

        except Exception as e:
            if verbose:
                print(f"FAILED: {e}")
            success = False

    if verbose:
        if success:
            print("\nAll data loaded successfully!")
        else:
            print("\nSome tables failed to load. Check errors above.")

    return success


def main() -> int:
    """Main entry point."""
    print("Loading F1 data into PostgreSQL...")
    print(f"Database: {DB_URL.split('@')[1] if '@' in DB_URL else DB_URL}")
    print()

    success = load_f1_data(verbose=True)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
