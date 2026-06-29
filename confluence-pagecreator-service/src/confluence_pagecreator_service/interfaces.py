"""Интерфейсы сервисного слоя."""

from __future__ import annotations

from typing import Protocol, Union

from confluence_client import PageData, PageSummary, PagesResponse, UserInfo


class ConfluenceGateway(Protocol):
    """
    Протокол клиента Confluence для сервисного слоя.

    Позволяет подменять реальный REST-клиент тестовым или mock-объектом.
    """

    def current_user(self) -> UserInfo:
        """Получить текущего пользователя."""

    def find_page(self, title: str, space_key: str) -> PagesResponse:
        """Найти страницы по заголовку в пространстве."""

    def find_page_with_limit(self, space_key: str, limit: int) -> PagesResponse:
        """Найти страницы в пространстве с ограничением размера выборки."""

    def find_page_by_id(self, page_id: str) -> PageSummary:
        """Найти страницу по идентификатору."""

    def find_page_by_id_with_storage(self, page_id: str) -> PageSummary:
        """Найти страницу по идентификатору вместе с содержимым."""

    def create_child_page(
        self,
        title: str,
        space_key: str,
        parent_id: Union[int, str],
        content: str,
    ) -> PageData:
        """Создать дочернюю страницу."""
