"""
LLM Engine: Text-to-SQL generation using Google Gemini 2.5 Flash.
Handles prompt construction, API calls, SQL extraction, chart type inference,
and query validation with hallucination guards.
"""
from __future__ import annotations


import os
import re
import logging
import google.generativeai as genai
from dotenv import load_dotenv
from schema_info import get_schema_prompt, get_column_names

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Configure Gemini
_api_key = os.getenv("GEMINI_API_KEY")
if not _api_key:
    logger.warning("GEMINI_API_KEY not set — LLM calls will fail")
else:
    genai.configure(api_key=_api_key)

model = genai.GenerativeModel("gemini-2.5-flash")

CLARIFICATION_PROMPT = """You are a helpful SQL assistant. The user asked a vague or ambiguous question.

User question: {question}

Available schema:
{schema}

Determine if the question is:
1. CLEAR - can be answered directly
2. AMBIGUOUS - needs clarification

If AMBIGUOUS, respond with: CLARIFY: <specific question to ask user>
If CLEAR, respond with: CLEAR

Examples of ambiguous questions:
- "Show me data" → CLARIFY: What specific data would you like to see? (e.g., age, income, gender distribution)
- "Get stats" → CLARIFY: Which statistics? (e.g., average, sum, count, min, max)
- "Show customers" → CLARIFY: What information about customers? (e.g., count, demographics, spending patterns)
"""

SYSTEM_PROMPT = """You are an expert SQL analyst. Your job is to convert natural language questions into valid SQLite SQL queries.

DATABASE SCHEMA:
{schema}

STRICT RULES:
1. Output ONLY a valid SQLite SELECT query — nothing else.
2. Use ONLY the columns and table listed above. Do NOT invent columns.
3. For categorical filters, use exact values: gender IN ('Male','Female','Other'), city_tier IN ('Tier 1','Tier 2','Tier 3'), shopping_preference IN ('Online','Store','Hybrid').
4. Use appropriate aggregations (AVG, SUM, COUNT, MIN, MAX) when the question implies summarization.
5. ALWAYS use GROUP BY when you have both aggregated and non-aggregated columns in SELECT.
6. LIMIT results to at most 1000 rows for performance.
7. Use ROUND() for decimal results — round to 2 decimal places.
8. If the question is ambiguous or cannot be answered with the available data, respond with: CANNOT_ANSWER: <reason>
9. If the question references columns that don't exist, respond with: INVALID_COLUMN: <column_name>
10. Do NOT wrap the SQL in markdown code blocks or backticks. Output raw SQL only.
11. When using aggregations without GROUP BY, SELECT only aggregated columns.
"""

CHART_PROMPT = """Based on the user's question and the SQL query results, determine the best chart type.

User question: {question}
SQL query: {sql}
Result columns: {columns}
Number of rows: {row_count}

Choose exactly ONE from: bar, line, pie, scatter, histogram, kpi
Reply with ONLY the chart type name, nothing else.

Guidelines:
- "over time", "trend", "monthly", "yearly" → line
- "by category", "compare", "breakdown", "by region/city/gender" → bar
- "share", "proportion", "percentage", "distribution of categories" → pie
- "correlation", "vs", "relationship between" → scatter
- "spread", "distribution" of numeric values → histogram
- Single summary metric, "total", "average of" with one result row → kpi
"""


