---
description: Преобразовать Markdown в Confluence storage без публикации
agent: code
---

Преобразуй Markdown в Confluence storage format без публикации.

Используй MCP tool:
- server_name: `confluence-mcp`
- tool_name: `preview_markdown_to_storage`

Если пользователь не указал обязательные параметры, сначала попроси их:
- `markdown_text`

Поддерживаемые аргументы:
- `markdown_text` (обязательный)
- `enabled_extensions`

Передавай только те аргументы, которые указаны пользователем или имеют очевидное безопасное значение по умолчанию.

После выполнения кратко покажи результат, важные предупреждения и ошибки.
