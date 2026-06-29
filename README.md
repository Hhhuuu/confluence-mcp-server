# Рабочая область Confluence MCP Server

Отдельная рабочая область для миграции `confluence-page-creator-plugin` на Python.

Для внешних потребителей отдельная инструкция лежит в `EXTERNAL_CONSUMERS.md`.

Если проект переносится архивом, пошаговая инструкция лежит в `DEPLOY_FROM_ARCHIVE.md`.

## Структура

- `pagecreator-core` — чистая бизнес-логика
- `confluence-client` — клиент для Confluence REST API
- `pagecreator-service` — сервисный слой
- `pagecreator-mcp-server` — транспортный слой MCP

## Локальная разработка

Для локальной разработки используем editable installs:

```bash
cd pagecreator-mcp-server
pip install -r requirements-dev.txt
```

## Локальный API для ручной проверки

Можно поднять простой HTTP API и проверять логику через `curl` или Postman:

```bash
cd pagecreator-mcp-server
uvicorn run_api:app --reload
```

Доступные endpoint:

- `GET /health` — проверка, что API запущен
- `GET /api/v1/config` — показать активный конфиг
- `POST /api/v1/plan` — построить план без записи в Confluence
- `POST /api/v1/create` — создать страницы в Confluence

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
.venv-mcp/bin/python -m pagecreator_mcp
```

Для локального HTTP-запуска MCP-сервера:

```bash
cd confluence-mcp-server
source .venv-mcp/bin/activate
python pagecreator-mcp-server/run_mcp_http.py
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

## Порядок работ

1. Переносим `pagecreator-core`
2. Затем `confluence-client`
3. Затем `pagecreator-service`
4. После этого собираем `pagecreator-mcp-server`
