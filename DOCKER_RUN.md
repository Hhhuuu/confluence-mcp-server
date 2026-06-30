# Confluence MCP Server: Запуск в Docker

## 1. Назначение

Этот документ описывает, как собрать и запустить `confluence-mcp-server` в Docker.

Поддерживаются три режима:

- `http-api` — локальный HTTP API для ручной проверки
- `mcp-http` — MCP через streamable HTTP
- `mcp-stdio` — MCP через stdio

## 2. Что должно быть подготовлено

Перед запуском должны существовать:

- `config/app.yaml`
- `secrets/confluence.yaml`

Шаблоны:

- `config/app.yaml.example`
- `secrets/confluence.yaml.example`

Пример `config/app.yaml` для Confluence Cloud:

```yaml
confluence:
  base_url: "https://your-domain.atlassian.net"
  deployment: "cloud"
  verify_ssl: true
  default_space_key: "~personal-space-key"
```

Пример `config/app.yaml` для Confluence Server:

```yaml
confluence:
  base_url: "https://confluence.example.local"
  deployment: "server"
  verify_ssl: true
  default_space_key: "DOC"
```

Пример `secrets/confluence.yaml`:

```yaml
confluence:
  auth_type: "api_token"
  username: "user@example.com"
  api_token: "your-api-token"
```

## 3. Сборка образа

Из корня проекта:

```bash
docker build -t confluence-mcp:local .
```

Если хочешь своё имя образа:

```bash
docker build -t my-company/confluence-mcp:dev .
```

## 4. Запуск HTTP API

Этот режим нужен для:

- ручной отладки
- curl-запросов
- smoke-check

Команда:

```bash
docker run --rm -p 8000:8000 \
  -e PAGECREATOR_RUNTIME_MODE=http-api \
  -v "$(pwd)/config:/app/config:ro" \
  -v "$(pwd)/secrets:/app/secrets:ro" \
  confluence-mcp:local
```

После запуска доступны:

- `GET /health`
- `GET /api/v1/config`
- `POST /api/v1/plan`
- `POST /api/v1/create`
- `GET /api/v1/page/{page_id}/markdown`
- `POST /api/v1/page/{page_id}/markdown/file`
- `POST /api/v1/page/{page_id}/markdown/tree`
- `POST /api/v1/page/markdown/preview`
- `POST /api/v1/page/markdown/preview-file`
- `POST /api/v1/page/markdown/create`
- `POST /api/v1/page/markdown/create-file`
- `POST /api/v1/page/markdown/update`
- `POST /api/v1/page/markdown/update-file`
- debug endpoints клиента Confluence, если они включены в текущей сборке

### Быстрая проверка

```bash
curl http://127.0.0.1:8000/health
```

```bash
curl http://127.0.0.1:8000/api/v1/config
```

```bash
curl -X POST http://127.0.0.1:8000/api/v1/plan \
  -H "Content-Type: application/json" \
  -d '{
    "paths": ["Root/Team // Dev/Runbook", "Root/FAQ"]
  }'
```

## 5. Запуск MCP over HTTP

Этот режим нужен, если MCP-клиент умеет работать с HTTP transport.

Команда:

```bash
docker run --rm -p 8000:8000 \
  -e PAGECREATOR_RUNTIME_MODE=mcp-http \
  -e PAGECREATOR_MCP_HOST=0.0.0.0 \
  -e PAGECREATOR_MCP_PORT=8000 \
  -v "$(pwd)/config:/app/config:ro" \
  -v "$(pwd)/secrets:/app/secrets:ro" \
  confluence-mcp:local
```

## 6. Запуск MCP stdio

Этот режим нужен, если MCP-клиент запускает сервер как локальную команду.

Команда:

```bash
docker run --rm -i \
  -e PAGECREATOR_RUNTIME_MODE=mcp-stdio \
  -v "$(pwd)/config:/app/config:ro" \
  -v "$(pwd)/secrets:/app/secrets:ro" \
  confluence-mcp:local
```

## 7. Примеры подключения MCP-клиента через Docker

### Вариант 1. MCP stdio через `docker run`

Подходит для клиентов, которые умеют запускать локальную команду.

Пример конфигурации:

