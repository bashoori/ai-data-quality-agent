"""
Deterministic validation engine for the AI Data Quality Agent.

This module applies the rules defined in rules.py to a pandas DataFrame.
It returns structured validation results that can later be consumed by
the AI Agent.

The validator does not use AI.
"""

from pathlib import Path
from typing import Any
import re

import pandas as pd

from .rules import get_rules


EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$"
)


def _missing_mask(series: pd.Series) -> pd.Series:
    """Return True for null or whitespace-only values."""
    return series.isna() | series.astype("string").str.strip().eq("").fillna(False)


def _validate_required(df: pd.DataFrame, column: str) -> dict[str, Any]:
    mask = _missing_mask(df[column])
    count = int(mask.sum())

    return {
        "rule": "required",
        "status": "FAIL" if count else "PASS",
        "invalid_count": count,
        "message": (
            f"{count} missing value(s) found."
            if count
            else "No missing values found."
        ),
    }


def _validate_unique(df: pd.DataFrame, column: str) -> dict[str, Any]:
    series = df[column]
    valid_values = series[~_missing_mask(series)]
    duplicate_mask = valid_values.duplicated(keep=False)
    duplicate_count = int(duplicate_mask.sum())

    return {
        "rule": "unique",
        "status": "FAIL" if duplicate_count else "PASS",
        "invalid_count": duplicate_count,
        "message": (
            f"{duplicate_count} record(s) contain duplicated values."
            if duplicate_count
            else "All non-missing values are unique."
        ),
    }


def _validate_email_format(df: pd.DataFrame, column: str) -> dict[str, Any]:
    series = df[column]
    non_missing = series[~_missing_mask(series)].astype("string").str.strip()

    invalid_mask = ~non_missing.str.match(EMAIL_PATTERN, na=False)
    invalid_count = int(invalid_mask.sum())

    return {
        "rule": "email_format",
        "status": "FAIL" if invalid_count else "PASS",
        "invalid_count": invalid_count,
        "message": (
            f"{invalid_count} invalid email address(es) found."
            if invalid_count
            else "All non-missing email addresses have a valid format."
        ),
    }


def _validate_range(
    df: pd.DataFrame,
    column: str,
    minimum: float,
    maximum: float,
) -> dict[str, Any]:
    numeric_values = pd.to_numeric(df[column], errors="coerce")
    missing_mask = _missing_mask(df[column])

    invalid_mask = (
        ~missing_mask
        & (numeric_values < minimum)
        | (~missing_mask & (numeric_values > maximum))
        | (~missing_mask & numeric_values.isna())
    )

    invalid_count = int(invalid_mask.sum())

    return {
        "rule": "range",
        "status": "FAIL" if invalid_count else "PASS",
        "invalid_count": invalid_count,
        "expected": f"{minimum} to {maximum}",
        "message": (
            f"{invalid_count} value(s) outside the allowed range "
            f"{minimum} to {maximum}."
            if invalid_count
            else f"All values are within the allowed range {minimum} to {maximum}."
        ),
    }


def _validate_allowed_values(
    df: pd.DataFrame,
    column: str,
    allowed_values: set[str],
) -> dict[str, Any]:
    series = df[column]
    missing_mask = _missing_mask(series)
    normalized = series.astype("string").str.strip()

    invalid_mask = ~missing_mask & ~normalized.isin(allowed_values)
    invalid_count = int(invalid_mask.sum())

    invalid_values = sorted(
        normalized[invalid_mask].dropna().unique().tolist()
    )

    return {
        "rule": "allowed_values",
        "status": "FAIL" if invalid_count else "PASS",
        "invalid_count": invalid_count,
        "invalid_values": invalid_values,
        "message": (
            f"{invalid_count} invalid value(s) found."
            if invalid_count
            else "All non-missing values are allowed."
        ),
    }


def _validate_date_format(
    df: pd.DataFrame,
    column: str,
) -> dict[str, Any]:
    series = df[column]
    missing_mask = _missing_mask(series)

    parsed_dates = pd.to_datetime(
        series,
        format="%Y-%m-%d",
        errors="coerce",
    )

    invalid_mask = ~missing_mask & parsed_dates.isna()
    invalid_count = int(invalid_mask.sum())

    return {
        "rule": "date_format",
        "status": "FAIL" if invalid_count else "PASS",
        "invalid_count": invalid_count,
        "expected": "YYYY-MM-DD",
        "message": (
            f"{invalid_count} invalid date value(s) found."
            if invalid_count
            else "All non-missing dates use the expected YYYY-MM-DD format."
        ),
    }


def validate_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    """
    Apply all configured data quality rules to a DataFrame.

    Returns a structured dictionary containing column-level validation
    results and an overall PASS/FAIL status.
    """
    rules = get_rules()

    results: dict[str, Any] = {
        "overall_status": "PASS",
        "total_failed_rules": 0,
        "columns": {},
    }

    for column, column_rules in rules.items():
        if column not in df.columns:
            results["columns"][column] = {
                "status": "FAIL",
                "rules": [{
                    "rule": "column_exists",
                    "status": "FAIL",
                    "invalid_count": 1,
                    "message": f"Required column '{column}' is missing.",
                }],
            }
            results["overall_status"] = "FAIL"
            results["total_failed_rules"] += 1
            continue

        column_results = {
            "status": "PASS",
            "rules": [],
        }

        if column_rules.get("required"):
            column_results["rules"].append(
                _validate_required(df, column)
            )

        if column_rules.get("unique"):
            column_results["rules"].append(
                _validate_unique(df, column)
            )

        if column_rules.get("format") == "email":
            column_results["rules"].append(
                _validate_email_format(df, column)
            )

        if "min" in column_rules and "max" in column_rules:
            column_results["rules"].append(
                _validate_range(
                    df,
                    column,
                    column_rules["min"],
                    column_rules["max"],
                )
            )

        if "allowed_values" in column_rules:
            column_results["rules"].append(
                _validate_allowed_values(
                    df,
                    column,
                    column_rules["allowed_values"],
                )
            )

        if column_rules.get("format") == "YYYY-MM-DD":
            column_results["rules"].append(
                _validate_date_format(df, column)
            )

        failed_rules = [
            rule for rule in column_results["rules"]
            if rule["status"] == "FAIL"
        ]

        if failed_rules:
            column_results["status"] = "FAIL"
            results["overall_status"] = "FAIL"
            results["total_failed_rules"] += len(failed_rules)

        results["columns"][column] = column_results

    return results


def print_validation_results(results: dict[str, Any]) -> None:
    """Print validation results in a human-readable format."""
    print("\n=== DATA QUALITY VALIDATION ===")
    print(f"Overall status: {results['overall_status']}")
    print(f"Failed rules: {results['total_failed_rules']}")

    for column, column_result in results["columns"].items():
        print(f"\n{column}")

        for rule in column_result["rules"]:
            status_icon = "✓" if rule["status"] == "PASS" else "✗"
            print(
                f"  {status_icon} {rule['rule']}: "
                f"{rule['status']} - {rule['message']}"
            )

            if rule.get("invalid_values"):
                print(f"    Invalid values: {rule['invalid_values']}")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    dataset_path = project_root / "data" / "raw" / "customers.csv"

    df = pd.read_csv(dataset_path)
    validation_results = validate_dataframe(df)
    print_validation_results(validation_results)
