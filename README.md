# fetch-to-csv

Download JSON from any REST API and save it as a flat CSV — no external dependencies.

> Learning project built with [Claude Code](https://github.com/anthropics/claude-code), focused on code quality: type hints, Google-style docstrings, structured logging, error handling, and full test coverage.

## Features

- Fetches JSON via HTTP/HTTPS with optional custom headers
- Recursively flattens nested objects into dot-notation columns (`address.city`, `company.name`)
- Serialises complex list fields as JSON strings; joins simple lists with `, `
- Drills into nested responses via a dot-path key (`--key data.results`)
- Structured logging with optional `--verbose` debug output
- Zero runtime dependencies — pure Python stdlib

## Requirements

Python 3.9+

## Usage

```bash
# Default: fetch JSONPlaceholder /users → output.csv
python fetch_to_csv.py

# Custom endpoint and output file
python fetch_to_csv.py --url https://api.example.com/items --output items.csv

# Authenticated endpoint
python fetch_to_csv.py --url https://api.example.com/data \
  --header "Authorization:Bearer YOUR_TOKEN"

# Response is nested: { "data": { "results": [...] } }
python fetch_to_csv.py --url https://api.example.com/data --key data.results

# Debug logging
python fetch_to_csv.py --verbose
```

## Options

| Flag | Default | Description |
|---|---|---|
| `--url` | JSONPlaceholder `/users` | API endpoint to fetch |
| `--output` | `output.csv` | Output CSV file path |
| `--header Key:Value` | — | Request header (repeatable) |
| `--key` | — | Dot-path into the JSON response |
| `--verbose / -v` | — | Enable debug logging |

## Example output

Given a response like:
```json
[{"id": 1, "name": "Alice", "address": {"city": "Berlin"}}]
```

The CSV will contain:
```
id,name,address.city
1,Alice,Berlin
```

## Running tests

```bash
python -m pytest test_fetch_to_csv.py -v
```

25 tests, no network calls required (all HTTP interactions are mocked).

## License

MIT
