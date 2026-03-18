"""
Conversation Context Manager: Handles conversational querying with context.
Stores conversation history and enables follow-up queries.
"""
from __future__ import annotations


import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# In-memory conversation storage
_conversations: Dict[str, Dict[str, Any]] = {}

# Cleanup old conversations (older than 1 hour)
CONVERSATION_TIMEOUT = timedelta(hours=1)


def generate_conversation_id() -> str:
    """Generate unique conversation ID."""
    return str(uuid.uuid4())[:12]


def create_conversation(conversation_id: str = None) -> str:
    """
    Create new conversation or return existing ID.
    
    Returns:
        conversation_id
    """
    if not conversation_id:
        conversation_id = generate_conversation_id()
    
    if conversation_id not in _conversations:
        _conversations[conversation_id] = {
            "conversation_id": conversation_id,
            "created_at": datetime.now(),
            "last_updated": datetime.now(),
            "history": []
        }
        logger.info(f"Created conversation: {conversation_id}")
    
    return conversation_id


def add_to_context(
    conversation_id: str,
    user_query: str,
    sql: str,
    data: list,
    columns: list,
    chart_type: str
) -> None:
    """
    Add query and response to conversation context.
    
    Args:
        conversation_id: Conversation ID
        user_query: User's natural language query
        sql: Generated SQL
        data: Query results
        columns: Column names
        chart_type: Chart type
    """
    if conversation_id not in _conversations:
        create_conversation(conversation_id)
    
    conv = _conversations[conversation_id]
    
    # Add to history
    conv["history"].append({
        "user_query": user_query,
        "sql": sql,
        "columns": columns,
        "row_count": len(data),
        "chart_type": chart_type,
        "timestamp": datetime.now()
    })
    
    # Keep only last 5 queries
    if len(conv["history"]) > 5:
        conv["history"] = conv["history"][-5:]
    
    # Update last context
    conv["last_query"] = user_query
    conv["last_sql"] = sql
    conv["last_columns"] = columns
    conv["last_updated"] = datetime.now()
    
    logger.info(f"Added to context: {conversation_id} (history: {len(conv['history'])})")


def get_context(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Get conversation context.
    
    Returns:
        {
            "last_query": str,
            "last_sql": str,
            "last_columns": list,
            "history": list
        } or None
    """
    if conversation_id not in _conversations:
        return None
    
    conv = _conversations[conversation_id]
    
    # Check if conversation expired
    if datetime.now() - conv["last_updated"] > CONVERSATION_TIMEOUT:
        logger.info(f"Conversation expired: {conversation_id}")
        del _conversations[conversation_id]
        return None
    
    return {
        "last_query": conv.get("last_query"),
        "last_sql": conv.get("last_sql"),
        "last_columns": conv.get("last_columns"),
        "history": conv.get("history", [])
    }


def is_follow_up_query(user_query: str) -> bool:
    """
    Detect if query is a follow-up/refinement.
    
    Returns:
        True if follow-up, False if new query
    """
    query_lower = user_query.lower().strip()
    
    # Follow-up indicators
    follow_up_patterns = [
        # Filters
        "only for", "filter by", "only", "just", "exclude", "include",
        # Modifications
        "now", "but", "also", "add", "remove", "without",
        # Limits
        "top", "bottom", "first", "last", "limit",
        # Sorting
        "sort by", "order by", "sorted",
        # Comparisons
        "more than", "less than", "greater than", "above", "below",
        # Specific values
        "for male", "for female", "tier 1", "tier 2", "tier 3"
    ]
    
    # Check if query starts with follow-up words
    follow_up_starts = ["now", "but", "also", "and", "only", "just", "filter", "sort", "top", "bottom"]
    if any(query_lower.startswith(word) for word in follow_up_starts):
        return True
    
    # Check for follow-up patterns
    if any(pattern in query_lower for pattern in follow_up_patterns):
        return True
    
    # Short queries are likely follow-ups
    if len(query_lower.split()) <= 4:
        return True
    
    return False


def build_context_prompt(user_query: str, context: Dict[str, Any], schema: str) -> str:
    """
    Build prompt with conversation context for LLM.
    
    Args:
        user_query: Current user query
        context: Conversation context
        schema: Database schema
    
    Returns:
        Formatted prompt with context
    """
    # Check if "top N" query on single-row result
    user_lower = user_query.lower().strip()
    if any(word in user_lower for word in ['top', 'first', 'bottom', 'last']):
        row_count = context.get('history', [])[-1].get('row_count', 0) if context.get('history') else 0
        if row_count == 1:
            # Return special instruction for single-row case
            return f"""The user asked: "{user_query}"

However, the previous query result already contains only 1 row.

Respond with EXACTLY this text:
SINGLE_ROW: Result already contains a single group. No need to limit further.
"""
    
    prompt = f"""You are an expert SQL analyst. The user is having a conversation and wants to refine their previous query.

DATABASE SCHEMA:
{schema}

PREVIOUS QUERY: {context['last_query']}
PREVIOUS SQL: {context['last_sql']}

CURRENT REQUEST: {user_query}

INSTRUCTIONS:
1. The user wants to MODIFY the previous SQL based on their new request.
2. Common modifications:
   - "only for females" → add WHERE gender = 'Female'
   - "filter by Tier 1" → add WHERE city_tier = 'Tier 1'
   - "top 5" → add ORDER BY <metric_column> DESC LIMIT 5 (where metric is AVG, SUM, COUNT, etc.)
   - "sort by age" → add ORDER BY age
   - "now for males" → change WHERE gender = 'Male'
3. For "top N" queries:
   - Identify the metric column (e.g., AVG(age), SUM(income), COUNT(*))
   - Add ORDER BY <metric_column> DESC before LIMIT
   - Example: "top 3" → ORDER BY <metric> DESC LIMIT 3
4. Keep the same SELECT and GROUP BY structure unless explicitly asked to change.
5. Output ONLY the modified SQL query, nothing else.
6. Do NOT wrap in markdown code blocks.

MODIFIED SQL:"""
    
    return prompt


def cleanup_old_conversations() -> int:
    """
    Remove expired conversations.
    
    Returns:
        Number of conversations removed
    """
    now = datetime.now()
    expired = [
        conv_id for conv_id, conv in _conversations.items()
        if now - conv["last_updated"] > CONVERSATION_TIMEOUT
    ]
    
    for conv_id in expired:
        del _conversations[conv_id]
    
    if expired:
        logger.info(f"Cleaned up {len(expired)} expired conversations")
    
    return len(expired)


def get_conversation_count() -> int:
    """Get number of active conversations."""
    return len(_conversations)


def reset_conversation(conversation_id: str) -> bool:
    """
    Reset/delete conversation.
    
    Returns:
        True if deleted, False if not found
    """
    if conversation_id in _conversations:
        del _conversations[conversation_id]
        logger.info(f"Reset conversation: {conversation_id}")
        return True
    return False
