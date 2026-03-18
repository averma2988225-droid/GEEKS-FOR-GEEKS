"""
Generate short insights from query results.
Identifies highest/lowest values and comparisons.
"""
from __future__ import annotations


import logging

logger = logging.getLogger(__name__)


def generate_insight(data: list[dict], columns: list[str], chart_type: str) -> str:
    """
    Generate 1-2 line insight from query results.
    
    Args:
        data: Query result rows
        columns: Column names
        chart_type: Chart type being displayed
    
    Returns:
        Short insight string (max 2 lines)
    """
    if not data or len(data) == 0:
        return ""
    
    try:
        # Single value (KPI)
        if len(data) == 1 and len(columns) <= 2:
            return _insight_single_value(data[0], columns)
        
        # Multiple rows
        if len(columns) == 2:
            return _insight_comparison(data, columns)
        
        return ""
    
    except Exception as e:
        logger.warning(f"Insight generation failed: {e}")
        return ""


def _insight_single_value(row: dict, columns: list[str]) -> str:
    """Insight for single KPI value."""
    col = columns[-1]  # Last column is usually the metric
    val = row[col]
    
    if isinstance(val, (int, float)):
        return f"The result is {val:,.2f}." if isinstance(val, float) else f"The result is {val:,}."
    
    return f"The result is {val}."


def _insight_comparison(data: list[dict], columns: list[str]) -> str:
    """Insight for comparison data (category + value)."""
    if len(data) < 2:
        return ""
    
    cat_col = columns[0]
    val_col = columns[1]
    
    # Extract numeric values
    numeric_rows = []
    for row in data:
        val = row.get(val_col)
        if isinstance(val, (int, float)):
            numeric_rows.append((row[cat_col], val))
    
    if len(numeric_rows) < 2:
        return ""
    
    # Find highest and lowest
    sorted_rows = sorted(numeric_rows, key=lambda x: x[1], reverse=True)
    highest = sorted_rows[0]
    lowest = sorted_rows[-1]
    
    # Format values
    h_val = f"{highest[1]:,.2f}" if isinstance(highest[1], float) else f"{highest[1]:,}"
    l_val = f"{lowest[1]:,.2f}" if isinstance(lowest[1], float) else f"{lowest[1]:,}"
    
    # Calculate difference if meaningful
    if highest[1] > 0 and lowest[1] > 0:
        diff_pct = ((highest[1] - lowest[1]) / lowest[1]) * 100
        if diff_pct > 10:  # Only mention if significant
            return f"{highest[0]} has the highest value ({h_val}), while {lowest[0]} has the lowest ({l_val}). That's {diff_pct:.0f}% higher."
    
    return f"{highest[0]} has the highest value ({h_val}), while {lowest[0]} has the lowest ({l_val})."
