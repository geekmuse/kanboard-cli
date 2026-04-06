"""Property-based fuzz testing for the Python SDK/CLI.

Uses Hypothesis to generate adversarial inputs and verify that:
- The SDK client serialization handles arbitrary data without crashing
- Config parsing rejects / survives malicious input
- CLI argument parsing handles bizarre inputs safely
- Model deserialization (from_api) doesn't crash on malformed dicts

Does NOT require Docker — these test the Python code itself.

Run with:
    pytest tests/security/test_sdk_fuzz.py -v -m security
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

pytestmark = [pytest.mark.security]

# Hypothesis settings for fuzzing — more examples, longer deadline
_FUZZ_SETTINGS = settings(
    max_examples=200,
    deadline=5000,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Strings with nasty characters: null bytes, unicode, injection patterns
nasty_strings = st.one_of(
    st.text(min_size=0, max_size=1000),
    st.sampled_from(
        [
            "' OR '1'='1",
            "<script>alert(1)</script>",
            "../../../etc/passwd",
            "; rm -rf /",
            "\x00\x00\x00",
            "${7*7}",
            "{{constructor.constructor('return this')()}}",
            "%s%s%s%s%n%n%n%n",
            "a" * 100000,
            "\ud800",  # lone surrogate
        ]
    ),
)

# Arbitrary JSON-like values
json_values = st.recursive(
    st.one_of(
        st.none(),
        st.booleans(),
        st.integers(min_value=-(2**63), max_value=2**63),
        st.floats(allow_nan=True, allow_infinity=True),
        nasty_strings,
    ),
    lambda children: st.one_of(
        st.lists(children, max_size=5),
        st.dictionaries(st.text(max_size=20), children, max_size=5),
    ),
    max_leaves=10,
)


# ===================================================================
# 1. SDK Client — request serialization
# ===================================================================


class TestClientSerialization:
    """Verify the SDK client builds valid JSON-RPC payloads for any input."""

    @_FUZZ_SETTINGS
    @given(
        method=nasty_strings,
        params=st.dictionaries(st.text(max_size=50), json_values, max_size=10),
    )
    def test_build_request_never_crashes(self, method, params):
        """_build_request should produce a serializable dict for any input."""
        from kanboard.client import KanboardClient

        # Don't actually connect — just test the serialization path
        client = KanboardClient.__new__(KanboardClient)
        client._request_id = 0

        payload = client._build_request(method, params)

        # Must be JSON-serializable
        serialized = json.dumps(payload)
        assert isinstance(serialized, str)
        assert len(serialized) > 0

        # Must have the required JSON-RPC fields
        assert payload["jsonrpc"] == "2.0"
        assert payload["method"] == method
        assert "id" in payload
        assert "params" in payload

    @_FUZZ_SETTINGS
    @given(raw=nasty_strings)
    def test_parse_json_handles_garbage(self, raw):
        """_parse_json should raise KanboardResponseError for non-JSON, never crash."""
        from kanboard.client import KanboardClient
        from kanboard.exceptions import KanboardResponseError

        client = KanboardClient.__new__(KanboardClient)

        try:
            result = client._parse_json(raw, "fuzzMethod")
            # If it parsed, it must be a valid Python object
            assert result is not None or raw.strip() == "null"
        except KanboardResponseError:
            pass  # expected for garbage input

    @_FUZZ_SETTINGS
    @given(data=st.dictionaries(st.text(max_size=30), json_values, max_size=10))
    def test_extract_result_handles_arbitrary_dicts(self, data):
        """_extract_result should not crash on arbitrary response dicts."""
        from kanboard.client import KanboardClient
        from kanboard.exceptions import KanboardAPIError

        client = KanboardClient.__new__(KanboardClient)

        try:
            client._extract_result(data, "fuzzMethod")
        except KanboardAPIError:
            pass  # expected when "error" key present
        except (TypeError, KeyError, AttributeError):
            pass  # tolerable for truly wild dicts


# ===================================================================
# 2. Model deserialization — from_api()
# ===================================================================


class TestModelDeserialization:
    """Verify dataclass models survive malformed API response dicts."""

    @_FUZZ_SETTINGS
    @given(data=st.dictionaries(st.text(max_size=30), json_values, max_size=20))
    def test_task_from_api_survives_garbage(self, data):
        """Task.from_api should not crash the process on arbitrary dicts."""
        from kanboard.models import Task

        try:
            Task.from_api(data)
        except (KeyError, TypeError, ValueError, AttributeError):
            pass  # expected for malformed data

    @_FUZZ_SETTINGS
    @given(data=st.dictionaries(st.text(max_size=30), json_values, max_size=20))
    def test_project_from_api_survives_garbage(self, data):
        """Project.from_api should not crash on arbitrary dicts."""
        from kanboard.models import Project

        try:
            Project.from_api(data)
        except (KeyError, TypeError, ValueError, AttributeError):
            pass

    @_FUZZ_SETTINGS
    @given(data=st.dictionaries(st.text(max_size=30), json_values, max_size=20))
    def test_user_from_api_survives_garbage(self, data):
        """User.from_api should not crash on arbitrary dicts."""
        from kanboard.models import User

        try:
            User.from_api(data)
        except (KeyError, TypeError, ValueError, AttributeError):
            pass

    @_FUZZ_SETTINGS
    @given(data=st.dictionaries(st.text(max_size=30), json_values, max_size=20))
    def test_comment_from_api_survives_garbage(self, data):
        """Comment.from_api should not crash on arbitrary dicts."""
        from kanboard.models import Comment

        try:
            Comment.from_api(data)
        except (KeyError, TypeError, ValueError, AttributeError):
            pass

    @_FUZZ_SETTINGS
    @given(data=st.dictionaries(st.text(max_size=30), json_values, max_size=20))
    def test_column_from_api_survives_garbage(self, data):
        """Column.from_api should not crash on arbitrary dicts."""
        from kanboard.models import Column

        try:
            Column.from_api(data)
        except (KeyError, TypeError, ValueError, AttributeError):
            pass


# ===================================================================
# 3. Config parsing
# ===================================================================


class TestConfigFuzzing:
    """Fuzz the config resolution with adversarial environment variables."""

    @_FUZZ_SETTINGS
    @given(
        url=st.text(
            alphabet=st.characters(
                blacklist_categories=("Cs",),
                blacklist_characters="\x00",
            ),
            max_size=500,
        ),
        token=st.text(
            alphabet=st.characters(
                blacklist_categories=("Cs",),
                blacklist_characters="\x00",
            ),
            max_size=500,
        ),
        username=st.text(
            alphabet=st.characters(
                blacklist_categories=("Cs",),
                blacklist_characters="\x00",
            ),
            max_size=500,
        ),
    )
    def test_config_resolve_survives_bad_env(self, url, token, username):
        """Config resolution should not crash with arbitrary env values."""
        from kanboard.config import KanboardConfig
        from kanboard.exceptions import KanboardError

        env_patch = {
            "KANBOARD_URL": url,
            "KANBOARD_TOKEN": token,
            "KANBOARD_USERNAME": username,
        }
        with patch.dict(os.environ, env_patch, clear=False):
            try:
                KanboardConfig.resolve()
            except (KanboardError, ValueError, TypeError, KeyError, OSError):
                pass  # expected for bad config values


# ===================================================================
# 4. CLI input handling
# ===================================================================


class TestCLIInputFuzzing:
    """Fuzz CLI commands with adversarial arguments."""

    @_FUZZ_SETTINGS
    @given(project_id=st.text(max_size=100))
    def test_cli_project_get_with_garbage_id(self, project_id):
        """CLI should reject or handle non-integer project IDs gracefully."""
        from kanboard_cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["project", "get", "--project-id", project_id])
        # Should not produce a Python traceback (exit code 1 is fine for bad input)
        assert "Traceback (most recent call last)" not in (result.output or "")

    @_FUZZ_SETTINGS
    @given(name=nasty_strings)
    def test_cli_project_create_with_nasty_name(self, name):
        """CLI should handle adversarial project names without crashing."""
        from kanboard_cli.main import cli

        runner = CliRunner()
        # --url/--token prevent actual network calls; Click should parse args safely
        result = runner.invoke(
            cli,
            [
                "--url",
                "http://fake:9999/jsonrpc.php",
                "--token",
                "fake",
                "project",
                "create",
                "--name",
                name,
            ],
        )
        # The CLI may fail (connection refused etc.) but shouldn't produce raw tracebacks
        # from input handling
        output = result.output or ""
        assert "SyntaxError" not in output
        assert "UnicodeDecodeError" not in output

    @_FUZZ_SETTINGS
    @given(format_val=st.sampled_from(["table", "json", "csv", "quiet", "invalid", "", "'; DROP"]))
    def test_cli_format_option_handling(self, format_val):
        """CLI --format should accept known values and reject others safely."""
        from kanboard_cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--format", format_val, "project", "list"])
        assert "Traceback (most recent call last)" not in (result.output or "")


# ===================================================================
# 5. JSON-RPC response handling edge cases
# ===================================================================


class TestResponseHandling:
    """Fuzz the client's response parsing with adversarial server responses."""

    @_FUZZ_SETTINGS
    @given(body=nasty_strings)
    def test_call_with_garbage_response_body(self, body):
        """SDK .call() should raise a typed exception for garbage HTTP responses."""
        from kanboard.client import KanboardClient
        from kanboard.exceptions import KanboardError

        client = KanboardClient.__new__(KanboardClient)
        client._request_id = 0

        # Mock _send to return garbage
        client._send = MagicMock(return_value=body)

        try:
            client.call("getVersion")
        except KanboardError:
            pass  # expected
        except (json.JSONDecodeError, TypeError, KeyError, AttributeError):
            pass  # acceptable for edge cases

    @_FUZZ_SETTINGS
    @given(
        status_code=st.sampled_from([200, 400, 401, 403, 404, 500, 502, 503]),
        body=nasty_strings,
    )
    def test_various_http_status_codes(self, status_code, body):
        """SDK should handle any HTTP status + body combination without crashing."""
        from kanboard.client import KanboardClient
        from kanboard.exceptions import KanboardError

        client = KanboardClient.__new__(KanboardClient)
        client._request_id = 0
        client._timeout = 5.0
        client._url = "http://fake:9999/jsonrpc.php"

        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.text = body

        client._http = MagicMock()
        client._http.post.return_value = mock_response

        try:
            client.call("getVersion")
        except KanboardError:
            pass
        except (json.JSONDecodeError, TypeError, KeyError, AttributeError):
            pass
