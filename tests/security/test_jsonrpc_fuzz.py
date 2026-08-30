"""JSON-RPC API security fuzzing tests.

Sends malicious payloads to a live Kanboard instance via Docker and asserts
that the server handles them safely — no 500s, no stack traces, no SQL errors
in responses, no information leakage.

Run with:
    pytest tests/security/test_jsonrpc_fuzz.py -v -m security
"""

from __future__ import annotations

import json
import re

import httpx
import pytest

import tests.security.payloads as _p
from tests.security.conftest import CORE_METHODS, KANBOARD_URL

pytestmark = [pytest.mark.security]

# Module-level payload aliases for concise parametrize decorators
_SQLI_STR = _p.SQLI_STRINGS
_SQLI_INT = _p.SQLI_INTEGERS
_XSS = _p.XSS_STRINGS
_PATH = _p.PATH_TRAVERSAL_STRINGS
_CMDI = _p.COMMAND_INJECTION_STRINGS
_FMTSTR = _p.FORMAT_STRING_PAYLOADS
_NULL = _p.NULL_BYTE_STRINGS
_UNICODE = _p.UNICODE_EDGE_CASES
_STR_ATTACKS = _p.string_attack_payloads()
_KNOWN_UPSTREAM_TYPE_WARNING = pytest.mark.xfail(
    strict=True,
    reason=(
        "Kanboard v1.2.54 exposes PHP array-to-string warnings for collection values; "
        "retain as a visible upstream finding until fixed"
    ),
)
_INT_ATTACKS = [
    pytest.param(payload, marks=_KNOWN_UPSTREAM_TYPE_WARNING)
    if isinstance(payload, (list, dict))
    else payload
    for payload in _p.integer_attack_payloads()
]
_NULL_UNICODE = _p.NULL_BYTE_STRINGS + _p.UNICODE_EDGE_CASES
_ENVELOPES = _p.malformed_envelopes()
_RAW_BODIES = _p.raw_malformed_bodies()

# ---------------------------------------------------------------------------
# Detection patterns — indicators of unsafe server behavior
# ---------------------------------------------------------------------------

_SQLI_LEAK_PATTERNS = re.compile(
    r"(sql\s*syntax|mysql_|pg_query|sqlite3?\.|ORA-\d|"
    r"SQLSTATE\[|Uncaught\s+PDOException|"
    r"You have an error in your SQL|"
    r"Warning:.*mysql_|"
    r"supplied argument is not a valid|"
    r"pg_exec|pg_query|"
    r"Microsoft OLE DB Provider|"
    r"JET Database Engine|"
    r"Unclosed quotation mark)",
    re.IGNORECASE,
)

_INFO_LEAK_PATTERNS = re.compile(
    r"(Fatal error:|PHP Warning:|PHP Notice:|PHP Parse error:|"
    r"Stack trace:|Traceback \(most recent|"
    r"<b>Warning</b>:|<b>Fatal error</b>:|"
    r"DocumentRoot|server at .* port|"
    r"/var/www/|/home/www-data/|"
    r"vendor/autoload\.php|"
    r"kanboard/app/|"
    r"X-Powered-By:\s*PHP)",
    re.IGNORECASE,
)


def _assert_safe_response(
    response: httpx.Response,
    context: str,
) -> None:
    """Assert a response shows no signs of unsafe server behavior.

    Checks for:
    - HTTP 500 Internal Server Error
    - SQL error messages in response body
    - PHP/framework stack traces or info leakage
    - Unreasonably large responses (potential data dump)
    """
    body = response.text

    assert response.status_code != 500, (
        f"HTTP 500 for {context}.\nBody (first 500 chars): {body[:500]}"
    )

    match = _SQLI_LEAK_PATTERNS.search(body)
    assert match is None, (
        f"SQL error leaked for {context}: '{match.group()}'\nBody (first 500 chars): {body[:500]}"
    )

    match = _INFO_LEAK_PATTERNS.search(body)
    assert match is None, (
        f"Info leak detected for {context}: '{match.group()}'\nBody (first 500 chars): {body[:500]}"
    )

    assert len(body) < 1_000_000, f"Suspiciously large response ({len(body)} bytes) for {context}"


