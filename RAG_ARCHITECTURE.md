# Confluence MCP Server: Архитектура retrieval и RAG

## 1. Назначение

Этот документ описывает, как организовать retrieval по знаниям вокруг `confluence-mcp-server`, чтобы AI-агент:

- быстро находил нужный слой
- не перегружал контекст лишними файлами
- уверенно отвечал на вопросы о runtime, API, MCP и markdown bridge
- различал архитектурные знания, код и пользовательскую документацию

Документ описывает именно модель retrieval и индексации, а не конкретную реализацию.

## 2. Какие источники индексировать

### 2.1 Код

Индексировать:

- `confluence-client/src`
- `confluence-pagecreator-service/src`
- `confluence-markdown-service/src`
- `confluence-mcp-server/src`

Особенно важны:

- `client.py`
- `service.py`
- `exporter.py`
- `importer.py`
- `api.py`
- `mcp_server.py`
- `runtime.py`
- `launch.py`

### 2.2 Конфигурация

Индексировать:

- `config/app.yaml.example`
- `secrets/confluence.yaml.example`
- `.mcp.json`
- `Dockerfile`
- `.dockerignore`
- `scripts/run_mcp.sh`

Реальные секреты индексировать нельзя.

### 2.3 Документация

Индексировать:

- `README.md`
- `EXTERNAL_CONSUMERS.md`
- `DOCKER_RUN.md`
- `LOCAL_ENVIRONMENTS.md`
- `DEPLOY_FROM_ARCHIVE.md`
- `MARKDOWN_BRIDGE_PLAN.md`
- `KNOWLEDGE_MODEL.md`
- `RAG_ARCHITECTURE.md`

### 2.4 Ограниченно индексируемые артефакты

Лучше не включать как полноценные источники знаний:

- `tmp/`
- `.venv/`
- `.venv-mcp/`
- `__pycache__/`
- локальные smoke-test файлы
- архивы вроде `python-pagecreator.zip`

Их можно учитывать только как временный контекст, если пользователь явно про них спрашивает.

## 3. Что индексировать целиком, а что резать на чанки

### Индексировать целиком

Хорошо подходят для полного документа:

- `README.md`
- `EXTERNAL_CONSUMERS.md`
- `DOCKER_RUN.md`
- `LOCAL_ENVIRONMENTS.md`
- `.mcp.json`
- `config/app.yaml.example`
- `secrets/confluence.yaml.example`

Причина:

- документы компактные
- структура важнее, чем локальные куски
- часто читаются как единое целое

### Резать на чанки

Нужно чанкование для:

- больших Python-файлов
- экспортёров / импортёров markdown
- сервисных модулей
- transport API файлов

Особенно:

- `confluence_markdown_service/exporter.py`
- `confluence_markdown_service/importer.py`
- `confluence_mcp/api.py`
- `confluence_mcp/mcp_server.py`
- `confluence_pagecreator_service/service.py`

## 4. Какие сущности лучше индексировать отдельно

### 4.1 MCP tools

Каждый tool должен быть отдельной retrieval-единицей:

- имя tool
- описание
- аргументы
- вызываемый service method
- ограничения

### 4.2 HTTP endpoints

Каждый endpoint — отдельная retrieval-единица:

- метод
- путь
- request schema
- response schema
- связанный сценарий

### 4.3 Сервисные сценарии

Отдельно индексировать:

- `plan_pages`
- `create_pages`
- `export_page_to_markdown`
- `create_page_from_markdown`
- `update_page_from_markdown`
- file-based markdown operations

### 4.4 Runtime / deployment блоки

Отдельные сущности:

- local HTTP runtime
- MCP stdio runtime
- MCP HTTP runtime
- Docker launch modes

### 4.5 Known issues / ограничения

Отдельно индексировать:

- поиск по `title + space_key` без `parent`
- lossy export unknown macros
- file import attachment name collisions

Это очень полезно при ответах на вопросы “почему так работает”.

## 5. Размер чанков

Для этого проекта достаточно практичной схемы:

### Код

- 80–180 строк на чанк
- стараться не разрывать функцию или класс

### Документация

- 1–3 раздела markdown
- не резать пополам пример команды и её объяснение

### Конфиги

- целиком, если файл короткий
- по логическим секциям, если файл вырастет

## 6. Какие метаданные хранить для каждого чанка

Минимальный набор:

- `repository`
- `package`
- `module`
- `path`
- `entity_type`
- `entity_name`
- `layer`
- `audience`
- `capability_tags`
- `runtime_tags`
- `source_kind`

### Примеры `entity_type`

- `mcp_tool`
- `http_endpoint`
- `service_method`
- `client_method`
- `dto`
- `config_schema`
- `doc_section`
- `known_issue`

### Примеры `layer`

- `client`
- `service`
- `transport`
- `runtime`
- `documentation`

### Примеры `capability_tags`

