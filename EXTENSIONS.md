# Расширения Markdown Bridge для Confluence

## Назначение

`Confluence Markdown Bridge` поддерживает систему расширений, которая позволяет
добавлять специальные markdown-конструкции и отображать их в Confluence через
native macro и storage format.

Расширения подключаются **опционально**:

- через Python API
- через HTTP API
- через MCP tools

Базовый markdown bridge продолжает работать и без них.

## Встроенные расширения

### 1. `toc`

Назначение:

- поддержка `[TOC]`, `[[TOC]]` и `[TOC maxLevel=3]`

Что делает:

- Markdown -> Confluence: превращает маркер в `toc` macro
- если указан `maxLevel`, добавляет внутрь `ac:structured-macro` дочерний элемент `ac:parameter ac:name="maxLevel"`
- Confluence -> Markdown: возвращает `[TOC]` или `[TOC maxLevel=...]`

Пример:

```md
[TOC]

[TOC maxLevel=3]
```

### 2. `admonitions`

Назначение:

- поддержка информационных и предупреждающих блоков

Поддерживаемый синтаксис:

```md
> [!NOTE]
> Текст справки

> [!INFO]
> Информационный блок

> [!TIP]
> Подсказка

> [!WARNING]
> Важное предупреждение

> [!ERROR]
> Ошибка или критичное замечание
```

Что делает:

- Markdown -> Confluence:
  - `NOTE` -> `note`
  - `INFO` -> `info`
  - `TIP` -> `tip`
  - `WARNING` -> `warning`
  - `ERROR` -> `panel` с красным оформлением
- Confluence -> Markdown:
  - известные macro возвращаются обратно в markdown admonition syntax

### 3. `code_blocks`

Назначение:

- поддержка code block с заголовком и языком

Поддерживаемый синтаксис:

````md
```python {title="example.py"}
print("hello")
```
````

Что делает:

- Markdown -> Confluence:
  - language -> параметр `language`
  - title -> параметр `title`
  - создаётся `code` macro
- Confluence -> Markdown:
  - `code` macro с title и language возвращается в fenced code block

## Как включить расширения

### Через Python API

```python
from confluence_markdown_service import ConfluenceMarkdownImporter

importer = ConfluenceMarkdownImporter(
    client,
    enabled_extensions=["toc", "admonitions", "code_blocks"],
)
```

Для экспорта:

```python
from confluence_markdown_service import ConfluenceMarkdownExporter

exporter = ConfluenceMarkdownExporter(
    client,
    enabled_extensions=["toc", "admonitions", "code_blocks"],
)
```

### Через HTTP API

Preview markdown:

```json
{
  "markdown": "> [!WARNING]\n> Важное предупреждение",
  "enabled_extensions": ["admonitions"]
}
```

Создание страницы из markdown:

```json
{
  "title": "Runbook",
  "parent_id": "12345",
  "space_key": "DOC",
  "markdown": "```python {title=\"example.py\"}\nprint(\"hi\")\n```",
  "enabled_extensions": ["code_blocks"]
}
```

Для выгрузки страницы в markdown через GET:

```text
/api/v1/page/163939/markdown?enabled_extensions=toc,admonitions,code_blocks
```

### Через MCP

Пример preview:

```json
{
  "tool": "preview_markdown_to_storage",
  "arguments": {
    "markdown_text": "> [!NOTE]\n> Полезная справка",
    "enabled_extensions": ["admonitions"]
  }
}
```

Пример создания страницы:

```json
{
  "tool": "create_page_from_markdown",
  "arguments": {
    "title": "Example",
    "parent_id": "12345",
    "space_key": "DOC",
    "markdown_text": "```python {title=\"example.py\"}\nprint(\"hi\")\n```",
    "enabled_extensions": ["code_blocks"]
  }
}
```

## Как посмотреть список расширений

### HTTP API

```text
GET /api/v1/markdown/extensions
```

### MCP

Tool:

```text
list_markdown_extensions
```

## Как добавить своё расширение

Нужно создать класс, наследующий `ConfluenceMarkdownExtension`.

Пример:

```python
from xml.etree import ElementTree as ET

from confluence_markdown_service import ConfluenceMarkdownExtension
from confluence_markdown_service.extensions.base import (
    MarkdownImportTransformResult,
    MarkdownRenderResult,
)


class ExpandExtension(ConfluenceMarkdownExtension):
    name = "expand"
    description = "Поддержка :::expand блоков"

    def preprocess_markdown(self, markdown_text: str) -> str:
        return markdown_text

    def transform_import_element(self, importer, element: ET.Element) -> MarkdownImportTransformResult:
        return MarkdownImportTransformResult()

    def render_macro(self, renderer, element: ET.Element) -> MarkdownRenderResult:
        return MarkdownRenderResult()
```

## Как подключить своё расширение

Пользовательские расширения передаются программно через `extra_extensions`.

Пример:

```python
from confluence_markdown_service import ConfluenceMarkdownImporter

custom_extension = ExpandExtension()

importer = ConfluenceMarkdownImporter(
    client,
    enabled_extensions=["toc", "admonitions"],
    extra_extensions=[custom_extension],
)
```

Для экспорта:

```python
from confluence_markdown_service import ConfluenceMarkdownExporter

exporter = ConfluenceMarkdownExporter(
    client,
    enabled_extensions=["toc", "admonitions"],
    extra_extensions=[custom_extension],
)
```

## Рекомендации для авторов расширений

- не менять работу базового markdown bridge, если расширение не включено
- по возможности сохранять обратимость `Markdown -> Confluence -> Markdown`
- использовать warnings, если точный roundtrip невозможен
- не ломать экспорт на неизвестных блоках
- оставлять fallback до plain text, если форматирование не удаётся сохранить

## Ограничения текущей версии

- встроенные расширения активируются только по явному запросу
- пользовательские расширения пока подключаются программно, а не через YAML-конфиг
- `admonitions` рассчитаны на поддерживаемый поднабор blockquote syntax
- `code_blocks` ориентирован на fenced code block с атрибутом `title`
