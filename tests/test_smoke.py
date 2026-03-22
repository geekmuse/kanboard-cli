"""Smoke tests: verify packages are importable after scaffolding."""


def test_kanboard_importable() -> None:
    """Kanboard SDK package should be importable."""
    import kanboard  # noqa: F401
    import kanboard_cli  # noqa: F401
