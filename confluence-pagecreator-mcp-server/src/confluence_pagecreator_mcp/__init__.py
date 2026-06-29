"""Пакет MCP-сервера для создания страниц."""

from .api import app
from .launch import main as launch_main
from .mcp_server import mcp, main
from .server import build_service, build_toolset
from .tools import create_pages, plan_pages

__all__ = [
    "app",
    "build_service",
    "build_toolset",
    "create_pages",
    "launch_main",
    "main",
    "mcp",
    "plan_pages",
]
