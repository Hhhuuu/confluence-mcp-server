# План развития Markdown Bridge

Этот документ фиксирует поэтапный план добавления двух новых возможностей:

1. `Confluence -> Markdown`
2. `Markdown -> Confluence`

Документ нужен как опорная точка для продолжения работ, даже если текущий контекст диалога будет потерян.

## 1. Цель

Добавить в `confluence-mcp-server` простой и предсказуемый мост между страницами Confluence и Markdown-файлами.

Ключевой принцип:

- мы сознательно поддерживаем не весь Confluence Storage Format, а только тексто-ориентированный поднабор
- допускаются потери Confluence-макросов и сложных визуальных конструкций
- приоритет: читаемый Markdown на выходе и предсказуемая публикация Markdown в Confluence

## 2. Границы v1

### Поддерживаем в `Confluence -> Markdown`

- заголовки
- абзацы
- маркированные списки
- нумерованные списки
- цитаты
- жирный текст
- курсив
- inline code
- code blocks
- ссылки
- горизонтальные линии
- таблицы, если можно стабильно извлечь без сильной деградации
- изображения как markdown-ссылки или markdown image

### Поддерживаем в `Markdown -> Confluence`

- `#` заголовки
- абзацы
- маркированные и нумерованные списки
- `> quote`
- `**bold**`
- `*italic*`
- `` `inline code` ``
- fenced code blocks
- ссылки
- изображения
- горизонтальные линии
- таблицы, если итоговый HTML стабильно принимается Confluence

### Осознанно не гарантируем в v1

- сохранение макросов Atlassian
- сохранение layout/колонок
- сохранение include/excerpt/jira/app-specific blocks
- визуально точный round-trip
- поддержку произвольного embedded HTML внутри Markdown
- полную обратимость `Confluence -> Markdown -> Confluence`

## 3. Ключевые ограничения

Confluence хранит тело страницы не как обычный HTML, а как `storage format` на основе XHTML/XML с собственными тегами и макросами.

Следствие:

- `Confluence -> Markdown` нельзя строить как прямой `storage -> html2text`
- сначала нужен этап нормализации storage-разметки
- `Markdown -> Confluence` тоже не должен быть просто `markdown -> html -> publish`, без контроля итоговой структуры

## 4. Предлагаемая архитектура

### Новый пакет или модульный блок

Рекомендуемая структура внутри текущего проекта:

```text
pagecreator-service/src/pagecreator_service/
  markdown_bridge/
    __init__.py
    models.py
    exporter.py
    importer.py
    storage_normalizer.py
    storage_renderer.py
    markdown_extensions.py
    exceptions.py
```

### Зоны ответственности

- `exporter.py`
  - orchestration для `Confluence -> Markdown`
- `importer.py`
  - orchestration для `Markdown -> Confluence`
- `storage_normalizer.py`
  - преобразование `body.storage` в упрощенный HTML-поднабор
- `storage_renderer.py`
  - сборка Confluence storage из HTML/Markdown pipeline
- `markdown_extensions.py`
  - кастомные расширения вроде `[TOC]`
- `models.py`
  - DTO и служебные структуры результата

## 5. Этап 1. Confluence -> Markdown

Это первый этап, с которого начинаем реализацию.

### 5.1. Цель этапа

Научиться забирать страницу Confluence и получать читаемый Markdown с сохранением базовой структуры текста.

### 5.2. Предлагаемый pipeline

1. Получить страницу через `confluence_client.find_page_by_id_with_storage(...)`
2. Извлечь `body.storage.value`
3. Распарсить storage-разметку
4. Нормализовать Confluence-specific элементы в обычный HTML-поднабор
5. Преобразовать нормализованный HTML в Markdown
6. Вернуть Markdown и метаданные страницы

### 5.3. Минимальный API сервисного слоя

Рекомендуемые методы:

- `export_page_to_markdown(page_id: str) -> MarkdownExportResult`
- `export_page_tree_to_markdown(root_page_id: str, recursive: bool = False) -> list[MarkdownExportResult]`

### 5.4. Структура результата

Пример DTO:

```python
class MarkdownExportResult(BaseModel):
    page_id: str
    title: str
    space_key: str | None = None
    markdown: str
    warnings: list[str] = []
```

### 5.5. Что нужно нормализовать в первую очередь

- `h1..h6` как заголовки
- `p` как абзацы
- `ul/ol/li` как списки
- `strong/em/code/pre` как базовое форматирование
- `a` как ссылки
- `ac:link` и похожие ссылки в обычный HTML link
- `ri:attachment` и `ri:url` в ссылки или картинки

### 5.6. Что делаем с макросами

Поведение v1:

- неизвестные макросы отбрасываем
- по желанию добавляем предупреждение в `warnings`

Пример warning:

- `Макрос ac:structured-macro(name=jira) был пропущен при экспорте.`

### 5.7. Техническое решение по конвертации HTML -> Markdown

Есть два варианта:

