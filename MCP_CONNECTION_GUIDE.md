# Инструкция по подключению MCP серверов

Этот документ описывает, как подготовить окружение, настроить конфигурацию и подключить MCP-серверы в `stdio`-режиме.

Покрываются два проекта:

- `confluence-mcp-server`
- `jira-mcp-server`

Основной акцент в документе:

- локальный запуск через `Python`
- локальный запуск через `Docker`
- подключение к агенту именно в `stdio`-режиме
- готовые YAML-примеры под `server`-формат
- отдельные примеры для `Confluence Markdown Extensions`

## 0. Быстрый путь: автоматическая настройка

Если не хочется проходить весь процесс вручную, можно запустить bootstrap-скрипт:

```bash
python3 scripts/bootstrap_mcp.py
```

Что он делает:

- спрашивает `base_url`
- спрашивает `default_space_key`
- спрашивает `api_token`
- создаёт `config/app.yaml`
- создаёт `secrets/confluence.yaml`
- генерирует готовые MCP snippets для `Python` и `Docker`

Дополнительно можно попросить его сразу подготовить Python-окружение:

```bash
python3 scripts/bootstrap_mcp.py --setup-python
```

Или собрать Docker image:

```bash
python3 scripts/bootstrap_mcp.py --setup-docker
```

После этого обычно остаётся только взять готовый путь до `scripts/run_mcp.sh` или `scripts/run_mcp_docker.sh` и вставить его в MCP-конфиг клиента.

## 1. Что понадобится заранее

Минимально нужны:

- `Python 3.10+`
- `pip`
- `venv`
- `Docker` — если хочешь запускать не через Python, а через контейнер
- доступ к Confluence / Jira
- учетные данные для API

Рекомендуемый вариант:

- для разработки и ручного запуска использовать `Python`
- для стандартизированного запуска у пользователей или агентов использовать `Docker`

## 1.1. Скачать проекты из GitHub

Перед настройкой окружения сначала скачай нужные репозитории.

### Вариант A. Скачать оба проекта

```bash
git clone https://github.com/Hhhuuu/confluence-mcp-server.git
git clone https://github.com/Hhhuuu/jira-mcp-server.git
```

### Вариант B. Скачать только Confluence MCP Server

```bash
git clone https://github.com/Hhhuuu/confluence-mcp-server.git
```

### Вариант C. Скачать только Jira MCP Server

```bash
git clone https://github.com/Hhhuuu/jira-mcp-server.git
```

После этого перейди в каталог нужного проекта и продолжай настройку из этой инструкции.

## 2. Подготовка окружения

### 2.1. macOS

#### Python

Проверка:

```bash
python3 --version
python3 -m pip --version
```

Если Python не установлен, можно поставить его двумя способами:

