"""Tests for fetch_to_csv."""

from __future__ import annotations

import csv
import json
import os
import tempfile
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from fetch_to_csv import extract_nested, fetch_json, flatten, to_rows, write_csv


class TestFlatten(unittest.TestCase):
    def test_flat_dict_unchanged(self) -> None:
        assert flatten({"a": 1, "b": 2}) == {"a": 1, "b": 2}

    def test_nested_dict(self) -> None:
        assert flatten({"a": {"b": {"c": 3}}}) == {"a.b.c": 3}

    def test_simple_list_joined(self) -> None:
        assert flatten({"tags": ["x", "y", "z"]})["tags"] == "x, y, z"

    def test_nested_list_serialised_as_json(self) -> None:
        nested = [{"id": 1}, {"id": 2}]
        assert flatten({"items": nested})["items"] == json.dumps(nested)

    def test_custom_separator(self) -> None:
        assert "a_b" in flatten({"a": {"b": 1}}, sep="_")

    def test_empty_dict(self) -> None:
        assert flatten({}) == {}

    def test_prefix_applied(self) -> None:
        assert flatten({"b": 1}, prefix="a") == {"a.b": 1}


class TestToRows(unittest.TestCase):
    def test_list_input_preserves_length(self) -> None:
        rows = to_rows([{"id": 1}, {"id": 2}])
        assert len(rows) == 2

    def test_single_dict_wrapped_in_list(self) -> None:
        assert to_rows({"id": 1}) == [{"id": 1}]

    def test_non_dict_items_wrapped_with_value_key(self) -> None:
        assert to_rows([42, "hello"]) == [{"value": 42}, {"value": "hello"}]

    def test_nested_records_are_flattened(self) -> None:
        assert to_rows([{"a": {"b": 1}}]) == [{"a.b": 1}]


class TestWriteCsv(unittest.TestCase):
    def _write_and_read(self, rows: list[dict]) -> list[dict]:
        with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=False) as f:
            path = f.name
        try:
            write_csv(rows, path)
            with open(path, newline="", encoding="utf-8") as f:
                return list(csv.DictReader(f))
        finally:
            os.unlink(path)

    def test_writes_correct_number_of_rows(self) -> None:
        result = self._write_and_read([{"name": "Alice"}, {"name": "Bob"}])
        assert len(result) == 2

    def test_values_round_trip(self) -> None:
        result = self._write_and_read([{"name": "Alice", "age": 30}])
        assert result[0]["name"] == "Alice"
        assert result[0]["age"] == "30"

    def test_union_of_keys_across_rows(self) -> None:
        with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=False) as f:
            path = f.name
        try:
            write_csv([{"a": 1}, {"b": 2}], path)
            with open(path, newline="", encoding="utf-8") as f:
                fieldnames = f.readline().strip().split(",")
            assert set(fieldnames) == {"a", "b"}
        finally:
            os.unlink(path)

    def test_empty_rows_raises_system_exit(self) -> None:
        with self.assertRaises(SystemExit):
            write_csv([], "irrelevant.csv")

    def test_unwritable_path_raises_system_exit(self) -> None:
        with self.assertRaises(SystemExit):
            write_csv([{"a": 1}], "/no/such/directory/file.csv")


class TestExtractNested(unittest.TestCase):
    def test_single_key(self) -> None:
        assert extract_nested({"results": [1, 2, 3]}, "results") == [1, 2, 3]

    def test_dotted_path(self) -> None:
        assert extract_nested({"data": {"results": [1, 2]}}, "data.results") == [1, 2]

    def test_missing_key_raises_system_exit(self) -> None:
        with self.assertRaises(SystemExit):
            extract_nested({"a": 1}, "b")

    def test_non_dict_intermediate_raises_system_exit(self) -> None:
        with self.assertRaises(SystemExit):
            extract_nested({"a": [1, 2]}, "a.b")


class TestFetchJson(unittest.TestCase):
    def _mock_response(self, payload: object) -> MagicMock:
        mock = MagicMock()
        mock.read.return_value = json.dumps(payload).encode()
        mock.__enter__ = lambda s: s
        mock.__exit__ = MagicMock(return_value=False)
        return mock

    @patch("urllib.request.urlopen")
    def test_returns_parsed_json(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = self._mock_response([{"id": 1}])
        assert fetch_json("http://example.com/api") == [{"id": 1}]

    @patch("urllib.request.urlopen")
    def test_passes_custom_headers(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = self._mock_response({})
        fetch_json("http://example.com/api", headers={"X-Token": "abc"})
        req = mock_urlopen.call_args[0][0]
        assert req.get_header("X-token") == "abc"

    @patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.HTTPError(
            url=None, code=404, msg="Not Found", hdrs=None, fp=None
        ),
    )
    def test_http_error_raises_system_exit(self, _: MagicMock) -> None:
        with self.assertRaises(SystemExit):
            fetch_json("http://example.com/missing")

    @patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout"))
    def test_url_error_raises_system_exit(self, _: MagicMock) -> None:
        with self.assertRaises(SystemExit):
            fetch_json("http://unreachable.invalid/")

    @patch("urllib.request.urlopen")
    def test_invalid_json_raises_system_exit(self, mock_urlopen: MagicMock) -> None:
        mock = MagicMock()
        mock.read.return_value = b"not json {"
        mock.__enter__ = lambda s: s
        mock.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock
        with self.assertRaises(SystemExit):
            fetch_json("http://example.com/api")


if __name__ == "__main__":
    unittest.main()