def _send_rpc(
    client: httpx.Client,
    method: str,
    params: dict[str, object] | None = None,
    request_id: int = 1,
) -> httpx.Response:
    """Send a JSON-RPC request and return the raw response."""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "id": request_id,
        "params": params or {},
    }
    body = json.dumps(payload, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    return client.post(
        KANBOARD_URL,
        content=body.encode("ascii"),
        headers={"Content-Type": "application/json"},
    )


def _send_raw(client: httpx.Client, body: str) -> httpx.Response:
    """Send a raw HTTP POST body to the JSON-RPC endpoint."""
    return client.post(
        KANBOARD_URL,
        content=body.encode("utf-8", errors="replace"),
        headers={"Content-Type": "application/json"},
    )


def _cleanup_project(client: httpx.Client, resp: httpx.Response) -> None:
    """Remove a project created during fuzzing, if the response has an ID."""
    try:
        data = resp.json()
        pid = data.get("result")
        if isinstance(pid, int):
            _send_rpc(client, "removeProject", {"project_id": pid})
    except (ValueError, KeyError):
        pass


# ===================================================================
# 1. Protocol-level fuzzing
# ===================================================================


class TestProtocolFuzzing:
    """Test that malformed JSON-RPC envelopes are handled safely."""

    @pytest.mark.parametrize(
        "envelope",
        _ENVELOPES,
        ids=[f"envelope-{i}" for i in range(len(_ENVELOPES))],
    )
    def test_malformed_envelope(self, fuzz_http_client, envelope):
        resp = fuzz_http_client.post(KANBOARD_URL, json=envelope)
        ctx = f"malformed envelope: {json.dumps(envelope)[:100]}"
        _assert_safe_response(resp, ctx)

    @pytest.mark.parametrize(
        "body",
        _RAW_BODIES,
        ids=[f"raw-body-{i}" for i in range(len(_RAW_BODIES))],
    )
    def test_raw_malformed_body(self, fuzz_http_client, body):
        resp = _send_raw(fuzz_http_client, body)
        _assert_safe_response(resp, f"raw body: {body[:80]}")


class TestMethodInventory:
    """Ensure every SDK-exposed method receives protocol abuse coverage."""

    def test_sdk_method_inventory_is_complete(self, all_api_methods):
        """The method inventory cannot silently shrink below advertised coverage."""
        assert len(all_api_methods) >= 158
        assert len(all_api_methods) == len(set(all_api_methods))
        assert {method["name"] for method in CORE_METHODS} <= set(all_api_methods)

    def test_all_sdk_methods_handle_malformed_params_safely(
        self, fuzz_http_client, all_api_methods
    ):
        """Every SDK method safely rejects an unexpected adversarial parameter."""
        findings: list[str] = []
        for method_name in all_api_methods:
            resp = _send_rpc(
                fuzz_http_client,
                method_name,
                {"__unexpected_fuzz_parameter__": "' OR '1'='1' --"},
            )
            try:
                _assert_safe_response(resp, f"method-inventory:{method_name}")
            except AssertionError as exc:
                findings.append(str(exc))
        assert not findings, "Method inventory findings:\n" + "\n---\n".join(findings)


# ===================================================================
# 2. SQL Injection fuzzing
# ===================================================================


class TestSQLInjection:
    """Test SQL injection payloads against string and integer parameters."""

    @pytest.mark.parametrize(
        "payload",
        _SQLI_STR,
        ids=[f"sqli-str-{i}" for i in range(len(_SQLI_STR))],
    )
    def test_sqli_in_string_param(self, fuzz_http_client, payload):
        resp = _send_rpc(
            fuzz_http_client,
            "searchTasks",
            {
                "project_id": 1,
                "query": payload,
            },
        )
        _assert_safe_response(resp, f"searchTasks query={payload!r}")

    @pytest.mark.parametrize(
        "payload",
        _SQLI_STR,
        ids=[f"sqli-name-{i}" for i in range(len(_SQLI_STR))],
    )
    def test_sqli_in_project_name(self, fuzz_http_client, payload):
        resp = _send_rpc(
            fuzz_http_client,
            "getProjectByName",
            {
                "name": payload,
            },
        )
        _assert_safe_response(resp, f"getProjectByName name={payload!r}")

    @pytest.mark.parametrize(
        "payload",
        _SQLI_STR,
        ids=[f"sqli-user-{i}" for i in range(len(_SQLI_STR))],
    )
    def test_sqli_in_username_lookup(self, fuzz_http_client, payload):
        resp = _send_rpc(
            fuzz_http_client,
            "getUserByName",
            {
                "username": payload,
            },
        )
        _assert_safe_response(resp, f"getUserByName username={payload!r}")

    @pytest.mark.parametrize(
        "payload",
        _SQLI_INT,
        ids=[f"sqli-int-{i}" for i in range(len(_SQLI_INT))],
    )
    def test_sqli_in_integer_param(self, fuzz_http_client, payload):
        resp = _send_rpc(fuzz_http_client, "getTask", {"task_id": payload})
        _assert_safe_response(resp, f"getTask task_id={payload!r}")


# ===================================================================
# 3. XSS fuzzing (stored XSS via API)
# ===================================================================


class TestXSSInjection:
    """Test that XSS payloads in API inputs don't cause server errors.

    Note: stored XSS detection (i.e., the payload rendered unescaped in HTML)
    requires a browser-level test.  Here we verify the server handles
    the input without crashing or leaking info.
    """

    @pytest.mark.parametrize(
        "payload",
        _XSS,
        ids=[f"xss-{i}" for i in range(len(_XSS))],
    )
    def test_xss_in_project_creation(self, fuzz_http_client, payload):
        resp = _send_rpc(
            fuzz_http_client,
            "createProject",
            {
                "name": payload,
            },
        )
        _assert_safe_response(resp, f"createProject name={payload!r}")
        _cleanup_project(fuzz_http_client, resp)

    @pytest.mark.parametrize(
        "payload",
        _XSS,
        ids=[f"xss-task-{i}" for i in range(len(_XSS))],
    )
    def test_xss_in_task_title(self, fuzz_http_client, payload):
        create_resp = _send_rpc(
            fuzz_http_client,
            "createProject",
            {
                "name": f"fuzz-xss-{id(payload)}",
            },
        )
        project_id = None
        try:
            project_id = create_resp.json().get("result")
            if not isinstance(project_id, int):
                pytest.skip("Could not create project for XSS task test")
            resp = _send_rpc(
                fuzz_http_client,
                "createTask",
                {
                    "title": payload,
                    "project_id": project_id,
                },
            )
            _assert_safe_response(resp, f"createTask title={payload!r}")
        finally:
            if isinstance(project_id, int):
                _send_rpc(
                    fuzz_http_client,
                    "removeProject",
                    {"project_id": project_id},
                )


# ===================================================================
# 4. Path traversal
# ===================================================================


class TestPathTraversal:
    """Test path traversal payloads in string parameters."""

    @pytest.mark.parametrize(
        "payload",
        _PATH,
        ids=[f"path-{i}" for i in range(len(_PATH))],
    )
    def test_path_traversal_in_name(self, fuzz_http_client, payload):
        resp = _send_rpc(
            fuzz_http_client,
            "getProjectByName",
            {
                "name": payload,
            },
        )
        _assert_safe_response(resp, f"getProjectByName name={payload!r}")
        body = resp.text
        assert "root:" not in body, f"Possible LFI: /etc/passwd content in response for {payload!r}"


# ===================================================================
# 5. Command injection
# ===================================================================


class TestCommandInjection:
    """Test command injection payloads in string parameters."""

    @pytest.mark.parametrize(
        "payload",
        _CMDI,
        ids=[f"cmdi-{i}" for i in range(len(_CMDI))],
    )
    def test_command_injection_in_name(self, fuzz_http_client, payload):
        resp = _send_rpc(
            fuzz_http_client,
            "createProject",
            {
                "name": payload,
            },
        )
        _assert_safe_response(resp, f"createProject name={payload!r}")
        body = resp.text
        assert "uid=" not in body and "gid=" not in body, (
            f"Possible command injection: shell output for {payload!r}"
        )
        _cleanup_project(fuzz_http_client, resp)


# ===================================================================
# 6. Type confusion and boundary values
# ===================================================================


class TestTypeConfusion:
    """Test wrong-type and boundary-value payloads."""

    @pytest.mark.parametrize(
        "payload",
        _STR_ATTACKS,
        ids=[f"str-attack-{i}" for i in range(len(_STR_ATTACKS))],
    )
    def test_string_attacks_on_integer_param(self, fuzz_http_client, payload):
        resp = _send_rpc(
            fuzz_http_client,
            "getProjectById",
            {
                "project_id": payload,
            },
        )
        _assert_safe_response(resp, f"getProjectById project_id={payload!r}")

    @pytest.mark.parametrize(
        "payload",
        _INT_ATTACKS,
        ids=[f"int-attack-{i}" for i in range(len(_INT_ATTACKS))],
    )
    def test_integer_attacks_on_integer_param(self, fuzz_http_client, payload):
        resp = _send_rpc(fuzz_http_client, "getTask", {"task_id": payload})
        _assert_safe_response(resp, f"getTask task_id={payload!r}")

    @pytest.mark.parametrize(
        "payload",
        _INT_ATTACKS,
        ids=[f"int-str-{i}" for i in range(len(_INT_ATTACKS))],
    )
    def test_integer_attacks_on_string_param(self, fuzz_http_client, payload):
        resp = _send_rpc(
            fuzz_http_client,
            "getProjectByName",
            {
                "name": payload,
            },
        )
        _assert_safe_response(resp, f"getProjectByName name={payload!r}")


# ===================================================================
# 7. Null bytes and unicode edge cases
# ===================================================================


class TestNullBytesAndUnicode:
    """Test null byte injection and unicode edge cases."""

    @pytest.mark.parametrize(
        "payload",
        _NULL_UNICODE,
        ids=[f"nullunicode-{i}" for i in range(len(_NULL_UNICODE))],
    )
    def test_null_unicode_in_name(self, fuzz_http_client, payload):
        resp = _send_rpc(
            fuzz_http_client,
            "getProjectByName",
            {
                "name": payload,
            },
        )
        _assert_safe_response(resp, f"getProjectByName name={payload!r}")

    @pytest.mark.parametrize(
        "payload",
        _FMTSTR,
        ids=[f"fmtstr-{i}" for i in range(len(_FMTSTR))],
    )
    def test_format_strings(self, fuzz_http_client, payload):
        resp = _send_rpc(
            fuzz_http_client,
            "createProject",
            {
                "name": payload,
            },
        )
        _assert_safe_response(resp, f"createProject name={payload!r}")
        _cleanup_project(fuzz_http_client, resp)


# ===================================================================
# 8. Authentication boundary testing
# ===================================================================


class TestAuthBoundaries:
    """Test that unauthenticated and badly-authenticated requests fail."""

    def test_unauthenticated_read(self, unauthenticated_http_client):
        resp = unauthenticated_http_client.post(
            KANBOARD_URL,
            json={
                "jsonrpc": "2.0",
                "method": "getAllProjects",
                "id": 1,
                "params": {},
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "error" in data or data.get("result") is None, (
                "Unauthenticated request returned project data!"
            )
        else:
            assert resp.status_code in (401, 403)

    def test_unauthenticated_write(self, unauthenticated_http_client):
        resp = unauthenticated_http_client.post(
            KANBOARD_URL,
            json={
                "jsonrpc": "2.0",
                "method": "createProject",
                "id": 1,
                "params": {"name": "unauth-fuzz-test"},
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "error" in data or data.get("result") is False, (
                "Unauthenticated request created a project!"
            )
        else:
            assert resp.status_code in (401, 403)

    def test_bad_token_read(self, bad_token_http_client):
        resp = bad_token_http_client.post(
            KANBOARD_URL,
            json={
                "jsonrpc": "2.0",
                "method": "getAllProjects",
                "id": 1,
                "params": {},
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "error" in data or data.get("result") is None, (
                "Bad-token request returned project data!"
            )
        else:
            assert resp.status_code in (401, 403)

    def test_bad_token_write(self, bad_token_http_client):
        resp = bad_token_http_client.post(
            KANBOARD_URL,
            json={
                "jsonrpc": "2.0",
                "method": "removeProject",
                "id": 1,
                "params": {"project_id": 1},
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "error" in data or data.get("result") is False, (
                "Bad-token request deleted a project!"
            )
        else:
            assert resp.status_code in (401, 403)


# ===================================================================
# 9. Plugin method fuzzing (from api-schema.json)
# ===================================================================


class TestPluginMethodFuzz:
    """Fuzz all plugin API methods with attack payloads."""

    def test_plugin_methods_with_sqli(self, fuzz_http_client, plugin_methods):
        if not plugin_methods:
            pytest.skip("No plugin methods loaded from api-schema.json")

        findings: list[str] = []
        for method_def in plugin_methods:
            method_name = method_def["name"]
            params = method_def.get("params", [])
            if not params:
                continue

            fuzz_params: dict[str, object] = {}
            for p in params:
                if p["type"] == "string":
                    fuzz_params[p["name"]] = "' OR '1'='1' --"
                elif p["type"] == "integer":
                    fuzz_params[p["name"]] = "1 OR 1=1"
                elif p["type"] == "boolean":
                    fuzz_params[p["name"]] = True
                else:
                    fuzz_params[p["name"]] = "fuzz"

            resp = _send_rpc(fuzz_http_client, method_name, fuzz_params)
            try:
                _assert_safe_response(resp, f"plugin:{method_name} sqli")
            except AssertionError as e:
                findings.append(str(e))

        assert not findings, "Plugin SQLi findings:\n" + "\n---\n".join(findings)

    def test_plugin_methods_with_type_confusion(self, fuzz_http_client, plugin_methods):
        if not plugin_methods:
            pytest.skip("No plugin methods loaded from api-schema.json")

        findings: list[str] = []
        for method_def in plugin_methods:
            method_name = method_def["name"]
            params = method_def.get("params", [])
            if not params:
                continue

            fuzz_params: dict[str, object] = {}
            for p in params:
                if p["type"] == "string":
                    fuzz_params[p["name"]] = [1, 2, 3]
                elif p["type"] == "integer":
                    fuzz_params[p["name"]] = "not-an-int"
                elif p["type"] == "boolean":
                    fuzz_params[p["name"]] = "not-a-bool"
                else:
                    fuzz_params[p["name"]] = None

            resp = _send_rpc(fuzz_http_client, method_name, fuzz_params)
            try:
                _assert_safe_response(resp, f"plugin:{method_name} type_confusion")
            except AssertionError as e:
                findings.append(str(e))

        assert not findings, "Plugin type confusion findings:\n" + "\n---\n".join(findings)
