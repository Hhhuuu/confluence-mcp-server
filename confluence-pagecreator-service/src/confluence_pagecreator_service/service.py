"""Сервисный слой для сценария создания страниц."""

from __future__ import annotations

from typing import Dict, List, Optional

from confluence_client import ConfluenceClient, ConfluenceClientConfig, PageData
from confluence_pagecreator_core import build_creation_plan, parse_paths, render_plan_structure

from .config import AppConfig
from .dto import CreatePagesRequest, CreatePagesResult, PlannedPage
from .interfaces import ConfluenceGateway
from .secrets import ConfluenceSecrets


class PageCreatorService:
    """
    Сервис сценария создания страниц.

    Класс связывает доменную логику из `confluence-pagecreator-core` и
    REST-клиент из `confluence-client`.
    """

    def __init__(self, gateway: ConfluenceGateway) -> None:
        """
        Создать сервис с указанным gateway.

        Args:
            gateway: Клиент Confluence или совместимая реализация.
        """

        self._gateway = gateway

    @classmethod
    def from_config(
        cls,
        app_config: AppConfig,
        secrets: ConfluenceSecrets,
    ) -> "PageCreatorService":
        """
        Создать сервис из прикладного конфига и секретов.

        Args:
            app_config: Настройки приложения.
            secrets: Секреты доступа к Confluence.

        Returns:
            Готовый экземпляр `PageCreatorService`.
        """

        gateway = ConfluenceClient(
            ConfluenceClientConfig(
                base_url=app_config.confluence.base_url,
                deployment=app_config.confluence.deployment,
                auth_type=secrets.auth_type,
                username=secrets.username,
                password=secrets.password,
                api_token=secrets.api_token,
                verify_ssl=app_config.confluence.verify_ssl,
            )
        )
        return cls(gateway)

    def create_pages(
        self,
        request: CreatePagesRequest,
        default_space_key: Optional[str] = None,
    ) -> CreatePagesResult:
        """
        Построить план создания страниц и при необходимости выполнить его.

        Args:
            request: Входные данные сценария.
            default_space_key: Пространство по умолчанию.

        Returns:
            Результат планирования или фактического создания страниц.

        Raises:
            ValueError: Если не удалось определить `space_key`.
        """

        space_key = request.space_key or default_space_key
        if not space_key:
            raise ValueError("Не указан space_key и отсутствует значение по умолчанию.")

        parsed_paths = parse_paths(request.paths)
        plan = build_creation_plan(parsed_paths)
        structure = render_plan_structure(plan)

        if request.dry_run:
            return CreatePagesResult(
                space_key=space_key,
                structure=structure,
                items=[
                    PlannedPage(
                        title=item.title,
                        level=item.level,
                        parent_title=item.parent_title,
                        action="plan",
                    )
                    for item in plan.items
                ],
            )

        root_page = self._resolve_root_page(space_key)
        pages_by_title: Dict[str, str] = {root_page.title: root_page.page_id}
        result_items: List[PlannedPage] = []

        for item in plan.items:
            if item.title in pages_by_title:
                result_items.append(
                    PlannedPage(
                        title=item.title,
                        level=item.level,
                        parent_title=item.parent_title,
                        page_id=pages_by_title[item.title],
                        action="skip-existing-in-plan",
                    )
                )
                continue

            existing = self._gateway.find_page(item.title, space_key)
            if existing.results:
                page = existing.results[0]
                pages_by_title[item.title] = page.id
                result_items.append(
                    PlannedPage(
                        title=item.title,
                        level=item.level,
                        parent_title=item.parent_title,
                        page_id=page.id,
                        action="reuse-existing",
                    )
                )
                continue

            parent_title = item.parent_title or root_page.title
            parent_id = pages_by_title[parent_title]
            created = self._gateway.create_child_page(
                title=item.title,
                space_key=space_key,
                parent_id=parent_id,
                content=request.content,
            )
            pages_by_title[item.title] = created.page_id
            result_items.append(self._planned_created(item.title, item.level, item.parent_title, created))

        return CreatePagesResult(
            space_key=space_key,
            structure=structure,
            items=result_items,
        )

    def _resolve_root_page(self, space_key: str) -> PageData:
        pages = self._gateway.find_page_with_limit(space_key, 1)
        if not pages.results:
            raise ValueError(f"Не удалось определить корневую страницу пространства {space_key}.")

        page = pages.results[0]
        return PageData(title=page.title, page_id=page.id, page_url="")

    @staticmethod
    def _planned_created(
        title: str,
        level: int,
        parent_title: Optional[str],
        page: PageData,
    ) -> PlannedPage:
        return PlannedPage(
            title=title,
            level=level,
            parent_title=parent_title,
            page_id=page.page_id,
            page_url=page.page_url,
            action="create",
        )
