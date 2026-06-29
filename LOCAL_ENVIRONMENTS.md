# Локальные окружения

Этот документ описывает, как локально поднимать Python-окружения для проекта:

- `.venv` — для HTTP API и обычной ручной отладки
- `.venv-mcp` — для MCP-режима и проверки project-level `.mcp.json`

## 1. Зачем два окружения

Мы разделяем окружения, потому что:

- для HTTP API достаточно обычного локального Python
- для MCP у нас есть отдельные зависимости и отдельный сценарий запуска
- так удобнее не смешивать быстрый dev-цикл API и рабочее окружение MCP

Если хочется, можно жить и в одном окружении, но рекомендуемый вариант для проекта сейчас именно такой:

- `.venv`
- `.venv-mcp`

## 2. Структура пакетов

Сейчас локально используются editable installs для этих пакетов:

- `confluence-client`
- `confluence-pagecreator-service`
- `confluence-markdown-service`
- `confluence-mcp-server`

## 3. Окружение для HTTP API

### Шаг 1. Создать окружение

Из корня проекта:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Шаг 2. Обновить базовые инструменты

```bash
python -m pip install --upgrade pip setuptools wheel
```

### Шаг 3. Установить локальные пакеты

Важно: в текущей среде `pip` может пытаться выходить в сеть за build dependencies. Поэтому для локальной установки лучше использовать `--no-build-isolation`.

```bash
python -m pip install --no-build-isolation \
  -e confluence-client \
  -e confluence-pagecreator-service \
  -e confluence-markdown-service \
  -e confluence-mcp-server
```

### Шаг 4. Запустить локальный HTTP API

```bash
cd confluence-mcp-server
uvicorn confluence_mcp.api:app --app-dir src --reload
```

После этого API будет доступен по адресу:

```text
http://127.0.0.1:8000
```

### Шаг 5. Быстрая проверка

```bash
curl http://127.0.0.1:8000/health
```

## 4. Окружение для MCP

Для MCP нужен Python `3.10+`.

Рекомендуемый вариант:

```bash
python3.12 -m venv .venv-mcp
source .venv-mcp/bin/activate
```

Если `python3.12` недоступен, можно использовать любой Python `3.10+`.

### Шаг 2. Обновить инструменты сборки

```bash
python -m pip install --upgrade pip setuptools wheel
```

### Шаг 3. Установить локальные пакеты

```bash
python -m pip install --no-build-isolation \
  -e confluence-client \
  -e confluence-pagecreator-service \
  -e confluence-markdown-service \
  -e confluence-mcp-server
```

### Шаг 4. Запустить MCP вручную

Из корня проекта:

```bash
./scripts/run_mcp.sh
```

## 5. Project-level `.mcp.json`

В корне проекта лежит файл:

- `.mcp.json`

Он запускает MCP так:

```json
{
  "mcpServers": {
    "confluence-mcp": {
      "command": "./scripts/run_mcp.sh"
    }
  }
}
```

Почему это удобнее:

- launcher сам находит корень проекта
- внутри него автоматически вычисляются абсолютные пути до `.venv-mcp`, `config/app.yaml` и `secrets/confluence.yaml`
- при переносе проекта на другой компьютер не нужно вручную править пути в `.mcp.json`

Если клиент поддерживает project-level `.mcp.json`, обычно этого достаточно.

## 6. Конфиг и секреты

Перед запуском проверь, что созданы:

- `config/app.yaml`
- `secrets/confluence.yaml`

Шаблоны:

- `config/app.yaml.example`
- `secrets/confluence.yaml.example`

## 7. Если после rename что-то перестало импортироваться

После серьёзных переименований или переноса пакетов лучше повторно выполнить editable install:

```bash
source .venv/bin/activate
python -m pip install --no-build-isolation \
  -e confluence-client \
  -e confluence-pagecreator-service \
  -e confluence-markdown-service \
  -e confluence-mcp-server
```

И отдельно для MCP:

```bash
source .venv-mcp/bin/activate
python -m pip install --no-build-isolation \
  -e confluence-client \
  -e confluence-pagecreator-service \
  -e confluence-markdown-service \
  -e confluence-mcp-server
```

## 8. Как понять, что используется правильный Python

Проверь:

```bash
which python
python --version
python -m pip --version
```

Для MCP удобно проверять так:

```bash
.venv-mcp/bin/python --version
.venv-mcp/bin/python -m pip --version
```

## 9. Если `pip` пытается выйти в интернет

В нашей среде это может происходить из-за build isolation.

Используй:

```bash
python -m pip install --no-build-isolation ...
```

Это особенно важно, если сеть ограничена или PyPI недоступен.

## 10. Рекомендуемый порядок для нового разработчика

1. Создать `config/app.yaml` и `secrets/confluence.yaml` из `.example`
2. Поднять `.venv`
3. Проверить HTTP API
4. Поднять `.venv-mcp`
5. Проверить запуск `confluence_mcp`
6. Только после этого подключать `.mcp.json` в клиенте
