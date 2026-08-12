---
description: Преобразовать Markdown-файл в Confluence storage без публикации
agent: code
---

Преобразуй локальный Markdown-файл в Confluence storage format без публикации.

Используй MCP tool:
- server_name: `confluence-mcp`
- tool_name: `preview_markdown_file_to_storage`

Если пользователь не указал обязательные параметры, сначала попроси их:
- `file_path`

Поддерживаемые аргументы:
- `file_path` (обязательный)
- `enabled_extensions`

Передавай только те аргументы, которые указаны пользователем или имеют очевидное безопасное значение по умолчанию.

После выполнения кратко покажи результат, важные предупреждения и ошибки.
