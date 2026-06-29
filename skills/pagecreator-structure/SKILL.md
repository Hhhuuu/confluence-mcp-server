---
name: pagecreator-structure
description: Use this skill when the user wants to create a hierarchy of Confluence pages through the local PageCreator MCP server, preview a page tree before creation, validate path structure, inspect the target space or current user, or create nested pages in Confluence Cloud or Confluence Server. This skill is specifically for structure creation workflows based on path lists such as Root/Child/Subchild and for debugging the corresponding PageCreator MCP tools.
---

# PageCreator Structure

Используй этот skill, когда нужно создать или спланировать структуру страниц в Confluence через `PageCreator MCP`.

## Что умеет skill

- проверить, какой конфиг использует сервер
- проверить текущего пользователя Confluence
- проверить доступ к пространству
- построить dry-run план структуры страниц
- создать дерево страниц по списку путей

## Предусловия

Перед работой убедись, что:

- MCP-сервер `pagecreator` подключен
- у сервера есть доступ к `config/app.yaml`
- у сервера есть доступ к `secrets/confluence.yaml`

Если нужно сначала проверить окружение, начни с:

- `show_runtime_config`
- `get_current_user`
- `get_space`

## Базовый workflow

### 1. Проверка окружения

Сначала вызови:

- `show_runtime_config`

Проверь:

- `base_url`
- `default_space_key`
- пути к конфигу и секретам

### 2. Проверка доступа

Потом вызови:

- `get_current_user`
- `get_space`

Если пользователь не читается или пространство не найдено, не переходи к созданию страниц.

### 3. Dry-run

Перед реальным созданием всегда сначала вызывай:

- `plan_pages`

Используй его, чтобы:

- проверить разбор путей
- увидеть итоговую структуру
- убедиться, что экранирование `/` через `//` задано корректно

### 4. Создание

Только после успешного dry-run вызывай:

- `create_pages`

Передавай:

- `paths`
- при необходимости `space_key`
- при необходимости `content`

## Формат путей

Пути задаются так:

```text
Root/Backend/API
Root/Frontend/Web
```

Если в имени страницы нужен символ `/`, экранируй его двойным слешем:

```text
Root/Team // Dev/Runbook
```

Это будет интерпретировано как:

- `Root`
- `Team / Dev`
- `Runbook`

## Какие tools использовать

### Для диагностики

- `show_runtime_config`
- `get_current_user`
- `get_space`
- `find_page`
- `get_page`

### Для структуры

- `plan_pages`
- `create_pages`

## Рекомендуемый порядок вызовов

1. `show_runtime_config`
2. `get_current_user`
3. `get_space`
4. `plan_pages`
5. `create_pages`

## Пример запроса на планирование

Используй такой набор путей:

```json
{
  "paths": [
    "Release 1/Backend/API",
    "Release 1/Backend/Workers",
    "Release 1/Frontend/Web"
  ]
}
```

## Пример запроса на создание

```json
{
  "paths": [
    "Release 1/Backend/API",
    "Release 1/Backend/Workers",
    "Release 1/Frontend/Web"
  ],
  "content": "<p>Создано через PageCreator MCP.</p>"
}
```

## Как отвечать пользователю

После `plan_pages`:

- покажи итоговую структуру
- предупреди, что это dry-run
- попроси подтверждение только если дальше планируется реальное создание

После `create_pages`:

- перечисли созданные страницы
- покажи `page_id`
- покажи `page_url`
- отдельно укажи элементы, которые были переиспользованы, а не созданы заново

## Когда не использовать этот skill

Не используй этот skill, если пользователь:

- хочет редактировать произвольный HTML-контент страницы вручную
- хочет массово обновлять существующие страницы без построения структуры
- хочет удалять или перемещать страницы

В этих случаях нужен отдельный workflow поверх `confluence_client` или другой skill.
