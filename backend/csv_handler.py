"""
CSV Upload Handler: Dynamic dataset upload and schema inference.
Handles file validation, schema extraction, and temporary table creation.
"""
from __future__ import annotations


import os
import uuid
import logging
from io import BytesIO
import pandas as pd
import sqlite3
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# Store uploaded datasets in memory (session-based)
_uploaded_datasets: Dict[str, Dict[str, Any]] = {}


def generate_dataset_id() -> str:
    """Generate unique dataset ID."""
    return str(uuid.uuid4())[:8]


def validate_csv(file_content: bytes) -> Dict[str, Any]:
    """
    Validate CSV file and return basic info.
    
    Returns:
        {"valid": bool, "error": str | None, "row_count": int, "columns": list}
    """
    try:
        # Try to read CSV
        df = pd.read_csv(BytesIO(file_content))
        
        # Check if empty
        if df.empty:
            return {"valid": False, "error": "CSV file is empty", "row_count": 0, "columns": []}
        
        # Check column count
        if len(df.columns) == 0:
            return {"valid": False, "error": "CSV has no columns", "row_count": 0, "columns": []}
        
        # Check row count
        if len(df) > 100000:
            return {"valid": False, "error": "CSV too large (max 100,000 rows)", "row_count": len(df), "columns": []}
        
        return {
            "valid": True,
            "error": None,
            "row_count": len(df),
            "columns": df.columns.tolist()
        }
        
    except Exception as e:
        logger.error(f"CSV validation failed: {str(e)}")
        return {"valid": False, "error": f"Invalid CSV format: {str(e)}", "row_count": 0, "columns": []}


def infer_schema(df: pd.DataFrame) -> Dict[str, str]:
    """
    Infer column types from DataFrame.
    
    Returns:
        {"column_name": "type", ...}
    """
    schema = {}
    
    for col in df.columns:
        dtype = df[col].dtype
        
        if pd.api.types.is_integer_dtype(dtype):
            schema[col] = "INTEGER"
        elif pd.api.types.is_float_dtype(dtype):
            schema[col] = "REAL"
        elif pd.api.types.is_bool_dtype(dtype):
            schema[col] = "INTEGER"  # SQLite doesn't have BOOLEAN
        else:
            schema[col] = "TEXT"
    
    return schema


def upload_csv(file_content: bytes, filename: str, connection: sqlite3.Connection) -> Dict[str, Any]:
    """
    Process uploaded CSV and create temporary table.
    
    Args:
        file_content: Raw CSV bytes
        filename: Original filename
        connection: SQLite connection
    
    Returns:
        {
            "dataset_id": str,
            "table_name": str,
            "columns": list,
            "schema": dict,
            "row_count": int,
            "preview": list (first 5 rows)
        }
    """
    logger.info(f"Processing upload: {filename}")
    
    # Validate CSV
    validation = validate_csv(file_content)
    if not validation["valid"]:
        raise ValueError(validation["error"])
    
    # Read CSV into DataFrame
    df = pd.read_csv(BytesIO(file_content))
    
    # Clean column names
    df.columns = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]
    
    # Generate unique identifiers
    dataset_id = generate_dataset_id()
    table_name = f"uploaded_{dataset_id}"
    
    # Infer schema
    schema = infer_schema(df)
    
    # Create table in SQLite
    df.to_sql(table_name, connection, if_exists="replace", index=False)
    
    # Get preview (first 5 rows)
    preview = df.head(5).to_dict(orient="records")
    
    # Store metadata
    dataset_info = {
        "dataset_id": dataset_id,
        "table_name": table_name,
        "filename": filename,
        "columns": df.columns.tolist(),
        "schema": schema,
        "row_count": len(df),
        "preview": preview
    }
    
    _uploaded_datasets[dataset_id] = dataset_info
    
    logger.info(f"Dataset uploaded: {dataset_id} ({len(df)} rows, {len(df.columns)} columns)")
    
    return dataset_info


def get_dataset(dataset_id: str) -> Dict[str, Any] | None:
    """Get dataset metadata by ID."""
    return _uploaded_datasets.get(dataset_id)


def get_schema_prompt_for_dataset(dataset_id: str) -> str:
    """
    Generate schema prompt for uploaded dataset.
    
    Returns:
        Formatted schema string for LLM prompt
    """
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise ValueError(f"Dataset {dataset_id} not found")
    
    lines = [f"TABLE: {dataset['table_name']}", "COLUMNS:"]
    
    for col, col_type in dataset["schema"].items():
        lines.append(f"  - {col} ({col_type})")
    
    lines.append("")
    lines.append(f"TOTAL ROWS: {dataset['row_count']}")
    
    return "\n".join(lines)


def list_datasets() -> List[Dict[str, Any]]:
    """List all uploaded datasets."""
    return [
        {
            "dataset_id": info["dataset_id"],
            "filename": info["filename"],
            "row_count": info["row_count"],
            "columns": info["columns"]
        }
        for info in _uploaded_datasets.values()
    ]


def delete_dataset(dataset_id: str, connection: sqlite3.Connection) -> bool:
    """
    Delete uploaded dataset and drop table.
    
    Returns:
        True if deleted, False if not found
    """
    dataset = get_dataset(dataset_id)
    if not dataset:
        return False
    
    # Drop table — validate table name to prevent injection
    table_name = dataset['table_name']
    if not table_name.startswith('uploaded_') or not table_name[9:].isalnum():
        logger.error(f"Invalid table name: {table_name}")
        return False
    try:
        connection.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        logger.info(f"Dropped table: {table_name}")
    except Exception as e:
        logger.error(f"Failed to drop table: {str(e)}")
    
    # Remove from memory
    del _uploaded_datasets[dataset_id]
    logger.info(f"Dataset deleted: {dataset_id}")
    
    return True
