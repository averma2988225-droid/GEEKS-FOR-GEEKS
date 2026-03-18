"""
Schema metadata for prompt injection into the LLM.
Provides the LLM with full knowledge of the database structure.
"""

TABLE_NAME = "consumer_data"

COLUMNS = {
    "age": {"type": "INTEGER", "desc": "Consumer's age in years"},
    "monthly_income": {"type": "INTEGER", "desc": "Monthly financial income in currency units"},
    "daily_internet_hours": {"type": "REAL", "desc": "Hours spent on internet daily"},
    "smartphone_usage_years": {"type": "INTEGER", "desc": "Years of smartphone usage"},
    "social_media_hours": {"type": "REAL", "desc": "Daily hours on social media"},
    "online_payment_trust": {"type": "INTEGER", "desc": "Trust score in online payment gateways (1-10)"},
    "tech_savvy_score": {"type": "INTEGER", "desc": "Familiarity with technology (1-10)"},
    "monthly_online_orders": {"type": "INTEGER", "desc": "Number of online orders per month"},
    "monthly_store_visits": {"type": "INTEGER", "desc": "Number of physical store visits per month"},
    "avg_online_spend": {"type": "INTEGER", "desc": "Average monetary amount spent online"},
    "avg_store_spend": {"type": "INTEGER", "desc": "Average monetary amount spent in physical stores"},
    "discount_sensitivity": {"type": "INTEGER", "desc": "How much discounts influence purchase decisions (1-10)"},
    "return_frequency": {"type": "INTEGER", "desc": "How often the customer returns products (1-10)"},
    "avg_delivery_days": {"type": "INTEGER", "desc": "Average number of days to receive deliveries"},
    "delivery_fee_sensitivity": {"type": "INTEGER", "desc": "Aversion to delivery fees (1-10)"},
    "free_return_importance": {"type": "INTEGER", "desc": "Importance of free returns policy (1-10)"},
    "product_availability": {"type": "INTEGER", "desc": "Perceived product availability score (1-10)"},
    "impulse_buying_score": {"type": "INTEGER", "desc": "Tendency to buy impulsively (1-10)"},
    "need_touch_feel_score": {"type": "INTEGER", "desc": "Need to physically touch/feel products before buying (1-10)"},
    "brand_loyalty_score": {"type": "INTEGER", "desc": "Dedication to specific brands (1-10)"},
    "environmental_awareness": {"type": "INTEGER", "desc": "Environmental consideration in purchases (1-10)"},
    "time_pressure_level": {"type": "INTEGER", "desc": "Level of rush/urgency during shopping (1-10)"},
    "gender": {"type": "TEXT", "desc": "Gender identity (Male, Female, Other)"},
    "city_tier": {"type": "TEXT", "desc": "City classification (Tier 1, Tier 2, Tier 3)"},
    "shopping_preference": {"type": "TEXT", "desc": "Primary shopping channel preference (Online, Store, Hybrid)"},
}


def get_schema_prompt() -> str:
    """Generate a formatted schema string for LLM prompt injection."""
    lines = [f"TABLE: {TABLE_NAME}", "COLUMNS:"]
    for col, info in COLUMNS.items():
        lines.append(f"  - {col} ({info['type']}): {info['desc']}")

    lines.append("")
    lines.append("CATEGORICAL VALUES:")
    lines.append("  - gender: 'Male', 'Female', 'Other'")
    lines.append("  - city_tier: 'Tier 1', 'Tier 2', 'Tier 3'")
    lines.append("  - shopping_preference: 'Online', 'Store', 'Hybrid'")
    lines.append("")
    lines.append(f"TOTAL ROWS: ~11,790")

    return "\n".join(lines)


def get_column_names() -> list[str]:
    """Return ordered list of column names."""
    return list(COLUMNS.keys())