```json
{
  "mcpServers": {
    "confluence-mcp": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-e",
        "PAGECREATOR_RUNTIME_MODE=mcp-stdio",
        "-v",
        "./config:/app/config:ro",
        "-v",
        "./secrets:/app/secrets:ro",
        "confluence-mcp:local"
      ]
    }
  }
}
```

Если MCP-клиент не любит относительные пути, используй абсолютные пути для volume mounts.

### Вариант 2. MCP over HTTP

Сначала подними контейнер:

```bash
docker run --rm -p 8000:8000 \
  -e PAGECREATOR_RUNTIME_MODE=mcp-http \
  -e PAGECREATOR_MCP_HOST=0.0.0.0 \
  -e PAGECREATOR_MCP_PORT=8000 \
  -v "$(pwd)/config:/app/config:ro" \
  -v "$(pwd)/secrets:/app/secrets:ro" \
  confluence-mcp:local
```

После этого MCP-клиент подключается к HTTP endpoint контейнера.

Если клиент ожидает URL, обычно используется адрес вида:

```text
http://127.0.0.1:8000/mcp
```

Если конкретный клиент требует другой формат MCP HTTP-конфигурации, укажи тот же базовый URL контейнера.

## 8. Какие переменные окружения поддерживаются

### Общие

- `PAGECREATOR_CONFIG_PATH`
- `PAGECREATOR_SECRETS_PATH`
- `PAGECREATOR_RUNTIME_MODE`

По умолчанию внутри контейнера используются:

- `/app/config/app.yaml`
- `/app/secrets/confluence.yaml`

### Для HTTP API

- `PAGECREATOR_HTTP_HOST`
- `PAGECREATOR_HTTP_PORT`

По умолчанию:

- `PAGECREATOR_HTTP_HOST=0.0.0.0`
- `PAGECREATOR_HTTP_PORT=8000`

### Для MCP HTTP

- `PAGECREATOR_MCP_HOST`
- `PAGECREATOR_MCP_PORT`

По умолчанию:

- `PAGECREATOR_MCP_HOST=0.0.0.0`
- `PAGECREATOR_MCP_PORT=8000`

## 9. Безопасность

Реальные секреты не копируются в образ:

- `secrets/confluence.yaml` исключён через `.dockerignore`

Поэтому секреты передаются только через volume mount:

```bash
-v "$(pwd)/secrets:/app/secrets:ro"
```

Это рекомендуемый способ и для локальной работы, и для CI/CD.

## 10. Типовой сценарий запуска

1. Создать `config/app.yaml`
2. Создать `secrets/confluence.yaml`
3. Собрать образ:

```bash
docker build -t confluence-mcp:local .
```

4. Поднять HTTP API:

```bash
docker run --rm -p 8000:8000 \
  -e PAGECREATOR_RUNTIME_MODE=http-api \
  -v "$(pwd)/config:/app/config:ro" \
  -v "$(pwd)/secrets:/app/secrets:ro" \
  confluence-mcp:local
```

5. Проверить:

```bash
curl http://127.0.0.1:8000/health
```

## 11. Типовые проблемы

### Контейнер стартует, но Confluence не отвечает

Проверь:

- правильность `base_url`
- токен / логин / пароль
- доступность Confluence из среды, где запускается Docker

### `/api/v1/config` работает, а операции чтения или записи падают

Чаще всего это означает:

- нет доступа к нужному `space`
- неверно указан `default_space_key`
- неверный `page_id`
- для Cloud указан `deployment: "server"` или наоборот

### Markdown-публикация работает не так, как ожидалось

Проверь:

- запускаешь ли Cloud в `deployment: "cloud"`
- не используешь ли сложные макросы или layout, которые находятся вне поддерживаемого поднабора
- для file-based сценариев, существуют ли локальные картинки и нет ли конфликтов имён вложений

### MCP-клиент не умеет относительные пути

Тогда лучше:

- использовать локальный launcher `scripts/run_mcp.sh`
- либо запускать через Docker как фиксированную команду

## 12. Что дальше

После запуска на Docker можно:

- использовать HTTP API для ручной проверки
- подключить MCP-клиент к HTTP или stdio режиму
- строить иерархии страниц
- экспортировать страницы в Markdown
- публиковать Markdown обратно в Confluence
