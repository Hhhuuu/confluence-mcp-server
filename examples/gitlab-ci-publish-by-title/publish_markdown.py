#!/usr/bin/env python3
"""Опубликовать Markdown в существующую страницу Confluence по space и title."""

from __future__ import annotations

import os
from pathlib import Path

from confluence_client import ConfluenceClient, ConfluenceClientConfig
from confluence_markdown_service import ConfluenceMarkdownImporter


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Не задана обязательная переменная окружения {name}.")
    return value


def env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"Переменная {name} должна содержать true или false.")


def main() -> None:
    deployment = os.getenv("CONFLUENCE_DEPLOYMENT", "server").strip().lower()
    if deployment not in {"server", "cloud"}:
        raise RuntimeError("CONFLUENCE_DEPLOYMENT должен быть server или cloud.")

    markdown_file = Path(os.getenv("MARKDOWN_FILE", "README.md")).expanduser()
    if not markdown_file.is_file():
        raise RuntimeError(f"Markdown-файл не найден: {markdown_file}.")

    space_key = required_env("CONFLUENCE_SPACE_KEY")
    page_title = required_env("CONFLUENCE_PAGE_TITLE")
    auth_type = os.getenv("CONFLUENCE_AUTH_TYPE", "api_token").strip().lower()

    config = ConfluenceClientConfig(
        base_url=required_env("CONFLUENCE_BASE_URL"),
        deployment=deployment,
        auth_type=auth_type,
        username=os.getenv("CONFLUENCE_USERNAME"),
        password=os.getenv("CONFLUENCE_PASSWORD"),
        api_token=os.getenv("CONFLUENCE_API_TOKEN"),
        verify_ssl=env_bool("CONFLUENCE_VERIFY_SSL"),
    )

    with ConfluenceClient(config) as client:
        response = client.find_page(title=page_title, space_key=space_key)
        pages = [page for page in response.results if page.title == page_title]
        if not pages:
            raise RuntimeError(
                f"Страница '{page_title}' не найдена в пространстве '{space_key}'."
            )
        if len(pages) > 1:
            page_ids = ", ".join(page.id for page in pages)
            raise RuntimeError(
                f"В пространстве '{space_key}' найдено несколько страниц "
                f"'{page_title}': {page_ids}."
            )

        importer = ConfluenceMarkdownImporter(
            client,
            builtin_extension_options={
                "mermaid_diagrams": {"enabled": deployment == "server"},
                "table_excerpts": {"enabled": deployment == "server"},
            },
        )
        result = importer.update_page_from_markdown_file(
            page_id=pages[0].id,
            file_path=markdown_file,
        )

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
