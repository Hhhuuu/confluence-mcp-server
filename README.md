# Рабочая область Confluence MCP Server

Отдельная рабочая область для миграции `confluence-page-creator-plugin` на Python.

## Дополнительная документация

- `scripts/setup_mcp.ps1` / `scripts/setup_mcp.sh` — полная установка и настройка под Python 3.10+
- `scripts/install_mcp.ps1` / `scripts/install_mcp.sh` — клонирование или обновление репозитория с последующей настройкой
- `EXTERNAL_CONSUMERS.md` — инструкция для внешних потребителей MCP-сервера
- `LOCAL_ENVIRONMENTS.md` — установка, шаблоны конфигурации и нативный запуск
- `MCP_CONNECTION_GUIDE.md` — конфигурации Kilo Code 7.49+ и Kilo CLI для Windows, Linux и macOS
- `MARKDOWN_BRIDGE_PLAN.md` — план развития markdown bridge
- `EXTENSIONS.md` — система markdown-расширений, встроенные плагины и инструкция по добавлению своих
- `KNOWLEDGE_MODEL.md` — модель знаний проекта для анализа, поиска и автоматизации
- `RAG_ARCHITECTURE.md` — проектная схема индексации и retrieval для RAG

## Структура

- `confluence-pagecreator-service` — сервис page creator, включая разбор путей и построение плана
- `confluence-client` — клиент для Confluence REST API
- `confluence-markdown-service` — сервис экспорта и импорта Markdown
- `confluence-mcp-server` — общий HTTP- и MCP-транспорт для page creator и markdown-сценариев

## Локальная разработка

Проект требует Python 3.10 или новее. Автоматическая установка в
`.venv-mcp`:

```bash
./scripts/setup_mcp.sh
```

В Windows PowerShell:

```powershell
.\scripts\setup_mcp.ps1
```

## Локальный API для ручной проверки

Можно поднять простой HTTP API и проверять логику через `curl` или Postman:

```bash
cd confluence-mcp-server
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
- обычные локальные ссылки вида `[spec](./spec.pdf)` тоже загружаются как вложения страницы
- при экспорте рядом с markdown создаётся директория `attachments/`, и нужные вложения страницы сохраняются туда
- ссылки `attachment:...` в выгруженном markdown переписываются в относительные пути вида `./attachments/file.pdf`
- в storage изображения и файлы преобразуются в attachment-ссылки Confluence
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

Для изменения порядка и иерархии страниц доступен MCP tool `move_page`:

- `page_id` — страница, которую нужно переместить;
- `target_page_id` — страница-ориентир;
- `position` — `before`, `after` или `append`.

`before` и `after` задают порядок среди соседних страниц, `append` переносит
страницу под `target_page_id` и делает её последней дочерней страницей.
Cloud для этого использует REST endpoint `content/{id}/move`, а Server/Data Center —
токен-совместимое обновление `ancestors` через Content REST API. В Server/DC 8.5
через PAT доступен только `append` без гарантии порядка; `before/after` не поддерживаются.

В `create_pages` параметр `content` по умолчанию считается Markdown. Готовый
Confluence Storage Format можно передать с `content_format="storage"`.

Bootstrap генерирует в `.kilo-generated` отдельные конфигурации Kilo Code
7.49+ и Kilo CLI для Windows, Linux и macOS. Они используют абсолютный путь до
Python 3.10+ из `.venv-mcp` и локальные пути к YAML.

Команда запуска для stdio-режима:

```bash
./scripts/run_mcp.sh
```

Для локального HTTP-запуска MCP-сервера:

```bash
cd confluence-mcp-server
source .venv-mcp/bin/activate
python run_mcp_http.py
```

## Текущие ограничения

- При создании структуры сервис пока ищет существующие страницы по комбинации `title + space_key` без дополнительной проверки `parent`.
- Если в одном пространстве уже есть страницы с одинаковыми заголовками в разных ветках, сервис может переиспользовать страницу не из той иерархии вместо создания новой.
- Пока это не исправлено, для `create_pages` безопаснее использовать уникальные заголовки в пределах всего пространства или сначала проверять результат через `plan_pages`.
- При экспорте `Confluence -> Markdown` неизвестные макросы, кастомные блоки и нестандартные HTML/XML-узлы выгружаются в режиме best effort: если удаётся извлечь текст, он попадёт в markdown как обычный текст.
- Такой fallback помогает не терять содержимое полностью, но не гарантирует сохранение исходного форматирования или точный roundtrip для неизвестных блоков.

## Порядок работ

1. Переносим `confluence-pagecreator-service`
2. Затем `confluence-client`
3. Затем `confluence-markdown-service`
4. После этого собираем `confluence-mcp-server`
