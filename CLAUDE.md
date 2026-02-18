# Code Quality Rules

## Required
- Type hints for all functions
- Docstrings in Google format
- Handle all errors (try/except)
- logging instead of print
- Tests for each new function

## Style
- Maximum line length: 100 characters
- Import sorting: isort
- Formatting: black
- Linter: ruff

## Security
- Never hardcode secrets
- Parameterized SQL queries
- Validate all input data