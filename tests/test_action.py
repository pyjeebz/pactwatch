"""Tests for the GitHub Action entrypoint."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from pactwatch.action import _get_pr_number, get_input

GRAPH_FIXTURES = Path(__file__).parent / "fixtures" / "graph"


class TestGetInput:
    def test_reads_from_environment(self):
        with patch.dict(os.environ, {"INPUT_CONFIG": "/path/to/config.yaml"}):
            assert get_input("config") == "/path/to/config.yaml"

    def test_hyphenated_names(self):
        with patch.dict(os.environ, {"INPUT_OLD_SPEC": "/path/to/old.yaml"}):
            assert get_input("old-spec") == "/path/to/old.yaml"

    def test_strips_whitespace(self):
        with patch.dict(os.environ, {"INPUT_PRODUCER": "  api  "}):
            assert get_input("producer") == "api"

    def test_exits_on_missing_required(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                get_input("config")
            assert exc_info.value.code == 2

    def test_returns_empty_for_optional(self):
        with patch.dict(os.environ, {}, clear=True):
            result = get_input("optional-input", required=False)
            assert result == ""


class TestGetPrNumber:
    def test_reads_from_event_payload(self):
        event = {"pull_request": {"number": 42}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(event, f)
            f.flush()
            with patch.dict(os.environ, {"GITHUB_EVENT_PATH": f.name}):
                assert _get_pr_number() == 42
        os.unlink(f.name)

    def test_returns_none_without_event_path(self):
        with patch.dict(os.environ, {}, clear=True):
            assert _get_pr_number() is None

    def test_returns_none_for_bad_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json")
            f.flush()
            with patch.dict(os.environ, {"GITHUB_EVENT_PATH": f.name}):
                assert _get_pr_number() is None
        os.unlink(f.name)