- `page_creation`
- `page_search`
- `page_read`
- `markdown_export`
- `markdown_import`
- `docker`
- `mcp`
- `http_api`

## 7. Как организовать поиск

### 7.1 Keyword search

Нужен для:

- точных путей
- имен tools
- имен endpoints
- config keys
- env vars

Примеры запросов:

- `PAGECREATOR_RUNTIME_MODE`
- `plan_pages`
- `POST /api/v1/page/markdown/create`

### 7.2 Семантический поиск

Нужен для:

- “как публиковать markdown в confluence”
- “где обрабатываются неизвестные макросы”
- “как работает docker запуск”

### 7.3 Symbol / code-aware search

Нужен для:

- функций
- классов
- dataclass / pydantic моделей
- точек вызова

Примеры:

- `load_runtime_service`
- `create_page_from_markdown_file`
- `render_plan_structure`

### 7.4 Search by capability

Полезно поддерживать отдельный слой поиска по возможностям:

- page creator
- markdown bridge
- runtime / docker
- auth / config

### 7.5 Search by dependency / graph

Особенно полезно для вопросов вида:

- “какой service вызывается из этого endpoint”
- “какой client method используется этим tool”
- “какие модули затрагивает markdown import”

## 8. Как организовать многоступенчатый retrieval

Для этого проекта лучше использовать простую и стабильную каскадную схему.

### Шаг 1. Определить область вопроса

Определить, запрос относится к:

- page creator
- markdown bridge
- transport/API
- runtime/docker
- config/auth

### Шаг 2. Выбрать пакет

Например:

- `confluence-markdown-service`
- `confluence-pagecreator-service`
- `confluence-mcp-server`

### Шаг 3. Выбрать модуль

Например:

- `importer.py`
- `api.py`
- `runtime.py`

### Шаг 4. Выбрать сущность

Например:

- конкретный endpoint
- конкретный tool
- конкретную функцию

### Шаг 5. Добрать supporting docs

Только потом, при необходимости:

- `README.md`
- `EXTERNAL_CONSUMERS.md`
- `DOCKER_RUN.md`

## 9. Как избежать переполнения контекста

Не стоит сразу читать:

- весь `README.md`
- все service-файлы
- все transport-файлы
- все docs вместе

Лучше стратегия:

1. сначала определить capability
2. потом 1–2 ключевых модуля
3. потом 1 supporting document
4. только если не хватает — расширять контекст

### Хороший пример

Запрос:

- “Как обновить страницу из markdown-файла?”

Сначала читать:

- `confluence_markdown_service/importer.py`
- `confluence_mcp/api.py`

И только затем:

- `README.md` или `EXTERNAL_CONSUMERS.md`

## 10. Как агенту решать, что читать, а что нет

### Читать в первую очередь

- модуль, где находится требуемый use case
- transport-слой, если вопрос про внешний API
- config/runtime, если вопрос про запуск
- docs, если вопрос от внешнего потребителя

### Не читать без необходимости

- `tmp/`
- `.venv*`
- бинарные или архивные файлы
- старые или дублирующие артефакты

## 11. Как поддерживать индекс актуальным

Автоматически обновлять при изменениях:

- Python code
- docs
- launcher scripts
- Dockerfile
- config examples

Можно реже обновлять:

- ограничения
- архитектурные заметки
- knowledge model docs

## 12. Что должно обновляться автоматически, а что вручную

### Автоматически

- список файлов
- модули / функции / классы
- tools / endpoints
- config schema
- env variables
- зависимости между пакетами

### Вручную или полуавтоматически

- ограничения и known issues
- workaround'ы
- описания capabilities
- рекомендации по использованию для внешних потребителей

## 13. Итоговая архитектура retrieval

Практическая схема для этого проекта:

```text
Git / Workspace
  -> File Discovery
  -> Entity Extraction
     -> packages
     -> modules
     -> tools
     -> endpoints
     -> service scenarios
     -> config schemas
     -> docs
  -> Knowledge Base
     -> structural layer
     -> code layer
     -> capability layer
     -> docs layer
     -> constraint layer
  -> Retrieval
     -> capability classification
     -> package selection
     -> module selection
     -> entity retrieval
     -> supporting docs
  -> AI Agent
```

## 14. Минимально достаточный индекс

Если хочется стартовать с минимального, но уже полезного слоя, достаточно индексировать:

- `README.md`
- `EXTERNAL_CONSUMERS.md`
- `DOCKER_RUN.md`
- `confluence_mcp/api.py`
- `confluence_mcp/mcp_server.py`
- `confluence_mcp/runtime.py`
- `confluence_client/client.py`
- `confluence_pagecreator_service/service.py`
- `confluence_markdown_service/exporter.py`
- `confluence_markdown_service/importer.py`
- known issues из `README.md`

Этого уже достаточно, чтобы агент:

- понимал возможности сервера
- умел отвечать про запуск
- находил точки изменения для page creation и markdown bridge
- не путался между transport и service слоями
