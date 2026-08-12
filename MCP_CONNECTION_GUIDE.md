# Подключение Confluence MCP к Kilo Code и Kilo CLI

Сервер работает локально по STDIO под Python 3.10 или новее. Генерируются два разных
формата: для расширения Kilo Code 7.49+ в VS Code и для актуального Kilo CLI.

## Автоматическая генерация

После запуска `scripts/setup_mcp.ps1` или `scripts/setup_mcp.sh` создаются:

- `.kilo-generated/kilo-vscode.windows.json`;
- `.kilo-generated/kilo-vscode.linux.json`;
- `.kilo-generated/kilo-vscode.macos.json`;
- `.kilo-generated/kilo-cli.windows.json`;
- `.kilo-generated/kilo-cli.linux.json`;
- `.kilo-generated/kilo-cli.macos.json`.

Для расширения VS Code выбери файл `kilo-vscode.<os>.json`, проверь абсолютные
пути и скопируй его в рабочий проект:

```text
<рабочий-проект>/.kilocode/mcp.json
```

Конфигурация не содержит PAT: он остаётся в локальном
`secrets/confluence.yaml`.

## Kilo CLI

Для CLI выбери `kilo-cli.<os>.json`. Проектный конфиг рекомендуется положить в:

```text
<рабочий-проект>/.kilo/kilo.json
```

Можно также использовать `kilo.json` или `kilo.jsonc` в корне рабочего проекта.
Глобальный конфиг размещается в `~/.config/kilo/kilo.json`; на Windows это
обычно `C:\Users\<username>\.config\kilo\kilo.json`.

Пример CLI-конфигурации для Windows:

```json
{
  "mcp": {
    "confluence-mcp": {
      "type": "local",
      "command": [
        "C:\\Tools\\confluence-mcp-server\\.venv-mcp\\Scripts\\python.exe",
        "-m",
        "confluence_mcp"
      ],
      "environment": {
        "PAGECREATOR_CONFIG_PATH": "C:\\Tools\\confluence-mcp-server\\config\\app.yaml",
        "PAGECREATOR_SECRETS_PATH": "C:\\Tools\\confluence-mcp-server\\secrets\\confluence.yaml"
      },
      "enabled": true,
      "timeout": 30000
    }
  }
}
```

После копирования проверь подключение:

```bash
kilo mcp list
```

Запускай `kilo mcp list` из рабочего проекта, если используешь проектный
`.kilo/kilo.json`.

## Windows

На Windows используются прямые абсолютные пути. Пример для установки в
`C:\Tools\confluence-mcp-server`:

```json
{
  "mcpServers": {
    "confluence-mcp": {
      "command": "C:\\Tools\\confluence-mcp-server\\.venv-mcp\\Scripts\\python.exe",
      "args": ["-m", "confluence_mcp"],
      "env": {
        "PAGECREATOR_CONFIG_PATH": "C:\\Tools\\confluence-mcp-server\\config\\app.yaml",
        "PAGECREATOR_SECRETS_PATH": "C:\\Tools\\confluence-mcp-server\\secrets\\confluence.yaml"
      },
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

Сгенерировать файл с конкретным Windows-путём можно отдельно:

```powershell
py -3.10 .\scripts\bootstrap_mcp.py --skip-config --windows-project-root "D:\MCP\confluence-mcp-server"
```

## Linux

```json
{
  "mcpServers": {
    "confluence-mcp": {
      "command": "/opt/confluence-mcp-server/.venv-mcp/bin/python",
      "args": ["-m", "confluence_mcp"],
      "env": {
        "PAGECREATOR_CONFIG_PATH": "/opt/confluence-mcp-server/config/app.yaml",
        "PAGECREATOR_SECRETS_PATH": "/opt/confluence-mcp-server/secrets/confluence.yaml"
      },
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

Генерация под конкретный путь:

```bash
python3 scripts/bootstrap_mcp.py --skip-config --linux-project-root /opt/confluence-mcp-server
```

## macOS

```json
{
  "mcpServers": {
    "confluence-mcp": {
      "command": "/Users/user/Tools/confluence-mcp-server/.venv-mcp/bin/python",
      "args": ["-m", "confluence_mcp"],
      "env": {
        "PAGECREATOR_CONFIG_PATH": "/Users/user/Tools/confluence-mcp-server/config/app.yaml",
        "PAGECREATOR_SECRETS_PATH": "/Users/user/Tools/confluence-mcp-server/secrets/confluence.yaml"
      },
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

Генерация под конкретный путь:

```bash
python3 scripts/bootstrap_mcp.py --skip-config --macos-project-root /Users/user/Tools/confluence-mcp-server
```

## Slash-команды Kilo

В проекте есть готовые workflow-файлы для Kilo slash commands:

```text
.kilo/commands/confluence-*.md
```

Если открыть этот репозиторий в Kilo, команды появятся в чате через `/`, например:

```text
/confluence-help
/confluence-proofread-page
/confluence-add-proofread-comments
/confluence-get-page
/confluence-export-page-markdown
```

Каждая slash-команда является тонкой оберткой над соответствующим MCP tool сервера
`confluence-mcp`. Для рабочего проекта вне этого репозитория скопируй каталог
`.kilo/commands` в корень нужного проекта или в глобальный каталог
`~/.config/kilo/commands`.

После добавления команд перезапусти окно VS Code/Kilo или обнови список команд.

## Проверка в Kilo

1. Открой рабочий проект, где создан `.kilocode/mcp.json`.
2. В Kilo открой `Settings` → `Agent Behaviour` → `MCP Servers`.
3. Обнови список серверов или перезапусти окно VS Code.
4. Проверь, что `confluence-mcp` включён и его tools появились в списке.

При ошибке запуска сначала выполни wrapper вручную. Он явно сообщит об
отсутствующей `.venv-mcp`, неверной версии Python или отсутствующих YAML:

```powershell
C:\Tools\confluence-mcp-server\scripts\run_mcp.ps1
```

```bash
/opt/confluence-mcp-server/scripts/run_mcp.sh
```

Формат `mcpServers` оставлен специально для совместимости с Kilo Code 7.49+.
Kilo CLI использует отдельные файлы `kilo-cli.*.json`, верхнеуровневый ключ
`mcp` и массив `command`; не смешивай эти два формата.
