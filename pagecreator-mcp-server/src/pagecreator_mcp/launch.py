"""Универсальная точка входа для локального запуска и Docker."""

from __future__ import annotations

import os

import uvicorn

from .api import app
from .mcp_server import mcp


def main() -> None:
    """
    Запустить один из режимов runtime по переменной окружения.

    Поддерживаемые режимы:

    - `http-api` — локальный HTTP API для ручной проверки
    - `mcp-http` — MCP через streamable HTTP
    - `mcp-stdio` — MCP через stdio
    """

    mode = os.getenv("PAGECREATOR_RUNTIME_MODE", "http-api").strip().lower()

    if mode == "http-api":
        host = os.getenv("PAGECREATOR_HTTP_HOST", "0.0.0.0")
        port = int(os.getenv("PAGECREATOR_HTTP_PORT", "8000"))
        uvicorn.run(app, host=host, port=port)
        return

    if mode == "mcp-http":
        mcp.run(transport="streamable-http")
        return

    if mode == "mcp-stdio":
        mcp.run(transport="stdio")
        return

    raise ValueError(
        "Поддерживаются режимы PAGECREATOR_RUNTIME_MODE=http-api, mcp-http, mcp-stdio."
    )


if __name__ == "__main__":
    main()
