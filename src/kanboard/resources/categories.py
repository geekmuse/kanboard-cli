"""Categories resource module — task category management for Kanboard."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Category

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class CategoriesResource:
    """Kanboard Categories API resource.

    Exposes all five category-related JSON-RPC methods as typed Python methods.
    Accessed via ``KanboardClient.categories``.

    Example:
        >>> categories = client.categories.get_all_categories(1)
        >>> for cat in categories:
        ...     print(cat.name)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def create_category(
        self,
        project_id: int,
        name: str,
        **kwargs: Any,
    ) -> int:
        """Create a new category for a project.

        Maps to the Kanboard ``createCategory`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project to add the category to.
            name: The display name for the new category.
            **kwargs: Optional keyword arguments forwarded to the API (e.g. ``color_id``).

        Returns:
            The integer ID of the newly created category.

        Raises:
            KanboardAPIError: The API returned ``False`` or ``0`` indicating creation failed.
        """
        result = self._client.call(
            "createCategory",
            project_id=project_id,
            name=name,
            **kwargs,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to create category '{name}' in project {project_id}",
                method="createCategory",
            )
        return int(result)

    def get_category(self, category_id: int) -> Category:
        """Fetch a single category by its ID.

        Maps to the Kanboard ``getCategory`` JSON-RPC method.

        Args:
            category_id: Unique integer ID of the category to fetch.

        Returns:
            A :class:`~kanboard.models.Category` instance.

        Raises:
            KanboardNotFoundError: The API returned ``None`` — category does not exist.
        """
        result = self._client.call("getCategory", category_id=category_id)
        if result is None:
            raise KanboardNotFoundError(
                f"Category {category_id} not found",
                resource="Category",
                identifier=category_id,
            )
        return Category.from_api(result)

    def get_all_categories(self, project_id: int) -> list[Category]:
        """Fetch all categories for a project.

        Maps to the Kanboard ``getAllCategories`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project whose categories to fetch.

        Returns:
            A list of :class:`~kanboard.models.Category` instances.  Returns an
            empty list when the API responds with a falsy value.
        """
        result = self._client.call("getAllCategories", project_id=project_id)
        if not result:
            return []
        return [Category.from_api(item) for item in result]

    def update_category(self, id: int, name: str, **kwargs: Any) -> bool:
        """Update an existing category's name and optional fields.

        Maps to the Kanboard ``updateCategory`` JSON-RPC method.

        Args:
            id: Unique integer ID of the category to update.
            name: The new display name for the category.
            **kwargs: Optional keyword arguments forwarded to the API (e.g. ``color_id``).

        Returns:
            ``True`` when the category was updated successfully.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating the update failed.
        """
        result = self._client.call("updateCategory", id=id, name=name, **kwargs)
        if not result:
            raise KanboardAPIError(
                f"Failed to update category {id}",
                method="updateCategory",
            )
        return True

    def remove_category(self, category_id: int) -> bool:
        """Remove a category from a project.

        Maps to the Kanboard ``removeCategory`` JSON-RPC method.

        Args:
            category_id: Unique integer ID of the category to remove.

        Returns:
            ``True`` when the category was removed, ``False`` otherwise.
        """
        result = self._client.call("removeCategory", category_id=category_id)
        return bool(result)
