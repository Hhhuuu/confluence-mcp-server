# Технический долг Confluence MCP Server

Документ фиксирует уже накопившийся технический долг по проекту
`confluence-mcp-server` и помогает планировать следующие итерации
без потери контекста.

Дата актуализации: 2026-07-17

## Приоритеты

- `P1` — важно закрывать в ближайших итерациях, иначе стоимость изменений будет быстро расти
- `P2` — желательно закрыть после стабилизации основных сценариев
- `P3` — улучшения качества и сопровождения, которые не блокируют развитие прямо сейчас

## P1

### 1. Разделить `importer.py` на специализированные модули

Почему это долг:

- файл стал слишком большим
- в нём смешаны разные уровни ответственности
- новые HTML- и Confluence-элементы продолжают добавляться именно сюда

Текущая точка:

- [importer.py](/Users/mamapapa/work/projects-old/UFS_PLUGINS/confluence-mcp-server/confluence-markdown-service/src/confluence_markdown_service/importer.py)

Что сейчас внутри:

- markdown -> xhtml
- upload attachments
- html sanitization
- transform дерева
- обработка `img`, `a`, `input`, `details`, `summary`
- warnings и fallback-логика

Что сделать:

1. Вынести `html_sanitizer.py`
2. Вынести `attachment_resolver.py`
3. Вынести `tree_transformer.py`
4. Вынести `inline_import_handlers.py`

Почему важно сейчас:

- дальше любое новое расширение будет повышать риск регрессий
- файл уже тяжело безопасно читать и менять

### 2. Разделить `storage_renderer.py` на block/inline/table renderer

Почему это долг:

- файл стал вторым перегруженным центром логики
- в нём уже смешаны renderer, fallback, macro handling и table strategies

Текущая точка:

- [storage_renderer.py](/Users/mamapapa/work/projects-old/UFS_PLUGINS/confluence-mcp-server/confluence-markdown-service/src/confluence_markdown_service/storage_renderer.py)

Что сейчас внутри:

- общий document render
- block render
- macro render
- inline render
- image/link render
- fallback
- table strategies `auto`, `markdown`, `html`

Что сделать:

1. Вынести `table_renderer.py`
2. Вынести `inline_renderer.py`
3. Вынести `macro_renderer.py`
4. Оставить в `storage_renderer.py` orchestration-слой

Почему важно сейчас:

- таблицы и новые inline-элементы будут дальше раздувать сложность
- без разбиения тяжело тестировать частями

### 3. Добавить полноценные roundtrip-тесты для markdown bridge

Почему это долг:

- проект уже держится на заметном количестве эвристик
- ручные live-проверки полезны, но не заменяют автоматические тесты

Критичные сценарии:

- `toc`
- `admonitions`
- `code_blocks`
- `date_element`
- `status_element`
- `jira_links`
- attachments bundle
- unknown html sanitization
- `table_mode=auto|markdown|html`

Что сделать:

1. Snapshot tests для `markdown -> storage`
2. Snapshot tests для `storage -> markdown`
3. Roundtrip tests для ключевых кейсов

Почему важно сейчас:

- каждое следующее расширение повышает риск незаметной поломки старых сценариев

### 4. Формализовать export/import options в единые объекты

Почему это долг:

- параметры начинают расползаться по нескольким слоям
- уже есть риск забыть протащить новый флаг через один из transport-слоёв

Текущие параметры:

- `enabled_extensions`
- `table_mode`

Зоны:

- [exporter.py](/Users/mamapapa/work/projects-old/UFS_PLUGINS/confluence-mcp-server/confluence-markdown-service/src/confluence_markdown_service/exporter.py)
- [api.py](/Users/mamapapa/work/projects-old/UFS_PLUGINS/confluence-mcp-server/confluence-mcp-server/src/confluence_mcp/api.py)
- [mcp_server.py](/Users/mamapapa/work/projects-old/UFS_PLUGINS/confluence-mcp-server/confluence-mcp-server/src/confluence_mcp/mcp_server.py)

Что сделать:

1. Завести `MarkdownExportOptions`
2. Завести `MarkdownImportOptions`
3. Передавать объекты опций между слоями вместо набора разрозненных аргументов

Почему важно сейчас:

- это снизит дублирование
- это упростит дальнейшее развитие API и MCP

## P2

### 5. Централизовать правила HTML sanitization

Почему это долг:

- whitelist атрибутов уже появился и дальше будет расти
- сейчас это просто словарь в середине импортера

Текущая точка:

- [importer.py](/Users/mamapapa/work/projects-old/UFS_PLUGINS/confluence-mcp-server/confluence-markdown-service/src/confluence_markdown_service/importer.py)

Что сделать:

1. Вынести правила в `html_policy.py`
2. Описать, какие атрибуты и почему разрешены
3. Разделить allowlist для обычного HTML и для внутренних bridge-элементов