1. использовать `html2text`
2. написать упрощенный свой renderer для нужного HTML-поднабора

На текущий момент для прототипа допускается `html2text`, но нужно отдельно зафиксировать лицензионный риск:

- `html2text` на PyPI распространяется под `GPL-3.0-or-later`

Перед включением в итоговую поставку это решение нужно подтвердить отдельно.

Если GPL нежелателен, тогда:

- либо ищем альтернативу
- либо пишем свой ограниченный renderer под наш HTML-поднабор

### 5.8. Definition of Done для этапа 1

- можно выгрузить страницу по `page_id`
- на выходе читаемый Markdown
- заголовки, списки, ссылки и code blocks не теряются
- неизвестные макросы не валят обработку
- есть warnings по потерянным элементам
- есть unit-тесты на базовые кейсы

## 6. Этап 2. Markdown -> Confluence

Этот этап начинаем после завершения экспорта.

### 6.1. Цель этапа

Научиться брать Markdown и публиковать его в Confluence как страницу или обновление существующей страницы.

### 6.2. Предлагаемый pipeline

1. Принять Markdown
2. Преобразовать Markdown в HTML
3. Применить кастомные расширения и пост-обработку
4. Преобразовать HTML в безопасный storage-поднабор
5. Создать или обновить страницу через `body.storage`

### 6.3. Минимальный API сервисного слоя

- `create_page_from_markdown(...)`
- `update_page_from_markdown(...)`
- `preview_markdown_to_storage(markdown_text: str) -> str`

Пример:

```python
create_page_from_markdown(
    title: str,
    markdown_text: str,
    parent_id: str,
    space_key: str,
) -> PageData
```

### 6.4. Custom extension v1

Поддержать специальный токен:

- `[TOC]`

Или альтернативно:

- `[[TOC]]`

Рекомендуется выбрать один вариант и использовать его консистентно.

На этапе импорта он должен заменяться на Confluence TOC macro в storage-разметке.

### 6.5. Что делать с unsupported Markdown

Если встречается Markdown-конструкция вне поддерживаемого набора:

- либо сохраняем ее как обычный текст
- либо возвращаем warning

Но не должны падать без крайней необходимости.

### 6.6. Definition of Done для этапа 2

- можно создать страницу из Markdown
- можно обновить страницу из Markdown
- базовые элементы Markdown публикуются в ожидаемом виде
- `[TOC]` преобразуется в macro оглавления
- есть preview режима `markdown -> storage`
- есть unit-тесты и как минимум один интеграционный тест на реальном Confluence

## 7. MCP и HTTP API

После появления сервисного слоя можно добавить инструменты:

### MCP tools

- `export_page_to_markdown`
- `export_page_tree_to_markdown`
- `create_page_from_markdown`
- `update_page_from_markdown`
- `preview_markdown_to_storage`

### HTTP endpoints

- `GET /api/v1/page/{page_id}/markdown`
- `POST /api/v1/page/markdown/create`
- `POST /api/v1/page/markdown/update`
- `POST /api/v1/page/markdown/preview`

## 8. Тестовый план

### Для `Confluence -> Markdown`

- простой текст
- вложенные заголовки
- списки
- ссылки
- code block
- таблица
- страница с макросом, который должен быть проигнорирован

### Для `Markdown -> Confluence`

- заголовки
- списки
- ссылки
- code block
- таблица
- `[TOC]`
- пустой документ
- документ с unsupported-элементом

## 9. Открытые решения

Перед реализацией или в ходе реализации нужно принять решения по следующим вопросам:

1. Используем ли `html2text`, учитывая лицензию GPL.
2. Нужна ли поддержка таблиц в v1 или лучше перенести их в v1.1.
3. Как именно представлять картинки при экспорте:
   - markdown image
   - обычная ссылка
4. Как обозначать потерянные макросы:
   - просто пропускать
   - оставлять HTML comment
   - собирать warnings
5. Какой токен использовать для оглавления:
   - `[TOC]`
   - `[[TOC]]`

## 10. Рекомендуемый порядок реализации

1. Создать `markdown_bridge/` модульную структуру
2. Реализовать модели результата и исключения
3. Реализовать `export_page_to_markdown`
4. Добавить unit-тесты на экспорт
5. Добавить HTTP endpoint для экспорта
6. Проверить экспорт на реальных страницах Confluence
7. Реализовать `preview_markdown_to_storage`
8. Реализовать `create_page_from_markdown`
9. Реализовать `update_page_from_markdown`
10. Добавить `[TOC]`
11. Подключить MCP tools

## 11. Что считаем успешным результатом первой итерации

Первая итерация считается успешной, если:

- можно выгрузить реальную страницу Confluence в читаемый Markdown
- можно взять обычный Markdown-документ и опубликовать его как страницу
- заголовки, списки, ссылки и code blocks сохраняются в обе стороны
- макросы не блокируют экспорт, даже если теряются
- ограничения честно задокументированы
