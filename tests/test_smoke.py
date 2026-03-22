"""Smoke tests: verify packages are importable after scaffolding."""


def test_kanboard_importable() -> None:
    """Kanboard SDK package should be importable."""
    import kanboard  # noqa: F401
    import kanboard_cli  # noqa: F401


def test_orchestration_importable() -> None:
    """Orchestration subpackage should be importable from kanboard.orchestration."""
    from kanboard.orchestration import (  # noqa: F401
        DependencyAnalyzer,
        LocalPortfolioStore,
        PortfolioManager,
    )


def test_orchestration_classes_not_on_client() -> None:
    """Orchestration classes must NOT be auto-attached to KanboardClient."""
    from kanboard.client import KanboardClient

    assert not hasattr(KanboardClient, "portfolio_manager"), (
        "PortfolioManager must not be wired into KanboardClient"
    )
    assert not hasattr(KanboardClient, "dependency_analyzer"), (
        "DependencyAnalyzer must not be wired into KanboardClient"
    )
    assert not hasattr(KanboardClient, "portfolio_store"), (
        "LocalPortfolioStore must not be wired into KanboardClient"
    )
