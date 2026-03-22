"""Unit tests for the Kanboard exception hierarchy."""

import pytest

from kanboard import (
    KanboardAPIError,
    KanboardAuthError,
    KanboardConfigError,
    KanboardConnectionError,
    KanboardError,
    KanboardNotFoundError,
    KanboardResponseError,
    KanboardValidationError,
)

# ---------------------------------------------------------------------------
# KanboardError (base)
# ---------------------------------------------------------------------------


class TestKanboardError:
    def test_is_exception(self):
        err = KanboardError("something went wrong")
        assert isinstance(err, Exception)

    def test_message_attribute(self):
        err = KanboardError("base error")
        assert err.message == "base error"

    def test_str(self):
        err = KanboardError("base error")
        assert str(err) == "base error"

    def test_raise_and_catch(self):
        with pytest.raises(KanboardError, match="base error"):
            raise KanboardError("base error")


# ---------------------------------------------------------------------------
# KanboardConfigError
# ---------------------------------------------------------------------------


class TestKanboardConfigError:
    def test_subclass_of_kanboard_error(self):
        err = KanboardConfigError("missing url")
        assert isinstance(err, KanboardError)

    def test_message_only(self):
        err = KanboardConfigError("missing url")
        assert err.message == "missing url"
        assert err.field is None
        assert str(err) == "Configuration error: missing url"

    def test_with_field(self):
        err = KanboardConfigError("must not be empty", field="url")
        assert err.field == "url"
        assert str(err) == "Configuration error for field 'url': must not be empty"

    def test_raise_and_catch_as_base(self):
        with pytest.raises(KanboardError):
            raise KanboardConfigError("bad field")


# ---------------------------------------------------------------------------
# KanboardConnectionError
# ---------------------------------------------------------------------------


class TestKanboardConnectionError:
    def test_subclass_of_kanboard_error(self):
        err = KanboardConnectionError("timeout")
        assert isinstance(err, KanboardError)

    def test_message_only(self):
        err = KanboardConnectionError("timeout")
        assert str(err) == "Connection error: timeout"

    def test_with_url(self):
        err = KanboardConnectionError("refused", url="http://localhost")
        assert err.url == "http://localhost"
        assert "URL: http://localhost" in str(err)

    def test_with_cause(self):
        root = OSError("connection refused")
        err = KanboardConnectionError("failed", cause=root)
        assert err.cause is root
        assert "Caused by:" in str(err)

    def test_with_all_attrs(self):
        root = TimeoutError("timed out")
        err = KanboardConnectionError("timeout", url="http://kb.example.com", cause=root)
        text = str(err)
        assert "Connection error: timeout" in text
        assert "URL: http://kb.example.com" in text
        assert "Caused by:" in text

    def test_raise_and_catch_as_base(self):
        with pytest.raises(KanboardError):
            raise KanboardConnectionError("no route")


# ---------------------------------------------------------------------------
# KanboardAuthError
# ---------------------------------------------------------------------------


class TestKanboardAuthError:
    def test_subclass_of_kanboard_error(self):
        err = KanboardAuthError("unauthorised")
        assert isinstance(err, KanboardError)

    def test_message_only(self):
        err = KanboardAuthError("unauthorised")
        assert err.http_status is None
        assert str(err) == "Authentication error: unauthorised"

    def test_with_http_status(self):
        err = KanboardAuthError("forbidden", http_status=403)
        assert err.http_status == 403
        assert str(err) == "Authentication error (HTTP 403): forbidden"

    def test_401_status(self):
        err = KanboardAuthError("invalid token", http_status=401)
        assert "HTTP 401" in str(err)

    def test_raise_and_catch_as_base(self):
        with pytest.raises(KanboardError):
            raise KanboardAuthError("bad creds")


# ---------------------------------------------------------------------------
# KanboardAPIError
# ---------------------------------------------------------------------------


class TestKanboardAPIError:
    def test_subclass_of_kanboard_error(self):
        err = KanboardAPIError("api failed")
        assert isinstance(err, KanboardError)

    def test_message_only(self):
        err = KanboardAPIError("api failed")
        assert err.method is None
        assert err.code is None
        assert str(err) == "API error: api failed"

    def test_with_method(self):
        err = KanboardAPIError("bad call", method="createTask")
        assert err.method == "createTask"
        assert "method='createTask'" in str(err)

    def test_with_code(self):
        err = KanboardAPIError("unknown error", code=-32600)
        assert err.code == -32600
        assert "code=-32600" in str(err)

    def test_with_all_attrs(self):
        err = KanboardAPIError("parse error", method="getTask", code=-32700)
        text = str(err)
        assert "API error: parse error" in text
        assert "method='getTask'" in text
        assert "code=-32700" in text

    def test_raise_and_catch_as_base(self):
        with pytest.raises(KanboardError):
            raise KanboardAPIError("api issue")


