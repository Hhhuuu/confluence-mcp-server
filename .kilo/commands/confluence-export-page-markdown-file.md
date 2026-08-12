---
description: Экспортировать страницу Confluence в Markdown-файл
agent: code
---

Выгрузи страницу Confluence в локальный Markdown-файл.

Используй MCP tool:
- server_name: `confluence-mcp`
- tool_name: `export_page_to_markdown_file`

Если пользователь не указал обязательные параметры, сначала попроси их:
- `page_id`
- `output_path`

Поддерживаемые аргументы:
- `page_id` (обязательный)
- `output_path` (обязательный)
- `enabled_extensions`
- `table_mode`

Передавай только те аргументы, которые указаны пользователем или имеют очевидное безопасное значение по умолчанию.

После выполнения кратко покажи результат, важные предупреждения и ошибки.