Почему это важно:

- иначе политика очистки станет набором “магических” исключений

### 6. Централизовать Confluence-specific mapping rules

Почему это долг:

- знания о Confluence сейчас распределены по расширениям и рендерам
- при росте числа элементов сопровождать это станет всё сложнее

Примеры таких знаний:

- status macro
- date element
- jira links
- attachment resources
- fallback для макросов

Что сделать:

1. Завести `confluence_semantics.py` или аналогичный модуль
2. Хранить там централизованные mapping tables и policy-решения

Почему это важно:

- это упростит поддержку новых элементов, например `expand`, `mention`, `task-list`

### 7. Улучшить fallback для неизвестных макросов и HTML

Почему это долг:

- текущий fallback уже полезен, но всё ещё довольно грубый
- иногда лучше сохранить HTML-блок, чем схлопнуть всё в plain text

Что сделать:

1. Ввести режимы fallback:
   - `text`
   - `html`
   - `drop`
2. Добавить их хотя бы на уровне export options

Почему это важно:

- особенно полезно для нестандартных макросов и тяжёлых таблиц

### 8. Унифицировать warnings

Почему это долг:

- предупреждения сейчас формируются строками “по месту”
- их неудобно анализировать и стабильно проверять в тестах

Что сделать:

1. Ввести коды предупреждений
2. Оставить человекочитаемый текст как `message`
3. Примеры кодов:
   - `HTML_ATTR_STRIPPED`
   - `TABLE_EXPORTED_AS_HTML`
   - `UNKNOWN_MACRO_FLATTENED`
   - `ATTACHMENT_NOT_FOUND`

Почему это важно:

- будет проще анализировать проблемы
- будет проще писать устойчивые тесты

## P3

### 9. Обновить документацию под реальное текущее поведение

Почему это долг:

- функциональность bridge сильно выросла
- документация уже начала отставать от реальности

Что уже нужно явно описать:

- `date_element`
- `status_element`
- HTML sanitization
- `table_mode`
- поведение `auto`
- ограничения markdown tables

Файлы:

- [EXTENSIONS.md](/Users/mamapapa/work/projects-old/UFS_PLUGINS/confluence-mcp-server/EXTENSIONS.md)
- [EXTERNAL_CONSUMERS.md](/Users/mamapapa/work/projects-old/UFS_PLUGINS/confluence-mcp-server/EXTERNAL_CONSUMERS.md)
- [MCP_CONNECTION_GUIDE.md](/Users/mamapapa/work/projects-old/UFS_PLUGINS/confluence-mcp-server/MCP_CONNECTION_GUIDE.md)

Почему это важно:

- иначе внешние пользователи будут работать “по памяти”, а не по актуальному контракту

### 10. Разнести диагностические и live-check скрипты в отдельную структуру

Почему это долг:

- в `tmp/` уже накопились полезные, но разнородные артефакты
- сейчас они не отделены от временных файлов и ручных экспериментов

Что сделать:

1. Выделить `devtools/` или `scripts/manual_checks/`
2. Разнести `fixtures/`, `live_checks/`, `smoke/`
3. Явно отделить одноразовые файлы от поддерживаемых служебных сценариев

Почему это важно:

- будет проще поддерживать ручные проверки и онбордить новых разработчиков

### 11. Нормализовать transport layer между HTTP API и MCP

Почему это долг:

- логика похожа, но transport-слои дублируют обвязку
- со временем это почти неизбежно начнёт расходиться

Текущие точки:

- [api.py](/Users/mamapapa/work/projects-old/UFS_PLUGINS/confluence-mcp-server/confluence-mcp-server/src/confluence_mcp/api.py)
- [mcp_server.py](/Users/mamapapa/work/projects-old/UFS_PLUGINS/confluence-mcp-server/confluence-mcp-server/src/confluence_mcp/mcp_server.py)

Что сделать:

1. Вынести shared application service layer для markdown/pagecreator операций
2. Оставить в HTTP API и MCP только transport-адаптацию

Почему это важно:

- это снизит дублирование
- это уменьшит риск расхождения поведения между HTTP и MCP

## Рекомендуемый порядок работ

Если делать по шагам, я бы рекомендовал такой порядок:

1. Разделить `importer.py`
2. Разделить `storage_renderer.py`
3. Добавить roundtrip-тесты
4. Ввести единые `options`-объекты
5. Унифицировать warnings через коды

## Короткий вывод

Главный текущий техдолг проекта не в “плохом коде”, а в том, что
markdown bridge очень быстро вырос из простого конвертера в систему правил,
эвристик и расширений.

Это хороший этап развития, но теперь проекту нужен следующий шаг:

- формализация политики
- разбиение по модулям
- автоматические тесты
- выравнивание transport-слоёв и документации