def check_query_clarity(user_query: str) -> dict:
    """
    Check if user query is clear or needs clarification.
    
    Returns:
        {"clear": bool, "clarification": str | None}
    """
    # Quick heuristics for obviously vague queries
    vague_patterns = [
        r'^(show|get|give|display)\s+(me\s+)?(data|info|information|stats|statistics)\s*$',
        r'^(what|show)\s+(is|are)\s+(the|my)\s+(data|info)\s*$',
        r'^(analyze|check|look)\s*$',
    ]
    
    query_lower = user_query.lower().strip()
    
    for pattern in vague_patterns:
        if re.match(pattern, query_lower):
            return {
                "clear": False,
                "clarification": "Your question is too vague. Please specify what you'd like to know (e.g., 'average age by gender', 'total customers', 'income distribution')."
            }
    
    # Check if query is too short (likely vague)
    if len(query_lower.split()) <= 2:
        return {
            "clear": False,
            "clarification": "Please provide more details about what you'd like to analyze."
        }
    
    # Use LLM for deeper analysis (with fallback)
    try:
        schema = get_schema_prompt()
        prompt = CLARIFICATION_PROMPT.format(question=user_query, schema=schema)
        response = model.generate_content(prompt)
        result = response.text.strip()
        
        if result.startswith("CLARIFY:"):
            clarification = result.replace("CLARIFY:", "").strip()
            return {"clear": False, "clarification": clarification}
        
        return {"clear": True, "clarification": None}
        
    except Exception as e:
        logger.warning(f"Clarity check failed: {e}")
        # Assume clear if LLM fails
        return {"clear": True, "clarification": None}


