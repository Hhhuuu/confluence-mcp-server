# Развёртывание из архива

## 1. Что нужно положить в архив

В архив рекомендуется включать:

- `confluence-pagecreator-service/`
- `confluence-client/`
- `confluence-markdown-service/`
- `confluence-mcp-server/`
- `config/app.yaml.example`
- `secrets/confluence.yaml.example`
- `skills/`
- `.mcp.json`
- `Dockerfile`
- `.dockerignore`
- `README.md`
- `EXTERNAL_CONSUMERS.md`
- `DEPLOY_FROM_ARCHIVE.md`

## 2. Что не нужно класть в архив

Не включай в архив:

- `.venv/`
- `.venv-mcp/`
- `__pycache__/`
- `*.pyc`
- реальные секреты
- локальные служебные файлы IDE

## 3. Как должна выглядеть структура после распаковки

```text
confluence-mcp-server/
  confluence-pagecreator-service/
  confluence-client/
  confluence-markdown-service/
  confluence-mcp-server/
  config/
    app.yaml.example
  secrets/
    confluence.yaml.example
  skills/
  .mcp.json
  Dockerfile
  .dockerignore
  README.md
  EXTERNAL_CONSUMERS.md
  DEPLOY_FROM_ARCHIVE.md
```

## 4. Подготовка конфигурации

### Шаг 1. Создать рабочий конфиг

Скопируй пример:

```bash
cp config/app.yaml.example config/app.yaml
```

### Шаг 2. Создать файл секретов

Скопируй пример:

```bash
cp secrets/confluence.yaml.example secrets/confluence.yaml
```

### Шаг 3. Заполнить значения

#### Для Confluence Cloud

`config/app.yaml`

```yaml
confluence:
  base_url: "https://your-domain.atlassian.net"
  deployment: "cloud"
  verify_ssl: true
  default_space_key: "~your-space-key"
```

`secrets/confluence.yaml`

```yaml
confluence:
  auth_type: "api_token"
  username: "user@example.com"
  api_token: "your-api-token"
```

#### Для Confluence Server

`config/app.yaml`

```yaml
confluence:
  base_url: "https://confluence.example.local"
  deployment: "server"
  verify_ssl: true
  default_space_key: "DOC"
```

`secrets/confluence.yaml`

```yaml
confluence:
  auth_type: "basic"
  username: "my-login"
  password: "my-password"
```

## 5. Развёртывание для локального HTTP API

### Шаг 1. Создать виртуальное окружение

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

### Шаг 2. Установить пакеты

```bash
pip install -e confluence-pagecreator-service
pip install -e confluence-client
pip install -e confluence-markdown-service
pip install -e confluence-mcp-server
```

### Шаг 3. Запустить локальный API

```bash
uvicorn confluence_mcp.api:app --app-dir confluence-mcp-server/src --host 127.0.0.1 --port 8000
```

### Шаг 4. Проверить, что API жив

```bash
curl http://127.0.0.1:8000/health
```

## 6. Развёртывание для MCP

Для MCP нужен Python `3.10+`.

Рекомендуемый вариант: отдельное окружение `.venv-mcp`.

### Шаг 1. Создать отдельное окружение

```bash
python3.12 -m venv .venv-mcp
source .venv-mcp/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

Если `python3.12` недоступен, используй любой Python `3.10+`.

### Шаг 2. Установить пакеты

```bash
pip install -e confluence-pagecreator-service
pip install -e confluence-client
pip install -e confluence-markdown-service
pip install -e confluence-mcp-server
```

### Шаг 3. Запуск stdio MCP

```bash
./scripts/run_mcp.sh
```

### Шаг 4. Проверка `.mcp.json`

Файл `.mcp.json` уже подготовлен для запуска из корня проекта:

```json
{
  "mcpServers": {
    "confluence-mcp": {
      "command": "./scripts/run_mcp.sh"
    }
  }
}
```

Если MCP-клиент поддерживает project-level `.mcp.json`, этого обычно достаточно.

## 7. Развёртывание через Docker

### Шаг 1. Собрать образ

```bash
docker build -t confluence-mcp:local .
```

### Шаг 2. Запустить HTTP API

```bash
docker run --rm -p 8000:8000 \
  -e PAGECREATOR_RUNTIME_MODE=http-api \
  -v "$(pwd)/config:/app/config:ro" \
  -v "$(pwd)/secrets:/app/secrets:ro" \
  confluence-mcp:local
```

### Шаг 3. Запустить MCP over HTTP

```bash
docker run --rm -p 8000:8000 \
  -e PAGECREATOR_RUNTIME_MODE=mcp-http \
  -e PAGECREATOR_MCP_HOST=0.0.0.0 \
  -e PAGECREATOR_MCP_PORT=8000 \
  -v "$(pwd)/config:/app/config:ro" \
  -v "$(pwd)/secrets:/app/secrets:ro" \
  confluence-mcp:local
```

### Шаг 4. Запустить MCP stdio

```bash
docker run --rm -i \
  -e PAGECREATOR_RUNTIME_MODE=mcp-stdio \
  -v "$(pwd)/config:/app/config:ro" \
  -v "$(pwd)/secrets:/app/secrets:ro" \
  confluence-mcp:local
```

## 8. Рекомендуемая проверка после развёртывания

Порядок проверки:

1. `show_runtime_config`
2. `get_current_user`
3. `get_space`
4. `find_page`
5. `get_page`
6. `plan_pages`
7. `create_pages`

## 9. Типовые проблемы

### MCP не стартует

Проверь:

- что используется Python `3.10+`
- что `.venv-mcp` существует
- что `confluence-mcp-server` установлен

### Не работает авторизация

Проверь:

- `auth_type`
- `username`
- `password` или `api_token`
- права доступа к пространству

### Не находится пространство

Проверь:

- `default_space_key`
- режим `deployment`
- `base_url`

### Для Cloud приходят 404 по API

Проверь:

- что `deployment: "cloud"`
- что `base_url` без `/wiki`

### Для Server не работают REST-пути

Проверь:

- что `deployment: "server"`
- что не используется Cloud-домен
