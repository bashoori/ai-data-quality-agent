"""
Quality report generator for the AI Data Quality Agent.

This module combines dataset profiling and deterministic validation
results into one structured JSON report.

The report is designed to become the input for the AI Agent later.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.profiling.profiler import profile_dataset
from src.validation.validators import validate_dataframe


def calculate_severity(
    column: str,
    rule: str,
    invalid_count: int,
    total_rows: int,
) -> str:
    """Assign a simple, explainable severity level to a failed rule."""

    if invalid_count == 0:
        return "LOW"

    percentage = (invalid_count / total_rows) * 100 if total_rows else 0

    if column == "customer_id" and rule == "unique":
        return "CRITICAL"

    if column == "email" and rule in {"required", "unique", "email_format"}:
        return "HIGH"

    if column == "age" and rule == "range":
        return "HIGH" if percentage >= 0.1 else "MEDIUM"

    if column == "signup_date" and rule == "date_format":
        return "MEDIUM"

    if percentage >= 1:
        return "HIGH"

    return "MEDIUM"


def build_quality_report(
    dataset_path: str | Path,
) -> dict[str, Any]:
    """Build a complete structured quality report for a CSV dataset."""

    dataset_path = Path(dataset_path)

    profile = profile_dataset(dataset_path)
    df = pd.read_csv(dataset_path)
    validation = validate_dataframe(df)

    issues = []

    for column, column_result in validation["columns"].items():
        for rule_result in column_result["rules"]:
            if rule_result["status"] != "FAIL":
                continue

            invalid_count = int(rule_result.get("invalid_count", 0))

            issues.append({
                "column": column,
                "rule": rule_result["rule"],
                "severity": calculate_severity(
                    column,
                    rule_result["rule"],
                    invalid_count,
                    profile["row_count"],
                ),
                "invalid_count": invalid_count,
                "message": rule_result["message"],
            })

    severity_order = {
        "CRITICAL": 0,
        "HIGH": 1,
        "MEDIUM": 2,
        "LOW": 3,
    }

    issues.sort(
        key=lambda item: (
            severity_order.get(item["severity"], 99),
            -item["invalid_count"],
        )
    )

    severity_summary = {
        "CRITICAL": sum(
            1 for issue in issues if issue["severity"] == "CRITICAL"
        ),
        "HIGH": sum(
            1 for issue in issues if issue["severity"] == "HIGH"
        ),
        "MEDIUM": sum(
            1 for issue in issues if issue["severity"] == "MEDIUM"
        ),
        "LOW": sum(
            1 for issue in issues if issue["severity"] == "LOW"
        ),
    }

    report = {
        "report_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dataset": dataset_path.name,
            "row_count": profile["row_count"],
            "column_count": profile["column_count"],
        },
        "overall_status": validation["overall_status"],
        "validation_summary": {
            "failed_rules": validation["total_failed_rules"],
            "total_issues": len(issues),
            "severity_summary": severity_summary,
        },
        "profile_summary": {
            "duplicate_rows": profile["duplicate_row_count"],
            "columns": profile["columns"],
        },
        "issues": issues,
    }

    return report


def save_quality_report(
    report: dict[str, Any],
    output_path: str | Path,
) -> None:
    """Save a quality report as formatted JSON."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)


def print_report_summary(report: dict[str, Any]) -> None:
    """Print a concise report summary."""
    summary = report["validation_summary"]

    print("\n=== QUALITY REPORT ===")
    print(f"Dataset: {report['report_metadata']['dataset']}")
    print(f"Overall status: {report['overall_status']}")
    print(f"Failed rules: {summary['failed_rules']}")
    print(f"Total issues: {summary['total_issues']}")

    print("\n=== SEVERITY ===")
    for severity, count in summary["severity_summary"].items():
        print(f"{severity}: {count}")

    print("\n=== TOP ISSUES ===")

    for issue in report["issues"]:
        print(
            f"{issue['severity']}: "
            f"{issue['column']} -> {issue['rule']} "
            f"({issue['invalid_count']} records)"
        )


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]

    dataset_path = project_root / "data" / "raw" / "customers.csv"
    output_path = project_root / "reports" / "quality_report.json"

    quality_report = build_quality_report(dataset_path)
    save_quality_report(quality_report, output_path)
    print_report_summary(quality_report)

    print(f"\nReport saved to: {output_path}")
