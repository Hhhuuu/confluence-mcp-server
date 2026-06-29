"""Точка входа для локального HTTP-запуска MCP-сервера."""

from confluence_mcp.mcp_server import mcp


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
