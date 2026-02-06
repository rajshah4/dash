"""
Database Session
================

PostgreSQL database connection utilities.
"""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from db.url import db_url


def get_engine() -> Engine:
    """Create a SQLAlchemy engine.

    Returns:
        Configured SQLAlchemy Engine instance.
    """
    return create_engine(db_url)
