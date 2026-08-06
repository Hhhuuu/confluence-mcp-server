# Confluence MCP Server: Модель знаний проекта

## 1. Назначение

Этот документ описывает, какие знания об этом проекте должны быть собраны, чтобы AI-агент мог:

- быстро ориентироваться в кодовой базе
- понимать границы модулей
- выбирать нужный слой для изменений
- находить точки интеграции с Confluence
- понимать ограничения и риски
- отвечать на вопросы о возможностях сервера

Документ не описывает конкретные технологии хранения. Его задача — зафиксировать структуру знаний.

## 2. Границы проекта

`confluence-mcp-server` — это Python-проект, который предоставляет:

- HTTP API
- MCP transport
- клиент для Confluence REST API
- сервис создания иерархий страниц
- сервис экспорта и импорта Markdown
- нативные launcher-скрипты для Windows, Linux и macOS

Проект включает несколько внутренних пакетов:

- `confluence-client`
- `confluence-pagecreator-service`
- `confluence-markdown-service`
- `confluence-mcp-server`

## 3. Основные сущности

### 3.1 Репозиторий

Примеры:

- `confluence-mcp-server`

Обязательные атрибуты:

- имя
- путь
- назначение
- основной язык
- статус
- основные пакеты / модули
- основные документы

Связи:

- содержит пакеты
- содержит документацию
- содержит конфигурацию
- содержит точки входа

Частота изменений:

- редко

Автоизвлечение:

- да

### 3.2 Пакет / модуль верхнего уровня

Примеры:

- `confluence-client`
- `confluence-pagecreator-service`
- `confluence-markdown-service`
- `confluence-mcp-server`

Обязательные атрибуты:

- имя
- путь
- роль
- зависимости
- публичный API

Связи:

- принадлежит репозиторию
- зависит от других пакетов
- содержит Python-модули

Частота изменений:

- средняя

Автоизвлечение:

- да

### 3.3 Python-модуль

Примеры:

- `client.py`
- `service.py`
- `api.py`
- `mcp_server.py`
- `runtime.py`

Обязательные атрибуты:

- имя
- путь
- пакет
- роль
- основные публичные функции / классы

Связи:

- принадлежит пакету
- импортирует другие модули
- определяет классы, функции, DTO

Частота изменений:

- средняя / высокая

Автоизвлечение:

- да

### 3.4 Сервисный сценарий

Примеры:

- `plan_pages`
- `create_pages`
- `export_page_to_markdown`
- `create_page_from_markdown`
- `update_page_from_markdown`

Обязательные атрибуты:

- имя сценария
- входные данные
- выходные данные
- вызываемый пакет
- побочные эффекты
- ограничения

Связи:

- реализуется сервисным модулем
- публикуется через HTTP API
- публикуется через MCP tool
- использует Confluence client

Частота изменений:

- средняя

Автоизвлечение:

- частично

### 3.5 HTTP endpoint

Примеры:

- `GET /health`
- `POST /api/v1/plan`
- `GET /api/v1/page/{page_id}/markdown`
- `POST /api/v1/page/markdown/update-file`

Обязательные атрибуты:

- метод
- путь
- назначение
- request schema
- response schema
- вызываемый use case

Связи:

- принадлежит `confluence_mcp.api`
- ссылается на сервисный сценарий

Частота изменений:

- средняя

Автоизвлечение:

- частично

### 3.6 MCP tool

Примеры:

- `show_runtime_config`
- `get_current_user`
- `find_page`
- `plan_pages`
- `create_pages`
- `export_page_to_markdown`
- `create_page_from_markdown`

Обязательные атрибуты:

- имя
- описание
- входные аргументы
- выход
- сценарий использования

Связи:

- принадлежит `confluence_mcp.mcp_server`
- вызывает сервисный сценарий

Частота изменений:

- средняя

Автоизвлечение:

- да

### 3.7 Модель данных / DTO

Примеры:

- модели клиента Confluence
- DTO page creator
- DTO markdown bridge

Обязательные атрибуты:

- имя
- поля
- слой
- сериализация / формат

Связи:

- используется сервисами
- используется HTTP API
- используется MCP tools

Частота изменений:

- средняя

Автоизвлечение:

- да

### 3.8 Конфигурация

Примеры:

- `config/app.yaml`
- `config/app.yaml.example`
- `secrets/confluence.yaml`
- `.mcp.json`
- переменные окружения launcher-скриптов

Обязательные атрибуты:

- путь
- тип
- обязательные поля
- примеры значений
- чувствительность данных

Связи:

- используется runtime
- влияет на transport и client

Частота изменений:

- редкая

Автоизвлечение:

- частично

### 3.9 Runtime режим

Примеры:

- `http-api`
- `mcp-http`
- `mcp-stdio`

Обязательные атрибуты:

- имя режима
- точка входа
- необходимые env variables
- используемый transport

Связи:

- принадлежит `confluence_mcp.launch`
- используется локальными launcher-скриптами

Частота изменений:

- редкая

Автоизвлечение:

- да

### 3.10 Внешняя система

Примеры:

- `Confluence Cloud`
- `Confluence Server / Data Center`

Обязательные атрибуты:

- тип системы
- режим подключения
- auth modes
- ключевые ограничения API

Связи:

- используется клиентом
- влияет на конфигурацию
- влияет на markdown bridge и page creation

Частота изменений:

- средняя

Автоизвлечение:

- нет, в основном документируется вручную

### 3.11 Ограничение / известный риск

Примеры:

- поиск страницы сейчас идёт по `title + space_key` без проверки `parent`
- неизвестные Confluence-блоки экспортируются в markdown в режиме `best effort`

