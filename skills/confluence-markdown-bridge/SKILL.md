---
name: confluence-markdown-bridge
description: Use this skill when the user wants to export a Confluence page to Markdown, preview how Markdown will be converted into Confluence storage format, create a new Confluence page from Markdown, or update an existing Confluence page from Markdown through the local Confluence MCP server.
---

# Confluence Markdown Bridge

Используй этот skill, когда нужно работать с содержимым страниц Confluence через Markdown.

## Что умеет skill

- выгружать страницу Confluence в Markdown
- выгружать страницу Confluence сразу в markdown-файл
- показывать preview `Markdown -> Confluence storage`
- показывать preview `markdown-файл -> Confluence storage`
- создавать страницу из Markdown
- создавать страницу из markdown-файла
- обновлять существующую страницу из Markdown
- обновлять существующую страницу из markdown-файла

## Предусловия

Перед началом убедись, что:

- MCP-сервер `confluence-mcp` подключен
- сервер видит `config/app.yaml`
- сервер видит `secrets/confluence.yaml`

Если есть сомнения по окружению, начни с:

- `show_runtime_config`
- `get_current_user`

## Базовый workflow

### 1. Проверка окружения

Сначала вызови:

- `show_runtime_config`
- `get_current_user`

Проверь:

- `base_url`
- `default_space_key`
- что авторизация проходит

### 2. Экспорт страницы в Markdown

Если пользователь хочет получить содержимое страницы в Markdown, вызови:

- `export_page_to_markdown`

Передавай:

- `page_id`

Если пользователь хочет сразу сохранить результат на диск, вместо этого вызывай:

- `export_page_to_markdown_file`

Передавай:

- `page_id`
- `output_path`

После экспорта:

- покажи `title`
- покажи `markdown`
- отдельно перечисли `warnings`, если были потеряны макросы

### 3. Preview перед публикацией

Перед созданием или обновлением страницы из Markdown сначала вызывай:

- `preview_markdown_to_storage`

Передавай:

- `markdown_text`

Это нужно, чтобы:

- убедиться, что Markdown корректно преобразуется
- увидеть Confluence storage до записи
- проверить специальные конструкции вроде `[TOC]`

Если исходник уже лежит в файле, используй:

- `preview_markdown_file_to_storage`

### 4. Создание страницы из Markdown

Если нужен новый документ, вызывай:

- `create_page_from_markdown`

Передавай:

- `title`
- `markdown_text`
- `parent_id`
- при необходимости `space_key`

Если источник уже хранится на диске, используй:

- `create_page_from_markdown_file`

### 5. Обновление страницы из Markdown

Если нужно обновить уже существующую страницу, вызывай:

- `update_page_from_markdown`

Передавай:

- `page_id`
- `markdown_text`
- при необходимости `title`

Если обновление идёт из локального markdown-файла, используй:

- `update_page_from_markdown_file`

## Какие tools использовать

### Для диагностики

- `show_runtime_config`
- `get_current_user`
- `get_space`
- `get_page`

### Для Markdown workflow

- `export_page_to_markdown`
- `export_page_to_markdown_file`
- `preview_markdown_to_storage`
- `preview_markdown_file_to_storage`
- `create_page_from_markdown`
- `create_page_from_markdown_file`
- `update_page_from_markdown`
- `update_page_from_markdown_file`

## Поддерживаемые возможности v1

Ориентируйся на text-first conversion.

Обычно хорошо поддерживаются:

- заголовки
- абзацы
- списки
- ссылки
- bold / italic
- inline code
- fenced code blocks
- `[TOC]`

## Ограничения v1

Учитывай текущие ограничения:

- часть макросов Confluence при экспорте может теряться
- сложные layout-блоки и встраивания не гарантируют round-trip
- markdown bridge не обещает визуально точную обратимость

Если есть `warnings`, не скрывай их от пользователя.

## Как отвечать пользователю

После `export_page_to_markdown`:

- покажи заголовок страницы
- отдай Markdown
- перечисли `warnings`, если они есть

После `preview_markdown_to_storage`:

- скажи, что это dry-run
- покажи storage только если это действительно полезно пользователю
- отдельно упомяни `warnings`

После `create_page_from_markdown` или `update_page_from_markdown`:

- покажи `title`
- покажи `page_id`
- покажи `page_url`
- отдельно перечисли `warnings`

## Когда не использовать этот skill

Не используй этот skill, если пользователь:

- хочет создать дерево страниц по path-списку
- хочет только диагностировать подключение к Confluence
- хочет работать с layout и макросами без потерь

В этих случаях нужен другой workflow:

- для структуры страниц — `pagecreator-structure`
- для базовой диагностики — общие client/debug tools