# ---------------------------------------------------------------------------
# KanboardNotFoundError
# ---------------------------------------------------------------------------


class TestKanboardNotFoundError:
    def test_subclass_of_kanboard_api_error(self):
        err = KanboardNotFoundError("not found")
        assert isinstance(err, KanboardAPIError)
        assert isinstance(err, KanboardError)

    def test_message_only(self):
        err = KanboardNotFoundError("task not found")
        assert err.resource is None
        assert err.identifier is None
        assert str(err) == "Not found: task not found"

    def test_with_resource_only(self):
        err = KanboardNotFoundError("missing", resource="project")
        assert str(err) == "Not found: project does not exist"

    def test_with_resource_and_identifier(self):
        err = KanboardNotFoundError("missing", resource="task", identifier=42)
        assert err.resource == "task"
        assert err.identifier == 42
        assert str(err) == "Not found: task '42' does not exist"

    def test_with_string_identifier(self):
        err = KanboardNotFoundError("missing", resource="user", identifier="admin")
        assert str(err) == "Not found: user 'admin' does not exist"

    def test_method_and_code_passthrough(self):
        err = KanboardNotFoundError(
            "missing", resource="task", identifier=7, method="getTask", code=-32001
        )
        assert err.method == "getTask"
        assert err.code == -32001

    def test_raise_and_catch_as_api_error(self):
        with pytest.raises(KanboardAPIError):
            raise KanboardNotFoundError("gone")

    def test_raise_and_catch_as_base(self):
        with pytest.raises(KanboardError):
            raise KanboardNotFoundError("gone")


# ---------------------------------------------------------------------------
# KanboardValidationError
# ---------------------------------------------------------------------------


class TestKanboardValidationError:
    def test_subclass_of_kanboard_api_error(self):
        err = KanboardValidationError("invalid input")
        assert isinstance(err, KanboardAPIError)
        assert isinstance(err, KanboardError)

    def test_message_only(self):
        err = KanboardValidationError("title is required")
        assert str(err) == "Validation error: title is required"

    def test_with_method(self):
        err = KanboardValidationError("bad value", method="createTask")
        text = str(err)
        assert "Validation error:" in text
        assert "method='createTask'" in text

    def test_with_code(self):
        err = KanboardValidationError("invalid", code=-32602)
        assert "code=-32602" in str(err)

    def test_raise_and_catch_as_api_error(self):
        with pytest.raises(KanboardAPIError):
            raise KanboardValidationError("bad data")

    def test_raise_and_catch_as_base(self):
        with pytest.raises(KanboardError):
            raise KanboardValidationError("bad data")


# ---------------------------------------------------------------------------
# KanboardResponseError
# ---------------------------------------------------------------------------


class TestKanboardResponseError:
    def test_subclass_of_kanboard_error(self):
        err = KanboardResponseError("malformed")
        assert isinstance(err, KanboardError)

    def test_message_only(self):
        err = KanboardResponseError("malformed JSON")
        assert err.raw_body is None
        assert str(err) == "Response error: malformed JSON"

    def test_with_str_body(self):
        err = KanboardResponseError("bad body", raw_body="<html>not json</html>")
        assert err.raw_body == "<html>not json</html>"
        text = str(err)
        assert "Response error: bad body" in text
        assert "body:" in text

    def test_with_bytes_body(self):
        err = KanboardResponseError("binary response", raw_body=b"\xff\xfe")
        text = str(err)
        assert "Response error: binary response" in text
        assert "body:" in text

    def test_long_body_truncated(self):
        long_body = "x" * 200
        err = KanboardResponseError("too long", raw_body=long_body)
        text = str(err)
        # snippet is capped at 120 chars
        assert "x" * 120 in text
        assert "x" * 200 not in text

    def test_raise_and_catch_as_base(self):
        with pytest.raises(KanboardError):
            raise KanboardResponseError("bad response")


# ---------------------------------------------------------------------------
# Import surface — all exceptions importable from top-level kanboard package
# ---------------------------------------------------------------------------


class TestImportSurface:
    def test_all_importable_from_kanboard_package(self):
        import kanboard

        for name in [
            "KanboardError",
            "KanboardConfigError",
            "KanboardConnectionError",
            "KanboardAuthError",
            "KanboardAPIError",
            "KanboardNotFoundError",
            "KanboardValidationError",
            "KanboardResponseError",
        ]:
            assert hasattr(kanboard, name), f"{name} not found in kanboard package"
