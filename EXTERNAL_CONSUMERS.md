# Confluence MCP Server: Документация для внешних потребителей

## 1. Назначение

`Confluence MCP Server` — это MCP-сервер для работы с Confluence.

Сервер позволяет:

- проверять подключение к Confluence
- получать информацию о пользователе и пространстве
- искать и читать страницы
- выгружать страницы в Markdown
- публиковать Markdown в Confluence
- строить план создания иерархии страниц
- создавать вложенные страницы в Confluence

Сервер поддерживает:

- `Confluence Cloud`
- `Confluence Server / Data Center`
- авторизацию через `логин + пароль`
- авторизацию через `API token`

## 2. Основные возможности

### Диагностика подключения

- `show_runtime_config`
- `get_current_user`
- `get_space`

### Работа со страницами

- `find_page`
- `get_page`

### Markdown bridge

- `export_page_to_markdown`
- `export_page_to_markdown_file`
- `preview_markdown_to_storage`
- `preview_markdown_file_to_storage`
- `create_page_from_markdown`
- `create_page_from_markdown_file`
- `update_page_from_markdown`
- `update_page_from_markdown_file`

### Работа с иерархией

- `plan_pages`
- `create_pages`

## 3. Поддерживаемые режимы Confluence

### Confluence Cloud

Используется:

- `base_url` вида `https://your-domain.atlassian.net`
- `deployment = "cloud"`

В этом режиме REST-вызовы идут через префикс `/wiki`.

### Confluence Server / Data Center

Используется:

- `base_url` вида `https://confluence.example.local`
- `deployment = "server"`

В этом режиме REST-вызовы идут без `/wiki`.

## 4. Поддерживаемые варианты авторизации

### Вариант 1. Basic auth

Подходит для:

- Confluence Server
- некоторых внутренних инсталляций

Используются:

- `username`
- `password`

### Вариант 2. API token c username

Подходит для:

- Atlassian Confluence Cloud

Используются:

- `username` — обычно email
- `api_token`

Фактически клиент отправляет basic auth с `username + api_token`.

### Вариант 3. Bearer token

Подходит для:

- некоторых server-установок
- сервисных интеграций

Используются:

- `auth_type = "api_token"`
- `api_token`
- `username` можно не указывать

В этом режиме клиент отправляет:

```text
Authorization: Bearer <token>
```

## 5. Конфигурация

### Файл `config/app.yaml`

Пример для Confluence Cloud:

```yaml
confluence:
  base_url: "https://your-domain.atlassian.net"
  deployment: "cloud"
  verify_ssl: true
  default_space_key: "~personal-space-key"
```

Пример для Confluence Server:

```yaml
confluence:
  base_url: "https://confluence.example.local"
  deployment: "server"
  verify_ssl: true
  default_space_key: "DOC"
```

### Файл `secrets/confluence.yaml`

Пример для Cloud:

```yaml
confluence:
  auth_type: "api_token"
  username: "user@example.com"
  api_token: "your-api-token"
```

Пример для Server с логином и паролем:

```yaml
confluence:
  auth_type: "basic"
  username: "my-login"
  password: "my-password"
```

Пример для Bearer token:

```yaml
confluence:
  auth_type: "api_token"
  api_token: "your-service-token"
```

## 6. Подключение MCP-сервера

В проекте уже есть файл `.mcp.json`, который описывает запуск сервера в `stdio`-режиме.

Базовая команда запуска:

```bash
.venv-mcp/bin/python -m confluence_mcp
```

Если MCP-клиент поддерживает запуск через `command + args`, можно использовать такую конфигурацию:

```json
{
  "mcpServers": {
    "confluence-mcp": {
      "command": ".venv-mcp/bin/python",
      "args": ["-m", "confluence_mcp"],
      "env": {
        "PAGECREATOR_CONFIG_PATH": "config/app.yaml",
        "PAGECREATOR_SECRETS_PATH": "secrets/confluence.yaml"
      }
    }
  }
}
```

Для Kilo это можно подключить так

```json
{
  "mcpServers": {
    "confluence-mcp": {
      "type": "local",
      "workdir": "~/projects/confluence-mcp-server",
      "command": ["~/projects/confluence-mcp-server/scripts/run_mcp.sh"],
      "enabled": true
    }
  }
}

```

## 7. Описание MCP tools

### `show_runtime_config`