Обязательные атрибуты:

- формулировка ограничения
- затронутый модуль
- влияние на пользователя
- возможный workaround

Связи:

- относится к сервисному сценарию
- относится к transport или export/import логике

Частота изменений:

- редкая

Автоизвлечение:

- нет

### 3.12 Документ проекта

Примеры:

- `README.md`
- `EXTERNAL_CONSUMERS.md`
- `MCP_CONNECTION_GUIDE.md`
- `LOCAL_ENVIRONMENTS.md`
- `MARKDOWN_BRIDGE_PLAN.md`

Обязательные атрибуты:

- путь
- тема
- аудитория
- актуальность

Связи:

- описывает репозиторий, пакеты, runtime, сценарии

Частота изменений:

- средняя

Автоизвлечение:

- частично

## 4. Разделение знаний по типу изменяемости

### 4.1 Статические знания

Это то, что меняется редко и задаёт каркас проекта:

- структура репозитория
- список верхнеуровневых пакетов
- роль каждого пакета
- основные runtime режимы
- базовая схема конфигурации
- типы интеграций с Confluence

### 4.2 Редко изменяемые знания

- публичные HTTP endpoints
- список MCP tools
- список основных DTO
- основные ограничения и known issues
- Python launcher-схемы для поддерживаемых ОС
- docs для внешних потребителей

### 4.3 Динамические знания

- конкретные `space_key`, `page_id`, test pages
- пользовательские секреты
- локальные env paths
- временные smoke-test файлы
- состояние текущей рабочей ветки

## 5. Архитектурные знания

Агенту нужно знать:

- что transport отделён от service layer
- что `confluence-client` не должен содержать бизнес-логику
- что `confluence-pagecreator-service` отвечает только за иерархии страниц
- что `confluence-markdown-service` отвечает только за markdown bridge
- что `confluence-mcp-server` — тонкий слой публикации HTTP API и MCP

Также нужны знания о runtime:

- как локальный launcher находит конфиг и секреты
- как launch-скрипты проверяют и запускают Python 3.10+
- как `.mcp.json` подключает сервер

## 6. Знания о коде

Агенту нужно знать:

- где лежат точки входа
- где находится Confluence REST client
- где реализован path parsing
- где реализован planner
- где реализован export/import markdown
- где находятся request/response схемы API
- где находятся MCP tools

Минимальная навигационная карта:

- `confluence-client/src/confluence_client/client.py`
- `confluence-pagecreator-service/src/confluence_pagecreator_service/service.py`
- `confluence-markdown-service/src/confluence_markdown_service/exporter.py`
- `confluence-markdown-service/src/confluence_markdown_service/importer.py`
- `confluence-mcp-server/src/confluence_mcp/api.py`
- `confluence-mcp-server/src/confluence_mcp/mcp_server.py`
- `confluence-mcp-server/src/confluence_mcp/runtime.py`
- `confluence-mcp-server/src/confluence_mcp/launch.py`

## 7. Знания о бизнес-логике

Для этого проекта бизнес-логика выражена не доменом компании, а сценариями работы с Confluence:

- создание иерархий страниц по path
- поиск и чтение страниц
- экспорт страниц в markdown
- публикация markdown в Confluence
- управление файлами и вложениями при markdown file flows

Агент должен знать:

- как path превращается в дерево уровней
- как markdown bridge intentionally lossy на неизвестных блоках
- как file-based import загружает вложения
- какие ограничения есть у roundtrip

## 8. Знания о процессах разработки

Агенту нужно знать:

- как поднимать `.venv` и `.venv-mcp`
- как делать editable installs
- как запускать API локально
- как запускать MCP локально
- как устанавливать и обновлять окружение Python 3.10+
- какие документы считать основными при онбординге внешнего потребителя

## 9. Минимальный набор данных, достаточный для ориентации

Если собран только минимальный набор, агент уже сможет работать осмысленно:

1. Имя и назначение репозитория
2. Список верхнеуровневых пакетов и их роли
3. Точки входа:
   - HTTP API
   - MCP
   - Windows и Unix launcher
4. Основные сценарии:
   - page creation
   - page read/search
   - markdown export/import
5. Конфиг:
   - `config/app.yaml`
   - `secrets/confluence.yaml`
6. Список MCP tools
7. Список HTTP endpoints
8. Ключевые ограничения
9. Основные документы:
   - `README.md`
   - `EXTERNAL_CONSUMERS.md`
   - `MCP_CONNECTION_GUIDE.md`
   - `LOCAL_ENVIRONMENTS.md`

## 10. Итоговая структура базы знаний проекта

Ниже — практическая структура знаний, которую можно поддерживать в актуальном состоянии.

### 10.1 Repository layer

- repository
- documents
- runtime modes
- configuration files

### 10.2 Package layer

- package
- role
- dependencies
- public modules

### 10.3 Code layer

- modules
- classes
- functions
- DTO/models
- imports

### 10.4 Capability layer

- HTTP endpoints
- MCP tools
- service scenarios
- external operations against Confluence

### 10.5 Constraint layer

- known issues
- lossy conversions
- auth / deployment caveats
- operational warnings

### 10.6 Operations layer

- local run instructions
- native Python run instructions
- archive/deploy instructions

## 11. Что можно поддерживать автоматически

Хорошо извлекается автоматически:

- структура репозитория
- список пакетов
- модули, классы, функции
- импорты и зависимости
- endpoints и MCP tools
- config schema из кода

Лучше поддерживать вручную или полуавтоматически:

- архитектурные ограничения
- known issues
- workaround'ы
- описание сценариев для внешних потребителей
- смысловые роли модулей