1. Через официальный installer: [Python для macOS](https://www.python.org/downloads/macos/)
2. Через Homebrew:

```bash
brew install python@3.12
```

Если Homebrew ещё не установлен, см. [официальную инструкцию Homebrew](https://brew.sh/).

Проверка `venv`:

```bash
python3 -m venv --help
```

#### Docker

Самый простой путь:

1. Установить Docker Desktop: [Docker Desktop для macOS](https://docs.docker.com/desktop/setup/install/mac-install/)
2. Или установить через Homebrew:

```bash
brew install --cask docker
```

3. Запустить Docker Desktop
4. Проверить:

```bash
docker --version
docker info
```

### 2.2. Linux

Ниже пример для Debian / Ubuntu. Для RHEL / Fedora / Arch команды будут отличаться, но логика та же.

#### Python

Официальные материалы:

- [Python Releases for Linux / source and other platforms](https://www.python.org/downloads/)

Пример для Debian / Ubuntu:

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

Проверка:

```bash
python3 --version
python3 -m pip --version
```

#### Docker

Официальная инструкция для Ubuntu:

- [Docker Engine на Ubuntu](https://docs.docker.com/engine/install/ubuntu/)

Простой системный вариант для Debian / Ubuntu:

```bash
sudo apt update
sudo apt install -y docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

После добавления в группу `docker` перелогинься или перезапусти shell.

Проверка:

```bash
docker --version
docker info
```

### 2.3. Windows

Рекомендуемый shell: `PowerShell`.

#### Python

Проверь:

```powershell
py --version
py -3 --version
```

Если Python не установлен:

1. Установи Python 3.12+ с официальной страницы: [Python для Windows](https://www.python.org/downloads/windows/)
2. На шаге установки включи `Add Python to PATH`

Проверка:

```powershell
py -3 -m pip --version
```

#### Docker

Самый простой путь:

1. Установить Docker Desktop: [Docker Desktop для Windows](https://docs.docker.com/desktop/setup/install/windows-install/)
2. Если установщик предложит, включить backend `WSL 2`
3. Запустить Docker Desktop
4. Проверить:

```powershell
docker --version
docker info
```

## 3. Какие режимы запуска поддерживаются

Для обоих проектов есть две основные ветки:

1. `Python + .venv-mcp`
2. `Docker + mcp-stdio`

Для подключения к агенту в этом документе приоритет у `stdio`.

## 4. Подготовка Confluence MCP Server

Проект:

- `confluence-mcp-server`

### 4.1. Подготовить рабочие YAML-файлы

В проекте уже лежат шаблоны. Из них нужно сделать рабочие файлы конфигурации.

Что должно получиться в итоге:

- `config/app.yaml`
- `secrets/confluence.yaml`

Самый простой способ на macOS / Linux:

```bash
cp config/app.yaml.example config/app.yaml
cp secrets/confluence.yaml.example secrets/confluence.yaml
```

На Windows PowerShell:

```powershell
Copy-Item config/app.yaml.example config/app.yaml
Copy-Item secrets/confluence.yaml.example secrets/confluence.yaml
```

После этого открой:

- `config/app.yaml`
- `secrets/confluence.yaml`

и замени примерные значения на свои реальные.

### 4.2. Готовый `app.yaml` под server-формат

```yaml
confluence:
  base_url: "https://confluence.example.local"
  deployment: "server"
  verify_ssl: false
  default_space_key: "DOC"
```

В этом минимальном варианте пользователю обычно нужно заменить только:

- `base_url` — указать свой адрес Confluence Server
- `default_space_key` — указать свой ключ пространства

### 4.3. Готовый `secrets/confluence.yaml` под server-формат

В этой инструкции используется только token-based авторизация.

```yaml
confluence:
  auth_type: "api_token"
  api_token: "your-server-token"
```

Здесь `your-server-token` нужно заменить на своё реальное значение. Где его получить, описано ниже в разделе `4.4`.

### 4.4. Где взять токен для Confluence

Добавь сюда свои скриншоты.

#### Блок для скриншота 1

> Вставить скриншот: где в Confluence Server / Data Center или внутреннем IAM создаётся токен.

#### Блок для скриншота 2

> Вставить скриншот: где пользователь создаёт или копирует token для интеграции.

### 4.5. Пример markdown с Confluence-расширениями

По умолчанию во встроенном markdown bridge уже включены расширения `toc`, `admonitions`, `code_blocks`, `date_element`, `jira_links` и `status_element`, поэтому можно использовать такой markdown:

```md
# Руководство по запуску

[TOC]

> [!NOTE]
> Это справочный блок.
>
> Он хорошо подходит для пояснений и подсказок.

> [!WARNING]
> Это предупреждение.
>
> Используй его для важных ограничений.

> [!ERROR]
> Это блок ошибки.
>
> В Confluence он будет опубликован как panel.

## Пример кода

```python {title="run_example.py"}
print("hello from confluence extension")
```

Дата релиза: <time datetime="2026-07-20"></time>

Статус: <status color="Green" subtle="true">Готово</status>

См. задачу по релизу: [KAN-123](https://jira.example.local/browse/KAN-123)
```

Важно:

- если нужен стандартный режим, ничего дополнительно включать не надо
- если нужно ограничить список расширений, можно передать `enabled_extensions`
- если нужно полностью отключить встроенные расширения, можно передать `enabled_extensions: []`
- актуальная документация по ним лежит в:
  - `EXTENSIONS.md`

## 5. Подготовка Jira MCP Server

Проект:

- `jira-mcp-server`

### 5.1. Подготовить рабочие YAML-файлы

В проекте уже лежат шаблоны. Из них нужно сделать рабочие файлы конфигурации.

Что должно получиться в итоге:

- `config/app.yaml`
- `secrets/jira.yaml`

Самый простой способ на macOS / Linux:

```bash
cp config/app.yaml.example config/app.yaml
cp secrets/jira.yaml.example secrets/jira.yaml
```

На Windows PowerShell:

```powershell
Copy-Item config/app.yaml.example config/app.yaml
Copy-Item secrets/jira.yaml.example secrets/jira.yaml
```

После этого открой:

- `config/app.yaml`
- `secrets/jira.yaml`

и замени примерные значения на свои реальные.

### 5.2. Готовый `app.yaml` под server-формат

```yaml
jira:
  base_url: "https://jira.example.local"
  api_version: "2"
  deployment: "server"
  verify_ssl: false
```

В этом минимальном варианте пользователю обычно нужно заменить только:

- `base_url` — указать свой адрес Jira Server

### 5.3. Готовый `secrets/jira.yaml` под server-формат

В этой инструкции используется только token-based авторизация.

```yaml
jira:
  auth_type: "bearer"
  bearer_token: "your-server-token"
```

Здесь `your-server-token` нужно заменить на своё реальное значение. Где его получить, описано ниже в разделе `5.4`.

### 5.4. Где взять токен для Jira

Добавь сюда свои скриншоты.

#### Блок для скриншота 1

> Вставить скриншот: где в Jira Server / Data Center или внешнем IAM создаётся bearer token для интеграции.

#### Блок для скриншота 2

> Вставить скриншот: где пользователь копирует или получает bearer token для подключения.

## 6. Установка через Python

Ниже именно подготовка `stdio`-ветки.

Идея такая:

- ты создаёшь `.venv-mcp`
- устанавливаешь зависимости
- дальше агент сам будет запускать `scripts/run_mcp.sh` из своей MCP-конфигурации

Если нужен HTTP API, для обоих проектов уже есть отдельные документы:

- `LOCAL_ENVIRONMENTS.md` в соответствующем проекте

### 6.1. macOS / Linux

#### Confluence

```bash
cd <path-to>/confluence-mcp-server
python3.12 -m venv .venv-mcp
source .venv-mcp/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install --no-build-isolation \
  -e confluence-client \
  -e confluence-pagecreator-service \
  -e confluence-markdown-service \
  -e confluence-mcp-server
```

После этих шагов окружение для Confluence готово.
Дальше в MCP-конфигурации агента нужно будет указать путь до `scripts/run_mcp.sh`.

#### Jira

```bash
cd <path-to>/jira-mcp-server
python3.12 -m venv .venv-mcp
source .venv-mcp/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install --no-build-isolation \
  -e jira-client \
  -e jira-readonly-service \
  -e jira-write-service \
  -e jira-mcp-server
```

После этих шагов окружение для Jira готово.
Дальше в MCP-конфигурации агента нужно будет указать путь до `scripts/run_mcp.sh`.

Если `python3.12` недоступен, используй любой `Python 3.10+`.

### 6.2. Windows PowerShell

#### Confluence

```powershell
cd C:\path\to\confluence-mcp-server
py -3.12 -m venv .venv-mcp
.\.venv-mcp\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install --no-build-isolation `
  -e confluence-client `
  -e confluence-pagecreator-service `
  -e confluence-markdown-service `
  -e confluence-mcp-server
```

После этих шагов окружение для Confluence готово.
Дальше в MCP-конфигурации агента нужно будет указать путь до `scripts/run_mcp.sh`.

Если `bash` недоступен, путь до `scripts/run_mcp.sh` удобно использовать через Git Bash или WSL.

#### Jira

```powershell
cd C:\path\to\jira-mcp-server
py -3.12 -m venv .venv-mcp
.\.venv-mcp\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install --no-build-isolation `
  -e jira-client `
  -e jira-readonly-service `
  -e jira-write-service `
  -e jira-mcp-server
```

После этих шагов окружение для Jira готово.
Дальше в MCP-конфигурации агента нужно будет указать путь до `scripts/run_mcp.sh`.

Если `bash` недоступен, путь до `scripts/run_mcp.sh` удобно использовать через Git Bash или WSL.

## 7. Запуск через Docker

### 7.1. Подготовка Docker по ОС

#### macOS

1. Установить Docker Desktop
2. Запустить Docker Desktop
3. Проверить:

```bash
docker --version
docker info
```

#### Linux

Ниже пример для Debian / Ubuntu:

```bash
sudo apt update
sudo apt install -y docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

После этого открой новый shell или перелогинься.

Проверка:

```bash
docker --version
docker info
```

#### Windows

1. Установить Docker Desktop
2. Включить backend `WSL 2`, если установщик это предложит
3. Запустить Docker Desktop
4. Проверить в PowerShell:

```powershell
docker --version
docker info
```

### 7.2. Сборка образов

#### Confluence

```bash
cd <path-to>/confluence-mcp-server
docker build -t confluence-mcp:local .
```

#### Jira

```bash
cd <path-to>/jira-mcp-server
docker build -t jira-mcp:local .
```

### 7.3. Ручной запуск `stdio`

#### Confluence

```bash
docker run --rm -i \
  -e PAGECREATOR_RUNTIME_MODE=mcp-stdio \
  -v "$(pwd)/config:/app/config:ro" \
  -v "$(pwd)/secrets:/app/secrets:ro" \
  confluence-mcp:local
```

#### Jira

```bash
docker run --rm -i \
  -e JIRA_RUNTIME_MODE=mcp-stdio \
  -v "$(pwd)/config:/app/config:ro" \
  -v "$(pwd)/secrets:/app/secrets:ro" \
  jira-mcp:local
```

### 7.4. Windows PowerShell пример для Docker

#### Confluence

```powershell
docker run --rm -i `
  -e PAGECREATOR_RUNTIME_MODE=mcp-stdio `
  -v "${PWD}\config:/app/config:ro" `
  -v "${PWD}\secrets:/app/secrets:ro" `
  confluence-mcp:local
```

#### Jira

```powershell
docker run --rm -i `
  -e JIRA_RUNTIME_MODE=mcp-stdio `
  -v "${PWD}\config:/app/config:ro" `
  -v "${PWD}\secrets:/app/secrets:ro" `
  jira-mcp:local
```

## 8. Подключение MCP к агенту в `stdio`-режиме

Ниже основной паттерн: агент запускает локальную команду, а команда поднимает MCP-сервер через stdin/stdout. В Python-ветке этой командой обычно будет `scripts/run_mcp.sh`.

### 8.1. Вариант A. Подключение через Python launcher

#### Confluence

Если клиент поддерживает project-level `.mcp.json`, можно использовать уже готовый файл:

- `.mcp.json`

Он содержит:

```json
{
  "mcpServers": {
    "confluence-mcp": {
      "command": "./scripts/run_mcp.sh"
    }
  }
}
```

Если нужен user-level JSON-конфиг клиента, используй абсолютный путь:

```json
{
  "mcpServers": {
    "confluence-mcp": {
      "command": "<absolute-path>/confluence-mcp-server/scripts/run_mcp.sh"
    }
  }
}
```

#### Jira

Готовый project-level файл:

- `.mcp.json`

Он содержит:

```json
{
  "mcpServers": {
    "jira-readonly": {
      "command": "./scripts/run_mcp.sh"
    }
  }
}
```

Если нужен user-level JSON-конфиг:

```json
{
  "mcpServers": {
    "jira-readonly": {
      "command": "<absolute-path>/jira-mcp-server/scripts/run_mcp.sh"
    }
  }
}
```

### 8.2. Вариант B. Подключение через Docker

Перед подключением агентом убедись, что образ уже собран на этой машине и команда `docker` доступна из того же окружения, где запускается клиент.

#### Confluence

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
        "<absolute-path>/confluence-mcp-server/config:/app/config:ro",
        "-v",
        "<absolute-path>/confluence-mcp-server/secrets:/app/secrets:ro",
        "confluence-mcp:local"
      ]
    }
  }
}
```

#### Jira

```json
{
  "mcpServers": {
    "jira-readonly": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-e",
        "JIRA_RUNTIME_MODE=mcp-stdio",
        "-v",
        "<absolute-path>/jira-mcp-server/config:/app/config:ro",
        "-v",
        "<absolute-path>/jira-mcp-server/secrets:/app/secrets:ro",
        "jira-mcp:local"
      ]
    }
  }
}
```

### 8.3. VS Code / IDE / CLI: как думать про конфиг

У разных клиентов точный формат различается, но логика одна и та же:

1. Указать `command`
2. Если нужно — указать `args`
3. Для `stdio` не нужен HTTP URL
4. Для Python-ветки лучше указывать launcher-скрипт
5. Для Docker-ветки лучше указывать `docker run --rm -i ...`

Практически это даёт две рабочие стратегии:

- `Python`:
  - `command: /abs/path/scripts/run_mcp.sh`
- `Docker`:
  - `command: docker`
  - `args: ["run", "--rm", "-i", ...]`

Если клиент плохо работает с относительными путями:

- используй абсолютные пути
- особенно для `docker -v ...`
- и для `command` до `run_mcp.sh`

## 9. Проверка после подключения

Когда агент впервые подключился к MCP-серверу, удобно проверить минимальный smoke-flow.

### 9.1. Confluence

Начни с таких вызовов:

1. `show_runtime_config`
2. `get_current_user`
3. `get_space`

Если хочешь проверить markdown flow:

1. `list_markdown_extensions`
2. `preview_markdown_to_storage`
3. `create_page_from_markdown`

### 9.2. Jira

Начни с:

1. `show_runtime_config`
2. `get_current_user`
3. `get_jira_issue`

Если нужно проверить write-flow:

1. `get_jira_create_issue_types`
2. `create_jira_issue`
3. `add_jira_comment`

## 10. Типовые проблемы

### 10.1. Не найден `.venv-mcp/bin/python`

Причина:

- окружение ещё не создано
- зависимости ещё не установлены

Решение:

- создать `.venv-mcp`
- установить editable-пакеты
- повторить запуск `./scripts/run_mcp.sh`

### 10.2. Клиент не понимает относительный путь

Решение:

- заменить `./scripts/run_mcp.sh` на абсолютный путь
- для Docker volume mounts тоже перейти на абсолютные пути

### 10.3. `docker run` не видит файлы конфигурации

Решение:

- проверить, что монтируются именно папки `config` и `secrets`
- проверить абсолютный путь
- проверить, что внутри есть `app.yaml` и `confluence.yaml` / `jira.yaml`

### 10.4. Ошибка авторизации

Проверь:

- `base_url`
- `deployment`
- `auth_type`
- username / password / token
- доступ пользователя к целевому продукту