Назначение:

- показать, какие конфиги и секреты использует сервер

Вход:

- без параметров

Выход:

- пути к конфигам
- `base_url`
- `default_space_key`

Когда использовать:

- при первой проверке подключения
- при отладке окружения

### `get_current_user`

Назначение:

- проверить авторизацию и получить текущего пользователя

Вход:

- без параметров

Выход:

- `account_id`
- `display_name`
- `public_name`
- `username`

Когда использовать:

- для smoke-check после настройки секретов

### `get_space`

Назначение:

- получить информацию о пространстве

Вход:

- `space_key` — опционально

Если не передан:

- используется `default_space_key`

Выход:

- `id`
- `key`
- `name`
- `type`
- `homepage`

Когда использовать:

- чтобы проверить доступ к пространству
- чтобы получить `homepage id`

### `find_page`

Назначение:

- найти страницы по заголовку

Вход:

- `title`
- `space_key` — опционально

Выход:

- список найденных страниц

Когда использовать:

- перед созданием страниц
- для ручной проверки дублей

### `get_page`

Назначение:

- получить страницу по `page_id`

Вход:

- `page_id`
- `include_storage` — `true/false`

Выход:

- краткая информация по странице
- если `include_storage=true`, также возвращается `body.storage`

Когда использовать:

- для чтения страницы
- для проверки содержимого

### `plan_pages`

Назначение:

- построить dry-run план создания страниц без записи в Confluence

Вход:

- `paths`
- `space_key` — опционально

Выход:

- `space_key`
- `structure`
- `items`

Когда использовать:

- перед реальным созданием дерева

### `create_pages`

Назначение:

- создать дерево страниц в Confluence

Вход:

- `paths`
- `space_key` — опционально
- `content` — базовое содержимое создаваемых страниц

Выход:

- итоговая структура
- список созданных или найденных страниц
- `page_id`
- `page_url`
- `action`

Когда использовать:

- для реального создания иерархии страниц

### `export_page_to_markdown`

Назначение:

- выгрузить страницу Confluence в Markdown

Вход:

- `page_id`

Выход:

- `page_id`
- `title`
- `space_key`
- `markdown`
- `warnings`

Когда использовать:

- для экспорта содержимого страницы в Markdown
- для подготовки контента к локальной правке

### `export_page_to_markdown_file`

Назначение:

- выгрузить страницу Confluence сразу в локальный markdown-файл

Вход:

- `page_id`
- `output_path`

Выход:

- `page_id`
- `title`
- `space_key`
- `output_path`
- `warnings`

Когда использовать:

- когда нужен файл на диске, а не markdown-строка в ответе

### `export_page_tree_to_markdown_files`

Назначение:

- выгрузить страницу и все её дочерние страницы в дерево локальных markdown-файлов

Вход:

- `page_id`
- `output_dir`

Выход:

- `root_page_id`
- `root_title`
- `output_dir`
- `items`
- `warnings`

Когда использовать:

- когда нужно локально сохранить целую ветку Confluence
- когда нужен файловый архив структуры страниц для последующей правки

### `preview_markdown_to_storage`

Назначение:

- предварительно преобразовать Markdown в `body.storage` без публикации

Вход:

- `markdown_text`

Выход:

- `storage`
- `warnings`

Когда использовать:

- перед публикацией Markdown в Confluence
- для отладки конвертации

### `preview_markdown_file_to_storage`

Назначение:

- предварительно преобразовать локальный markdown-файл в `body.storage`

Вход:

- `file_path`

Выход:

- `storage`
- `source_path`
- `warnings`

Когда использовать:

- перед публикацией большого markdown-файла
- для проверки локального документа без записи в Confluence

### `create_page_from_markdown`

Назначение:

- создать страницу Confluence из Markdown

Вход:

- `title`
- `markdown_text`
- `parent_id`
- `space_key` — опционально

Выход:

- `title`
- `page_id`
- `page_url`
- `warnings`

Когда использовать:

- для публикации нового Markdown-документа в Confluence

### `create_page_from_markdown_file`

Назначение:

- создать страницу Confluence из локального markdown-файла

Вход:

- `title`
- `file_path`
- `parent_id`
- `space_key` — опционально

Выход:

- `title`
- `page_id`
- `page_url`
- `source_path`
- `attachments`
- `warnings`

Когда использовать:

