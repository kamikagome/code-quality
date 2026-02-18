#!/usr/bin/env python3
"""
Download JSON from an API, process the data, and save to CSV.

Usage:
    python fetch_to_csv.py
    python fetch_to_csv.py --url https://api.example.com/data --output results.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import urllib.error
import urllib.request
from typing import Any, Optional

logger = logging.getLogger(__name__)


def fetch_json(url: str, headers: Optional[dict[str, str]] = None) -> list[Any] | dict[str, Any]:
    """Fetch and parse JSON from an HTTP endpoint.

    Args:
        url: The HTTP(S) endpoint to retrieve.
        headers: Optional mapping of request headers.

    Returns:
        Parsed JSON payload as a list or dict.

    Raises:
        SystemExit: On HTTP errors, network errors, or invalid JSON.
    """
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode()
            logger.debug("Received %d bytes from %s", len(raw), url)
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        logger.error("HTTP error %s: %s", e.code, e.reason)
        sys.exit(1)
    except urllib.error.URLError as e:
        logger.error("Connection error: %s", e.reason)
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in response: %s", e)
        sys.exit(1)


def flatten(record: dict[str, Any], prefix: str = "", sep: str = ".") -> dict[str, Any]:
    """Recursively flatten a nested dict into dot-notation keys.

    Args:
        record: The dict to flatten.
        prefix: Key prefix accumulated during recursion.
        sep: Separator inserted between parent and child key segments.

    Returns:
        A flat dict with no nested dicts or lists as values.
    """
    out: dict[str, Any] = {}
    for key, value in record.items():
        full_key = f"{prefix}{sep}{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, full_key, sep))
        elif isinstance(value, list):
            # Join simple lists; serialize nested object lists as JSON
            if all(not isinstance(v, (dict, list)) for v in value):
                out[full_key] = ", ".join(str(v) for v in value)
            else:
                out[full_key] = json.dumps(value)
        else:
            out[full_key] = value
    return out


def to_rows(data: list[Any] | dict[str, Any]) -> list[dict[str, Any]]:
    """Normalise a JSON payload into a flat list of row dicts.

    Args:
        data: A JSON list or a single JSON object.

    Returns:
        A list of flat dicts suitable for CSV writing.
    """
    records = data if isinstance(data, list) else [data]
    return [flatten(r) if isinstance(r, dict) else {"value": r} for r in records]


def write_csv(rows: list[dict[str, Any]], output_path: str) -> None:
    """Write a list of flat dicts to a CSV file.

    Column names are the union of all keys across all rows, preserving
    insertion order.

    Args:
        rows: Non-empty list of flat dicts to write.
        output_path: Destination file path.

    Raises:
        SystemExit: If *rows* is empty or the file cannot be written.
    """
    if not rows:
        logger.error("No data to write.")
        sys.exit(1)

    fieldnames = list(dict.fromkeys(k for row in rows for k in row))

    try:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    except OSError as e:
        logger.error("Could not write to %s: %s", output_path, e)
        sys.exit(1)

    logger.info("Wrote %d rows to %s", len(rows), output_path)


def extract_nested(
    data: list[Any] | dict[str, Any], key_path: str
) -> list[Any] | dict[str, Any]:
    """Drill into a JSON structure using a dot-separated key path.

    Args:
        data: The parsed JSON response.
        key_path: Dot-separated path to the target value, e.g. ``"data.results"``.

    Returns:
        The value found at *key_path*.

    Raises:
        SystemExit: If any path segment is missing or its parent is not a dict.
    """
    for part in key_path.split("."):
        if not isinstance(data, dict) or part not in data:
            logger.error("Key '%s' not found in response.", part)
            sys.exit(1)
        data = data[part]
    return data


def main() -> None:
    """Parse CLI arguments, fetch JSON from the API, and save to CSV."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default="https://jsonplaceholder.typicode.com/users",
        help="API endpoint URL (default: JSONPlaceholder /users)",
    )
    parser.add_argument(
        "--output",
        default="output.csv",
        help="Output CSV file path (default: output.csv)",
    )
    parser.add_argument(
        "--header",
        action="append",
        metavar="Key:Value",
        help="Extra request header (repeatable), e.g. --header 'Authorization:Bearer token'",
    )
    parser.add_argument(
        "--key",
        help="Dot-path to the target list in the JSON response, e.g. 'data.results'",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging.",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    headers: dict[str, str] = {}
    for h in args.header or []:
        k, _, v = h.partition(":")
        headers[k.strip()] = v.strip()

    logger.info("Fetching %s ...", args.url)
    data = fetch_json(args.url, headers)

    if args.key:
        data = extract_nested(data, args.key)

    rows = to_rows(data)
    write_csv(rows, args.output)


if __name__ == "__main__":
    main()
