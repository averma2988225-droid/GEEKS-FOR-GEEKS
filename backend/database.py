"""
Database module: CSV → SQLite ingestion and query execution.
Includes safety guards and logging.
"""
from __future__ import annotations


import sqlite3
import os
import logging
import pandas as pd


logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_BASE_DIR, "data", "queryviz.db")

# Look in backend/data/ first, then project root
_CSV_IN_DATA = os.path.join(_BASE_DIR, "data", "dataset.csv")
_CSV_IN_ROOT = os.path.join(os.path.dirname(_BASE_DIR), "dataset.csv")
CSV_PATH = _CSV_IN_DATA if os.path.exists(_CSV_IN_DATA) else _CSV_IN_ROOT
TABLE_NAME = "consumer_data"

_connection: sqlite3.Connection | None = None


def init_db() -> None:
    """Load CSV into SQLite. Creates the DB file if it doesn't exist."""
    global _connection

    df = pd.read_csv(CSV_PATH)

    # Clean column names: strip whitespace, lowercase
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    _connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    _connection.row_factory = sqlite3.Row

    # Write DataFrame to SQLite (replace if exists)
    df.to_sql(TABLE_NAME, _connection, if_exists="replace", index=False)

    row_count = _connection.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
    logger.info(f"Loaded {row_count} rows into '{TABLE_NAME}'")


def get_connection() -> sqlite3.Connection:
    """Return the active DB connection."""
    if _connection is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _connection


def execute_query(sql: str) -> dict:
    """
    Execute a READ-ONLY SQL query and return results.

    Returns:
        {
            "columns": ["col1", "col2", ...],
            "data": [{"col1": val, "col2": val}, ...],
            "row_count": int
        }

    Raises:
        ValueError: If SQL is not a SELECT statement (safety guard).
        Exception: For any SQL execution errors.
    """
    logger.info(f"Executing SQL: {sql[:100]}...")
    
    # Read-only guard
    cleaned = sql.strip().upper()
    if not cleaned.startswith("SELECT"):
        logger.error("Blocked non-SELECT query")
        raise ValueError("Only SELECT queries are allowed. Rejected potentially unsafe SQL.")

    blocked_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
    for kw in blocked_keywords:
        # Check for keyword as a standalone word (not part of column name)
        if f" {kw} " in f" {cleaned} ":
            logger.error(f"Blocked keyword: {kw}")
            raise ValueError(f"Blocked keyword '{kw}' detected. Only SELECT queries are allowed.")

    # Enforce LIMIT for performance
    if "LIMIT" not in cleaned:
        sql = sql.strip().rstrip(';') + " LIMIT 1000"
        logger.info("Auto-applied LIMIT 1000")

    conn = get_connection()
    
    try:
        cursor = conn.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        data = [dict(zip(columns, row)) for row in rows]
        
        logger.info(f"Query returned {len(data)} rows")

        return {
            "columns": columns,
            "data": data,
            "row_count": len(data),
        }
    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}")
        raise
