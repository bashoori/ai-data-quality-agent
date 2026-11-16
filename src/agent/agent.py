"""
AI Data Quality Agent.

The deterministic pipeline creates quality_report.json.
This module sends that structured report to an LLM for interpretation.

The AI does not decide whether a deterministic quality rule passed or failed.
It explains the findings, prioritizes them, and recommends next actions.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


SYSTEM_INSTRUCTIONS = """
You are an AI Data Quality Analyst.

You receive a deterministic data quality report produced by Python.
Do not invent validation results and do not change the reported counts.

Your job is to:
1. Explain the most important data quality problems.
2. Prioritize issues by business impact.
3. Explain why each important issue matters.
4. Recommend practical remediation actions.
5. Identify patterns that may indicate a root cause.
6. End with a short recommended action plan.

Use clear language suitable for a data engineer or data quality team.

Important:
- Treat the JSON report as the source of truth.
- Distinguish observed facts from hypotheses.
- Do not claim that data was fixed.
- Do not invent rows, values, or statistics that are not in the report.
"""


def load_quality_report(report_path: str | Path) -> dict:
    """Load the deterministic quality report."""
    report_path = Path(report_path)

    if not report_path.exists():
        raise FileNotFoundError(f"Quality report not found: {report_path}")

    with report_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def analyze_quality_report(
    report: dict,
    model: str | None = None,
) -> str:
    """Send the quality report to an LLM and return its analysis."""

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. "
            "Set it as an environment variable before running the agent."
        )

    client = OpenAI(api_key=api_key)

    selected_model = model or os.getenv("OPENAI_MODEL", "gpt-5.5")

    report_json = json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    )

    response = client.responses.create(
        model=selected_model,
        instructions=SYSTEM_INSTRUCTIONS,
        input=(
            "Analyze the following deterministic data quality report.\n\n"
            f"{report_json}"
        ),
    )

    return response.output_text


def save_analysis(
    analysis: str,
    output_path: str | Path,
) -> None:
    """Save the AI analysis as Markdown."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        file.write("# AI Data Quality Analysis\n\n")
        file.write(analysis.strip())
        file.write("\n")


def main() -> None:
    """Run the AI Data Quality Agent."""
    project_root = Path(__file__).resolve().parents[2]

    report_path = project_root / "reports" / "quality_report.json"
    output_path = project_root / "reports" / "ai_analysis.md"

    print("Loading quality report...")
    report = load_quality_report(report_path)

    print("Sending report to AI...")
    analysis = analyze_quality_report(report)

    save_analysis(analysis, output_path)

    print(f"AI analysis saved to: {output_path}")


if __name__ == "__main__":
    main()