- когда markdown уже хранится в файле на диске
- когда локальные изображения должны автоматически уйти во вложения страницы

### `update_page_from_markdown`

Назначение:

- обновить существующую страницу содержимым из Markdown

Вход:

- `page_id`
- `markdown_text`
- `title` — опционально

Выход:

- `title`
- `page_id`
- `page_url`
- `warnings`

Когда использовать:

- для повторной публикации Markdown в уже существующую страницу

### `update_page_from_markdown_file`

Назначение:

- обновить страницу содержимым из локального markdown-файла

Вход:

- `page_id`
- `file_path`
- `title` — опционально

Выход:

- `title`
- `page_id`
- `page_url`
- `source_path`
- `attachments`
- `warnings`

Когда использовать:

- когда локальный markdown-файл является источником истины для страницы
- когда нужно обновить и контент, и локальные картинки одним вызовом

## 8. Формат путей для `plan_pages` и `create_pages`

Пути задаются в формате:

```text
Root/Child/Subchild
```

Если в названии страницы нужен символ `/`, его нужно экранировать двойным слешем:

```text
Root/Team // Dev/Runbook
```

Это будет интерпретировано как:

- `Root`
- `Team / Dev`
- `Runbook`

## 9. Примеры использования

### Пример 1. Проверка пользователя

```json
{
  "tool": "get_current_user",
  "arguments": {}
}
```

### Пример 2. Получение пространства

```json
{
  "tool": "get_space",
  "arguments": {
    "space_key": "~7012138c5e2a1b11a4d72934257fb7651f81c"
  }
}
```

### Пример 3. Поиск страницы

```json
{
  "tool": "find_page",
  "arguments": {
    "title": "Обзор",
    "space_key": "~7012138c5e2a1b11a4d72934257fb7651f81c"
  }
}
```

### Пример 4. Чтение страницы с контентом

```json
{
  "tool": "get_page",
  "arguments": {
    "page_id": "163939",
    "include_storage": true
  }
}
```

### Пример 5. Dry-run плана

```json
{
  "tool": "plan_pages",
  "arguments": {
    "paths": [
      "Page A/Backend/API",
      "Page A/Backend/Workers",
      "Page A/Frontend/Web"
    ]
  }
}
```

### Пример 6. Создание дерева страниц

```json
{
  "tool": "create_pages",
  "arguments": {
    "paths": [
      "Page A/Backend/API",
      "Page A/Backend/Workers",
      "Page A/Frontend/Web"
    ],
    "content": "<p>Создано через PageCreator MCP.</p>"
  }
}
```

## 10. Типовые ошибки

### Ошибка авторизации

Причины:

- неверный `username`
- неверный `password`
- неверный `api_token`
- токен отозван

### Пространство не найдено

Причины:

- неверный `space_key`
- у пользователя нет доступа к пространству

### Страница не найдена

Причины:

- неверный `page_id`
- страница удалена
- нет прав на чтение

### Некорректный путь

Причины:

- передан пустой путь
- внутри одного пути есть повторяющиеся названия
- некорректно задано экранирование `/`

## 11. Рекомендуемый порядок интеграции

Для внешнего потребителя рекомендую идти в таком порядке:

1. Настроить `config/app.yaml`
2. Настроить `secrets/confluence.yaml`
3. Вызвать `show_runtime_config`
4. Вызвать `get_current_user`
5. Вызвать `get_space`
6. Вызвать `plan_pages`
7. Только после этого вызывать `create_pages`

## 12. Ограничения текущей версии

Текущая реализация ориентирована на:

- создание иерархии страниц
- чтение страниц и пространств
- Cloud и Server REST API через `content`

Пока не реализовано:

- удаление страниц
- перемещение страниц
- массовое обновление дерева
- расширенные стратегии поиска страниц по родителю

Поведение markdown-экспорта:

- неизвестные макросы, кастомные блоки и нестандартные HTML/XML-элементы обрабатываются в режиме best effort
- если из такого блока удаётся извлечь текст, он будет выгружен как обычный markdown-текст с warning
- исходное форматирование неизвестных блоков при этом не гарантируется

## 13. Что важно для эксплуатации

- для Atlassian Cloud лучше использовать `API token`, а не пароль
- `space_key` лучше фиксировать явно в конфиге
- перед массовым созданием страниц всегда сначала использовать `plan_pages`
- секреты не должны попадать в git
