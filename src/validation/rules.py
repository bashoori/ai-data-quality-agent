"""
Data quality rules for the AI Data Quality Agent.

This module defines the business rules that the validation layer will
apply to the customers dataset.

The rules are deterministic. The AI Agent will interpret validation
results later; it will not decide whether these core rules pass or fail.
"""

ALLOWED_CITIES = {
    "Vancouver",
    "Burnaby",
    "Coquitlam",
    "Surrey",
    "Richmond",
    "Toronto",
    "Calgary",
    "Edmonton",
    "Victoria",
    "Seattle",
}


DATA_QUALITY_RULES = {
    "customer_id": {
        "required": True,
        "unique": True,
    },
    "name": {
        "required": True,
    },
    "email": {
        "required": True,
        "unique": True,
        "format": "email",
    },
    "age": {
        "required": True,
        "min": 18,
        "max": 100,
    },
    "city": {
        "required": True,
        "allowed_values": ALLOWED_CITIES,
    },
    "signup_date": {
        "required": True,
        "format": "YYYY-MM-DD",
    },
}


def get_rules() -> dict:
    """Return the complete set of data quality rules."""
    return DATA_QUALITY_RULES


if __name__ == "__main__":
    print("=== DATA QUALITY RULES ===")

    for column, rules in DATA_QUALITY_RULES.items():
        print(f"\n{column}")

        for rule, value in rules.items():
            if rule == "allowed_values":
                value = sorted(value)

            print(f"  {rule}: {value}")