def generate_sql(user_query: str, error_context: str = None, dataset_id: str = None, conversation_context: dict = None) -> dict:
    """
    Convert natural language query to SQL using Gemini.

    Args:
        user_query: Natural language question
        error_context: Previous SQL error for retry
        dataset_id: Optional dataset ID for uploaded CSV
        conversation_context: Optional conversation context for follow-up queries

    Returns:
        {"sql": str, "error": str | None, "suggested_columns": list | None, "needs_clarification": bool, "clarification": str | None, "context_used": bool}
    """
    logger.info(f"Processing query: {user_query} (dataset_id={dataset_id}, has_context={conversation_context is not None})")
    
    # Check if this is a follow-up query with context
    context_used = False
    if conversation_context and not error_context:
        from conversation_manager import is_follow_up_query, build_context_prompt
        
        if is_follow_up_query(user_query):
            logger.info("Detected follow-up query, using conversation context")
            context_used = True
            
            # Get schema
            if dataset_id:
                from csv_handler import get_dataset, get_schema_prompt_for_dataset
                dataset = get_dataset(dataset_id)
                if not dataset:
                    return {
                        "sql": None,
                        "error": f"Dataset '{dataset_id}' not found. Please upload a CSV first.",
                        "suggested_columns": None,
                        "needs_clarification": False,
                        "clarification": None,
                        "context_used": False
                    }
                schema = get_schema_prompt_for_dataset(dataset_id)
            else:
                schema = get_schema_prompt()
            
            # Build context-aware prompt
            prompt = build_context_prompt(user_query, conversation_context, schema)
            
            try:
                response = model.generate_content(prompt)
                raw = response.text.strip()
                logger.info(f"Context-aware SQL: {raw[:100]}...")

                # Clean
                raw = re.sub(r"^```(?:sql)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
                raw = raw.strip()
                
                # Check for single-row message
                if raw.startswith("SINGLE_ROW:"):
                    message = raw.replace("SINGLE_ROW:", "").strip()
                    logger.info(f"Single-row result detected: {message}")
                    return {
                        "sql": None,
                        "error": None,
                        "suggested_columns": None,
                        "needs_clarification": True,
                        "clarification": message,
                        "context_used": True
                    }

                if raw.upper().startswith("SELECT"):
                    return {
                        "sql": raw,
                        "error": None,
                        "suggested_columns": None,
                        "needs_clarification": False,
                        "clarification": None,
                        "context_used": True
                    }
            except Exception as e:
                logger.warning(f"Context-aware generation failed: {str(e)}, falling back to normal")
                context_used = False
    
    # Normal query processing (no context or context failed)
    # Step 1: Check query clarity (skip if retry)
    if not error_context:
        clarity = check_query_clarity(user_query)
        if not clarity["clear"]:
            logger.info(f"Query needs clarification: {clarity['clarification']}")
            return {
                "sql": None,
                "error": None,
                "suggested_columns": None,
                "needs_clarification": True,
                "clarification": clarity["clarification"],
                "context_used": False
            }
    
    # Step 2: Get schema (default or uploaded dataset)
    if dataset_id:
        from csv_handler import get_dataset, get_schema_prompt_for_dataset
        dataset = get_dataset(dataset_id)
        if not dataset:
            return {
                "sql": None,
                "error": f"Dataset '{dataset_id}' not found. Please upload a CSV first.",
                "suggested_columns": None,
                "needs_clarification": False,
                "clarification": None,
                "context_used": False
            }
        schema = get_schema_prompt_for_dataset(dataset_id)
        table_name = dataset["table_name"]
    else:
        schema = get_schema_prompt()
        table_name = "consumer_data"
    
    # Step 3: Generate SQL
    prompt = SYSTEM_PROMPT.format(schema=schema) + f"\n\nUser question: {user_query}"
    
    if error_context:
        prompt += f"\n\nPrevious SQL failed with error: {error_context}\nPlease fix the SQL."
        logger.info(f"Retry with error context: {error_context}")
    
    prompt += "\n\nSQL:"

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        logger.info(f"LLM response: {raw[:100]}...")

        # Clean: remove markdown code blocks if present
        raw = re.sub(r"^```(?:sql)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        raw = raw.strip()

        # Check for "cannot answer"
        if raw.upper().startswith("CANNOT_ANSWER"):
            reason = raw.replace("CANNOT_ANSWER:", "").strip()
            logger.warning(f"Cannot answer: {reason}")
            return {
                "sql": None,
                "error": f"Unable to answer: {reason}",
                "suggested_columns": list(get_column_names())[:10],
                "needs_clarification": False,
                "clarification": None,
                "context_used": context_used
            }
        
        # Check for invalid column response
        if raw.upper().startswith("INVALID_COLUMN"):
            col_name = raw.replace("INVALID_COLUMN:", "").strip()
            suggestions = _find_similar_columns(col_name)
            logger.warning(f"Invalid column: {col_name}")
            return {
                "sql": None,
                "error": f"Column '{col_name}' not found in schema.",
                "suggested_columns": suggestions,
                "needs_clarification": False,
                "clarification": None,
                "context_used": context_used
            }

        # Basic validation: must start with SELECT
        if not raw.upper().startswith("SELECT"):
            logger.error(f"Invalid SQL format: {raw[:100]}")
            return {
                "sql": None,
                "error": f"Could not generate valid SQL. Please rephrase your question.",
                "suggested_columns": None,
                "needs_clarification": False,
                "clarification": None,
                "context_used": context_used
            }

        # Validate columns exist in schema
        validation = _validate_columns(raw)
        if not validation["valid"]:
            logger.warning(f"Column validation failed: {validation['error']}")
            return {
                "sql": None, 
                "error": validation["error"],
                "suggested_columns": validation["suggestions"],
                "needs_clarification": False,
                "clarification": None,
                "context_used": context_used
            }

        logger.info(f"SQL generated successfully: {raw}")
        return {
            "sql": raw,
            "error": None,
            "suggested_columns": None,
            "needs_clarification": False,
            "clarification": None,
            "context_used": context_used
        }

    except Exception as e:
        logger.error(f"LLM API error: {str(e)}")
        return {
            "sql": None,
            "error": f"Service temporarily unavailable. Please try again.",
            "suggested_columns": None,
            "needs_clarification": False,
            "clarification": None,
            "context_used": context_used
        }


def _find_similar_columns(invalid_col: str) -> list[str]:
    """
    Find similar column names for suggestions.
    """
    valid_columns = get_column_names()
    invalid_lower = invalid_col.lower()
    
    # Exact substring matches
    matches = [c for c in valid_columns if invalid_lower in c.lower() or c.lower() in invalid_lower]
    
    if matches:
        return matches[:5]
    
    # Return top 10 columns as fallback
    return valid_columns[:10]


def _validate_columns(sql: str) -> dict:
    """
    Validate that SQL only uses columns from schema.
    Focuses on catching obvious invalid columns, not aliases.
    
    Returns:
        {"valid": bool, "error": str | None, "suggestions": list | None}
    """
    valid_columns = set(get_column_names())
    
    # Simple check: look for column references after FROM/WHERE/GROUP BY/ORDER BY
    sql_lower = sql.lower()
    
    # Extract words that look like column names in key positions
    patterns = [
        r'from\s+consumer_data\s+where\s+([a-z_][a-z0-9_]*)',
        r'group\s+by\s+([a-z_][a-z0-9_]*)',
        r'order\s+by\s+([a-z_][a-z0-9_]*)',
    ]
    
    # Also check for obvious column references in WHERE/HAVING
    where_pattern = r'\b([a-z_][a-z0-9_]*)\s*(?:=|>|<|>=|<=|!=|<>|IN|LIKE|BETWEEN)'
    
    suspicious_cols = []
    for pattern in patterns:
        matches = re.findall(pattern, sql_lower)
        suspicious_cols.extend(matches)
    
    suspicious_cols.extend(re.findall(where_pattern, sql_lower))
    
    # Filter out SQL keywords
    sql_keywords = {'select', 'from', 'where', 'group', 'by', 'order', 'limit', 'having',
                    'and', 'or', 'not', 'in', 'as', 'on', 'null', 'is', 'like', 'between',
                    'consumer_data', 'all', 'any', 'exists', 'case', 'when', 'then', 'else'}
    
    invalid_cols = []
    for col in suspicious_cols:
        if col not in sql_keywords and col not in valid_columns:
            invalid_cols.append(col)
    
    if invalid_cols:
        suggestions = _find_similar_columns(invalid_cols[0])
        
        return {
            "valid": False,
            "error": f"Column not found: {', '.join(set(invalid_cols[:3]))}. Did you mean one of these?",
            "suggestions": suggestions
        }
    
    return {"valid": True, "error": None, "suggestions": None}


def determine_chart_type(user_query: str, sql: str, columns: list[str], row_count: int) -> str:
    """
    Determine the best chart type using smart rules.
    """
    logger.info(f"Determining chart type for {row_count} rows, {len(columns)} columns")
    
    q = user_query.lower()
    sql_lower = sql.lower()
    
    # Rule 1: Single value → KPI
    if row_count == 1 and len(columns) <= 2:
        logger.info("Chart type: kpi (single value)")
        return "kpi"
    
    # Rule 2: Time-based queries → Line
    time_keywords = ['trend', 'over time', 'monthly', 'yearly', 'by month', 'by year', 
                     'daily', 'weekly', 'time series', 'timeline']
    if any(kw in q for kw in time_keywords):
        logger.info("Chart type: line (time-based)")
        return "line"
    
    # Rule 3: Proportion/percentage → Pie
    proportion_keywords = ['share', 'proportion', 'percentage', 'distribution of', 
                          'breakdown of', 'composition', 'split']
    if any(kw in q for kw in proportion_keywords) and row_count <= 10:
        logger.info("Chart type: pie (proportion)")
        return "pie"
    
    # Rule 4: Correlation/relationship → Scatter
    correlation_keywords = ['correlation', ' vs ', 'versus', 'relationship between', 
                           'compare.*to', 'against']
    if any(re.search(kw, q) for kw in correlation_keywords) and len(columns) >= 2:
        logger.info("Chart type: scatter (correlation)")
        return "scatter"
    
    # Rule 5: Distribution of numeric values → Histogram
    if 'distribution' in q and len(columns) == 1:
        logger.info("Chart type: histogram (distribution)")
        return "histogram"
    
    # Rule 6: Comparison by category → Bar (default)
    comparison_keywords = ['by', 'per', 'each', 'compare', 'comparison', 'across']
    if any(kw in q for kw in comparison_keywords) or row_count > 1:
        logger.info("Chart type: bar (comparison)")
        return "bar"
    
    # Default fallback
    logger.info("Chart type: bar (default)")
    return "bar"
