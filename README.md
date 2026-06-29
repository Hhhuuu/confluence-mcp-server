# Рабочая область Confluence MCP Server

Отдельная рабочая область для миграции `confluence-page-creator-plugin` на Python.

Для внешних потребителей отдельная инструкция лежит в `EXTERNAL_CONSUMERS.md`.

Если проект переносится архивом, пошаговая инструкция лежит в `DEPLOY_FROM_ARCHIVE.md`.

План по развитию экспорта и импорта Markdown лежит в `MARKDOWN_BRIDGE_PLAN.md`.

## Структура

- `confluence-pagecreator-core` — чистая бизнес-логика
- `confluence-client` — клиент для Confluence REST API
- `confluence-pagecreator-service` — сервисный слой
- `confluence-markdown-service` — сервис экспорта и импорта Markdown
- `confluence-pagecreator-mcp-server` — транспортный слой MCP

## Локальная разработка

Для локальной разработки используем editable installs:

```bash
cd confluence-pagecreator-mcp-server
pip install -r requirements-dev.txt
```

## Локальный API для ручной проверки

Можно поднять простой HTTP API и проверять логику через `curl` или Postman:

```bash
cd confluence-pagecreator-mcp-server
uvicorn run_api:app --reload
```

Доступные endpoint:

- `GET /health` — проверка, что API запущен
- `GET /api/v1/config` — показать активный конфиг
- `POST /api/v1/plan` — построить план без записи в Confluence
- `POST /api/v1/create` — создать страницы в Confluence
- `GET /api/v1/page/{page_id}/markdown` — выгрузить страницу Confluence в Markdown
- `POST /api/v1/page/{page_id}/markdown/file` — выгрузить страницу Confluence сразу в markdown-файл
- `POST /api/v1/page/{page_id}/markdown/tree` — выгрузить страницу и её дочерние страницы в дерево markdown-файлов
- `POST /api/v1/page/markdown/preview` — преобразовать Markdown в Confluence storage без публикации
- `POST /api/v1/page/markdown/preview-file` — преобразовать markdown-файл в Confluence storage без публикации
- `POST /api/v1/page/markdown/create` — создать страницу Confluence из Markdown
- `POST /api/v1/page/markdown/create-file` — создать страницу Confluence из markdown-файла
- `POST /api/v1/page/markdown/update` — обновить страницу Confluence из Markdown
- `POST /api/v1/page/markdown/update-file` — обновить страницу Confluence содержимым из markdown-файла

Особенности file-based markdown-сценариев:

- локальные изображения вида `![alt](./image.png)` автоматически загружаются во вложения страницы
- в storage они преобразуются в `attachment:image.png`
- если вложение с таким именем уже существует, выполняется обновление бинарных данных
- если в одном markdown-файле встречаются разные локальные файлы с одинаковым именем, импорт завершится ошибкой, чтобы не смешать вложения

Пример запроса для предварительного просмотра:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/plan \
  -H "Content-Type: application/json" \
  -d '{
    "paths": ["Root/Team // Dev/Runbook", "Root/FAQ"]
  }'
```

Если нужно использовать нестандартные пути к конфигу и секретам:

```bash
export PAGECREATOR_CONFIG_PATH=/path/to/config/app.yaml
export PAGECREATOR_SECRETS_PATH=/path/to/secrets/confluence.yaml
uvicorn run_api:app --reload
```

Для Confluence Cloud базовый URL должен быть в формате:

```yaml
confluence:
  base_url: "https://your-domain.atlassian.net"
  deployment: "cloud"
```

REST-запросы при этом будут выполняться по путям вида `/wiki/rest/api/...`.

Шаблоны конфигов:

- `config/app.yaml.example`
- `secrets/confluence.yaml.example`

Для Confluence Server или Data Center можно использовать:

```yaml
confluence:
  base_url: "https://confluence.example.local"
  deployment: "server"
```

В этом режиме REST-запросы выполняются без префикса `/wiki`.

## Варианты авторизации

### Cloud через email + API token

```yaml
confluence:
  auth_type: "api_token"
  username: "user@example.com"
  api_token: "..."
```

### Server через логин + пароль

```yaml
confluence:
  auth_type: "basic"
  username: "my-login"
  password: "my-password"
```

### Server через bearer token

Если `auth_type: "api_token"` и `username` не задан, клиент отправит:

```text
Authorization: Bearer <token>
```

## MCP-конфигурация

В корне рабочей области лежит файл `.mcp.json`, который подключает сервер `confluence-mcp` через отдельное окружение `.venv-mcp`.

Команда запуска для stdio-режима:

```bash
.venv-mcp/bin/python -m confluence_pagecreator_mcp
```

Для локального HTTP-запуска MCP-сервера:

```bash
cd confluence-mcp-server
source .venv-mcp/bin/activate
python confluence-pagecreator-mcp-server/run_mcp_http.py
```

## Docker

Сервер можно собрать в Docker-образ.

Сборка:

```bash
cd confluence-mcp-server
docker build -t confluence-mcp:local .
```

### Режим 1. HTTP API для ручной проверки

```bash
docker run --rm -p 8000:8000 \
  -e PAGECREATOR_RUNTIME_MODE=http-api \
  -v "$(pwd)/config:/app/config:ro" \
  -v "$(pwd)/secrets:/app/secrets:ro" \
  confluence-mcp:local
```

### Режим 2. MCP over HTTP

```bash
docker run --rm -p 8000:8000 \
  -e PAGECREATOR_RUNTIME_MODE=mcp-http \
  -e PAGECREATOR_MCP_HOST=0.0.0.0 \
  -e PAGECREATOR_MCP_PORT=8000 \
  -v "$(pwd)/config:/app/config:ro" \
  -v "$(pwd)/secrets:/app/secrets:ro" \
  confluence-mcp:local
```

### Режим 3. MCP stdio

Для `stdio`-режима контейнер обычно запускается самим MCP-клиентом.

Пример ручного запуска:

```bash
docker run --rm -i \
  -e PAGECREATOR_RUNTIME_MODE=mcp-stdio \
  -v "$(pwd)/config:/app/config:ro" \
  -v "$(pwd)/secrets:/app/secrets:ro" \
  confluence-mcp:local
```

Секреты в образ не вшиваются: файл `secrets/confluence.yaml` исключён через `.dockerignore`.

## Текущие ограничения

- При создании структуры сервис пока ищет существующие страницы по комбинации `title + space_key` без дополнительной проверки `parent`.
- Если в одном пространстве уже есть страницы с одинаковыми заголовками в разных ветках, сервис может переиспользовать страницу не из той иерархии вместо создания новой.
- Пока это не исправлено, для `create_pages` безопаснее использовать уникальные заголовки в пределах всего пространства или сначала проверять результат через `plan_pages`.

## Порядок работ

1. Переносим `confluence-pagecreator-core`
2. Затем `confluence-client`
3. Затем `confluence-pagecreator-service`
4. После этого собираем `confluence-pagecreator-mcp-server`
