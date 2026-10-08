"""
Data models for the QueryViz analysis engine.

This module will contain the structured representations
used to describe analytical requests and decisions.
"""
from enum import Enum
from dataclasses import dataclass,field
from typing import List,Optional,Dict,Set
from datetime import datetime
class Intent(str,Enum):
    """
    Query intent classification. Determines analysis workflow.
    
    Canonical example questions for each intent:
    - KPI: "What are our sales this quarter?"
    - TREND: "How have sales changed over the last 12 months?"
    - COMPARISON: "How did Q3 revenue compare to Q2?"
    - BREAKDOWN: "Show me sales by region"
    - DISTRIBUTION: "What's the distribution of order values?"
    - RANKING: "Which products have the highest revenue?"
    - FILTER: "Show me orders from Europe"
    - CORRELATION: "Is customer age correlated with churn?"
    - DIAGNOSTIC: "Why did revenue drop last quarter?"
    - FORECAST: "What will revenue be in Q4?"
    - UNKNOWN: Classification failed or intent unclear
    """
    
    KPI = "KPI"
    """
    Request for single metric value (point-in-time or aggregate).
    Workflow: Execute single query → Verify → Evidence → Response
    Latency budget: <3s
    Examples:
    - "What are our sales this year?"
    - "How many customers do we have?"
    - "What's our churn rate?"
    """
    
    TREND = "TREND"
    """
    Request for metric change over time (time series).
    Workflow: Execute time-series query → Verify → Evidence → Visualization
    Latency budget: <5s
    Examples:
    - "How have sales changed over the last 12 months?"
    - "Show me the trend in churn rate"
    - "Is growth accelerating or decelerating?"
    """
    
    COMPARISON = "COMPARISON"
    """
    Request for metric comparison (YoY, QoQ, plan vs. actual, A vs. B).
    Workflow: Execute two queries → Calculate difference → Verify → Evidence
    Latency budget: <5s
    Examples:
    - "How did Q3 revenue compare to Q2?"
    - "What's the YoY growth rate?"
    - "Did we hit our sales target?"
    """
    
    BREAKDOWN = "BREAKDOWN"
    """
    Request for metric segmentation by dimension (region, product, customer, etc.).
    Workflow: Execute grouped query → Verify → Evidence → Rank/visualize
    Latency budget: <5s
    Examples:
    - "Show me sales by region"
    - "Break down churn by customer segment"
    - "Revenue by product category"
    """
    
    DISTRIBUTION = "DISTRIBUTION"
    """
    Request for distribution shape of metric (spread, histogram, percentiles).
    Workflow: Execute quantile query → Verify → Visualize
    Latency budget: <5s
    Examples:
    - "What's the distribution of order values?"
    - "How is revenue spread across customers?"
    - "What percentile am I in for this metric?"
    """
    
    RANKING = "RANKING"
    """
    Request for top-N or bottom-N items by metric.
    Workflow: Execute ORDER BY query → Verify → Rank
    Latency budget: <3s
    Examples:
    - "Which products have the highest revenue?"
    - "Top 10 customers by spend"
    - "Worst performing regions"
    """
    
    FILTER = "FILTER"
    """
    Request for data subset by constraint (WHERE clause).
    Workflow: Execute filtered query → Verify
    Latency budget: <3s
    Examples:
    - "Show me orders from Europe"
    - "List customers with churn=true"
    - "Sales for Q3 only"
    """
    
    CORRELATION = "CORRELATION"
    """
    Request for relationship between two metrics.
    Workflow: Execute correlation analysis → Verify → Evidence
    Latency budget: <8s
    Examples:
    - "Is customer age correlated with churn?"
    - "Does ad spend correlate with revenue?"
    - "Is there a relationship between product quality and retention?"
    """
    
    DIAGNOSTIC = "DIAGNOSTIC"
    """
    Request for root cause / explanation ("Why?").
    Workflow: Route to COMPLEX → Planner → Completeness check → Executor 
              → Verify → Evidence → Claims → Confidence Scoring
    Latency budget: <20s P99
    Examples:
    - "Why did revenue drop last quarter?"
    - "What caused the churn spike?"
    - "Why did this product launch fail?"
    """
    
    FORECAST = "FORECAST"
    """
    Request for future prediction.
    Workflow: Time-series analysis → Forecast model → Project → Verify
    Latency budget: <10s
    Examples:
    - "What will revenue be in Q4?"
    - "Predict churn rate for next month"
    - "Forecast customer growth"
    """
    
    UNKNOWN = "UNKNOWN"
    """
    Classification failed or intent unclear.
    Fallback response: Ask user for clarification or return error.
    """
