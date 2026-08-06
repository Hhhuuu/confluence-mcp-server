# Локальный запуск на Python 3.10+

Проект запускается нативно, без Docker. Для установки и работы MCP требуется
Python 3.10 или новее: bootstrap и launch-скрипты проверяют версию и
останавливаются только при запуске под Python 3.9 и старше.

## Автоматическая установка

### Windows PowerShell

Если репозиторий ещё не скачан:

```powershell
git clone https://github.com/Hhhuuu/confluence-mcp-server.git C:\Tools\confluence-mcp-server
Set-Location C:\Tools\confluence-mcp-server
.\scripts\setup_mcp.ps1
```

Или одной install-командой, если `install_mcp.ps1` уже сохранён локально:

```powershell
.\install_mcp.ps1 -InstallDirectory C:\Tools\confluence-mcp-server
```

Для обновления существующего клона и Python-пакетов:

```powershell
.\scripts\install_mcp.ps1 `
  -InstallDirectory C:\Tools\confluence-mcp-server `
  -Update `
  -SetupArguments "-Update", "-SkipConfig"
```

PowerShell-wrapper ищет Python через `py -3.10`, создаёт `.venv-mcp`, обновляет
инструменты сборки и устанавливает четыре локальных пакета в editable-режиме.

### Linux и macOS

```bash
git clone https://github.com/Hhhuuu/confluence-mcp-server.git ~/tools/confluence-mcp-server
cd ~/tools/confluence-mcp-server
./scripts/setup_mcp.sh
```

Обновление:

```bash
./scripts/install_mcp.sh --install-directory "$HOME/tools/confluence-mcp-server" --update -- --update --skip-config
```

Скрипт автоматически ищет `python3.10`, `python3` или `python` версии 3.10+.
Проверить активную версию можно так:

```bash
python3 --version
```

## Неинтерактивная настройка

Токен безопаснее передавать через переменную окружения, чтобы он не попадал в
историю команд.

PowerShell:

```powershell
$env:CONFLUENCE_TOKEN = "pat-value"
.\scripts\setup_mcp.ps1 -BaseUrl "https://confluence.company.local" -SpaceKey "DOC" -ApiTokenEnv CONFLUENCE_TOKEN -NonInteractive
```

Bash:

```bash
export CONFLUENCE_TOKEN='pat-value'
./scripts/setup_mcp.sh \
  --base-url 'https://confluence.company.local' \
  --space-key 'DOC' \
  --api-token-env CONFLUENCE_TOKEN \
  --non-interactive
```

## Пользовательские шаблоны

Встроенные шаблоны:

- `config/app.server.yaml.template`;
- `secrets/confluence.server.yaml.template`.

Можно передать любые собственные файлы через `--app-template` и
`--confluence-template`. Bootstrap заменяет в них:

- `${CONFLUENCE_BASE_URL}`;
- `${CONFLUENCE_SPACE_KEY}`;
- `${CONFLUENCE_API_TOKEN}`.

Пример для Windows:

```powershell
.\scripts\setup_mcp.ps1 `
  -AppTemplate "C:\McpTemplates\app.yaml.template" `
  -ConfluenceTemplate "C:\McpTemplates\confluence.yaml.template"
```

Результат всегда записывается в `config/app.yaml` и
`secrets/confluence.yaml`. Эти локальные файлы исключены из Git.

Bootstrap также создаёт в `.kilo-generated` отдельные конфигурации для
расширения Kilo Code 7.49+ (`kilo-vscode.*.json`) и Kilo CLI
(`kilo-cli.*.json`). Подробности находятся в `MCP_CONNECTION_GUIDE.md`.

## Установка или обновление только Python-пакетов

Windows:

```powershell
.\scripts\setup_mcp.ps1 -Update -SkipConfig
```

Linux/macOS:

```bash
./scripts/setup_mcp.sh --update --skip-config
```

## Запуск MCP

Windows:

```powershell
.\scripts\run_mcp.ps1
```

Linux/macOS:

```bash
./scripts/run_mcp.sh
```

Для нестандартного расположения YAML можно задать переменные
`PAGECREATOR_CONFIG_PATH` и `PAGECREATOR_SECRETS_PATH` до запуска.
