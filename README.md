# AI Data Quality Agent

An AI-powered data quality system that profiles datasets,
runs deterministic validation rules, identifies data quality
issues, and uses an AI agent to explain findings and recommend
next steps.

## Architecture

Data
 ↓
Profiling
 ↓
Validation
 ↓
AI Agent
 ↓
Quality Report

## Features

- Data profiling
- Missing value detection
- Duplicate detection
- Schema validation
- Data type validation
- Range validation
- AI-powered diagnosis
- Automated recommendations

## Tech Stack

Python
Pandas
OpenAI API
Pytest
GitHub

## Example

Input:
customers.csv

Output:

Overall Quality: WARNING

Issues:
- 127 missing values
- 32 duplicate records
- 18 invalid emails

## Roadmap

CSV → SQL → Fabric → Databricks → Automation



## Run

1- pip install -r requirements.txt

2- python -c "import pandas; print(pandas.__version__)"

3- python src/profiling/profiler.py

4- python src/validation/validators.py