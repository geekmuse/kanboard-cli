"""Typed exception hierarchy for the Kanboard SDK.

All SDK exceptions derive from :class:`KanboardError` so callers can catch
the entire family with a single ``except KanboardError`` clause while still
being able to handle fine-grained sub-classes when needed.
"""

from __future__ import annotations


class KanboardError(Exception):
    """Base class for all Kanboard SDK exceptions.

    Every SDK exception is a subclass of this class, allowing callers to
    catch the entire exception family with a single ``except KanboardError``.
    """

    def __init__(self, message: str) -> None:
        """Initialise with a human-readable message.

        Args:
            message: A human-readable description of the error.
        """
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        """Return a human-readable error message.

        Returns:
            The error message string.
        """
        return self.message


class KanboardConfigError(KanboardError):
    """Raised when the SDK configuration is invalid or incomplete.

    Attributes:
        message: A human-readable description of the configuration problem.
        field: The configuration field that is missing or invalid, if known.
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        """Initialise with a message and an optional field name.

        Args:
            message: A human-readable description of the configuration problem.
            field: The configuration field that is missing or invalid.
        """
        super().__init__(message)
        self.field = field

    def __str__(self) -> str:
        """Return a human-readable error message.

        Returns:
            A string that includes the field name when available.
        """
        if self.field:
            return f"Configuration error for field '{self.field}': {self.message}"
        return f"Configuration error: {self.message}"


class KanboardConnectionError(KanboardError):
    """Raised when the SDK cannot connect to the Kanboard server.

    Attributes:
        message: A human-readable description of the connection failure.
        url: The URL that was being contacted.
        cause: The underlying exception that triggered this error, if any.
    """

    def __init__(
        self,
        message: str,
        url: str | None = None,
        cause: BaseException | None = None,
    ) -> None:
        """Initialise with a message, optional URL, and optional root cause.

        Args:
            message: A human-readable description of the connection failure.
            url: The URL that was being contacted when the failure occurred.
            cause: The underlying exception that triggered this error.
        """
        super().__init__(message)
        self.url = url
        self.cause = cause

    def __str__(self) -> str:
        """Return a human-readable error message.

        Returns:
            A string including the URL and cause when available.
        """
        parts = [f"Connection error: {self.message}"]
        if self.url:
            parts.append(f"URL: {self.url}")
        if self.cause:
            parts.append(f"Caused by: {self.cause}")
        return " — ".join(parts)


class KanboardAuthError(KanboardError):
    """Raised when the Kanboard server rejects the credentials.

    Attributes:
        message: A human-readable description of the authentication failure.
        http_status: The HTTP status code returned by the server (e.g. 401, 403).
    """

    def __init__(self, message: str, http_status: int | None = None) -> None:
        """Initialise with a message and an optional HTTP status code.

        Args:
            message: A human-readable description of the authentication failure.
            http_status: The HTTP status code returned by the server.
        """
        super().__init__(message)
        self.http_status = http_status

    def __str__(self) -> str:
        """Return a human-readable error message.

        Returns:
            A string that includes the HTTP status code when available.
        """
        if self.http_status is not None:
            return f"Authentication error (HTTP {self.http_status}): {self.message}"
        return f"Authentication error: {self.message}"


class KanboardAPIError(KanboardError):
    """Raised when the Kanboard JSON-RPC API returns an error response.

    Attributes:
        message: A human-readable description of the API error.
        method: The JSON-RPC method that was called.
        code: The JSON-RPC error code returned by the server, if available.
    """

    def __init__(
        self,
        message: str,
        method: str | None = None,
        code: int | None = None,
    ) -> None:
        """Initialise with a message, optional method name, and optional error code.

        Args:
            message: A human-readable description of the API error.
            method: The JSON-RPC method name that was called.
            code: The JSON-RPC error code returned by the server.
        """
        super().__init__(message)
        self.method = method
        self.code = code

    def __str__(self) -> str:
        """Return a human-readable error message.

        Returns:
            A string that includes the method name and error code when available.
        """
        parts = [f"API error: {self.message}"]
        if self.method:
            parts.append(f"method='{self.method}'")
        if self.code is not None:
            parts.append(f"code={self.code}")
        return " ".join(parts)


class KanboardNotFoundError(KanboardAPIError):
    """Raised when a requested Kanboard resource does not exist.

    This is a specialisation of :class:`KanboardAPIError` for 404-style
    situations where a resource lookup returns ``None`` or ``false``.

    Attributes:
        resource: The type of resource that was not found (e.g. ``'task'``).
        identifier: The identifier used in the lookup (e.g. a task ID).
    """

    def __init__(
        self,
        message: str,
        resource: str | None = None,
        identifier: str | int | None = None,
        method: str | None = None,
        code: int | None = None,
    ) -> None:
        """Initialise with message, optional resource type, and optional identifier.

        Args:
            message: A human-readable description of the not-found error.
            resource: The type of resource that was not found.
            identifier: The identifier used in the lookup.
            method: The JSON-RPC method name that was called.
            code: The JSON-RPC error code returned by the server.
        """
        super().__init__(message, method=method, code=code)
        self.resource = resource
        self.identifier = identifier

    def __str__(self) -> str:
        """Return a human-readable error message.

        Returns:
            A string that includes the resource type and identifier when available.
        """
        if self.resource and self.identifier is not None:
            return f"Not found: {self.resource} '{self.identifier}' does not exist"
        if self.resource:
            return f"Not found: {self.resource} does not exist"
        return f"Not found: {self.message}"


class KanboardValidationError(KanboardAPIError):
    """Raised when the Kanboard API rejects a request due to invalid input.

    This is a specialisation of :class:`KanboardAPIError` for validation
    failures returned by the Kanboard server.
    """

    def __str__(self) -> str:
        """Return a human-readable validation error message.

        Returns:
            A string prefixed with 'Validation error'.
        """
        parts = [f"Validation error: {self.message}"]
        if self.method:
            parts.append(f"method='{self.method}'")
        if self.code is not None:
            parts.append(f"code={self.code}")
        return " ".join(parts)


class KanboardResponseError(KanboardError):
    """Raised when the Kanboard server returns a malformed or unexpected response.

    Attributes:
        message: A human-readable description of the response problem.
        raw_body: The raw response body that could not be parsed.
    """

    def __init__(self, message: str, raw_body: str | bytes | None = None) -> None:
        """Initialise with a message and the raw response body.

        Args:
            message: A human-readable description of the response problem.
            raw_body: The raw response body that could not be parsed.
        """
        super().__init__(message)
        self.raw_body = raw_body

    def __str__(self) -> str:
        """Return a human-readable error message.

        Returns:
            A string that includes a snippet of the raw body when available.
        """
        if self.raw_body is not None:
            snippet = (
                self.raw_body[:120]
                if isinstance(self.raw_body, str)
                else self.raw_body[:120].decode("utf-8", errors="replace")
            )
            return f"Response error: {self.message} — body: {snippet!r}"
        return f"Response error: {self.message}"
