"""
Data profiling module for the AI Data Quality Agent.

This module performs deterministic profiling of a CSV dataset.
It does not use AI. The AI Agent will consume these profiling results
later to explain issues and recommend actions.
"""

from pathlib import Path
from typing import Any

import pandas as pd


def profile_dataset(file_path: str | Path) -> dict[str, Any]:
    """
    Profile a CSV dataset and return structured quality metrics.

    Parameters
    ----------
    file_path:
        Path to the CSV file.

    Returns
    -------
    dict
        Dataset-level and column-level profiling results.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Dataset not found: {file_path}")

    if file_path.suffix.lower() != ".csv":
        raise ValueError("profile_dataset currently supports CSV files only.")

    df = pd.read_csv(file_path)

    profile: dict[str, Any] = {
        "file_name": file_path.name,
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "duplicate_row_count": int(df.duplicated().sum()),
        "columns": {},
    }

    for column in df.columns:
        series = df[column]

        missing_count = int(series.isna().sum())
        blank_count = int(
            series.astype("string").str.strip().eq("").fillna(False).sum()
        )

        column_profile: dict[str, Any] = {
            "data_type": str(series.dtype),
            "missing_count": missing_count,
            "missing_percentage": round(
                (missing_count / len(df)) * 100, 2
            ) if len(df) else 0.0,
            "blank_count": blank_count,
            "unique_count": int(series.nunique(dropna=True)),
            "duplicate_count": int(series.duplicated().sum()),
        }

        if pd.api.types.is_numeric_dtype(series):
            non_null = series.dropna()

            if len(non_null):
                column_profile["min"] = float(non_null.min())
                column_profile["max"] = float(non_null.max())
                column_profile["mean"] = round(float(non_null.mean()), 2)

        profile["columns"][column] = column_profile

    return profile


def print_profile(profile: dict[str, Any]) -> None:
    """Print a human-readable summary of a dataset profile."""
    print("\n=== DATASET PROFILE ===")
    print(f"File: {profile['file_name']}")
    print(f"Rows: {profile['row_count']:,}")
    print(f"Columns: {profile['column_count']}")
    print(f"Duplicate rows: {profile['duplicate_row_count']:,}")

    print("\n=== COLUMN PROFILE ===")

    for column, metrics in profile["columns"].items():
        print(f"\n{column}")
        print(f"  Type: {metrics['data_type']}")
        print(f"  Missing: {metrics['missing_count']:,} ({metrics['missing_percentage']}%)")
        print(f"  Blank: {metrics['blank_count']:,}")
        print(f"  Unique: {metrics['unique_count']:,}")
        print(f"  Duplicate values: {metrics['duplicate_count']:,}")

        if "min" in metrics:
            print(f"  Min: {metrics['min']}")
            print(f"  Max: {metrics['max']}")
            print(f"  Mean: {metrics['mean']}")


if __name__ == "__main__":
    dataset_path = Path(__file__).resolve().parents[2] / "data" / "raw" / "customers.csv"

    result = profile_dataset(dataset_path)
    print_profile(result)
