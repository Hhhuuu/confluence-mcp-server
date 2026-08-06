#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

VENV_PYTHON="${PROJECT_ROOT}/.venv-mcp/bin/python"
CONFIG_PATH="${PAGECREATOR_CONFIG_PATH:-${PROJECT_ROOT}/config/app.yaml}"
SECRETS_PATH="${PAGECREATOR_SECRETS_PATH:-${PROJECT_ROOT}/secrets/confluence.yaml}"

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "Не найден интерпретатор MCP-окружения: ${VENV_PYTHON}" >&2
  echo "Создай .venv-mcp и установи зависимости перед запуском MCP." >&2
  exit 1
fi

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "Не найден конфиг: ${CONFIG_PATH}. Запусти scripts/setup_mcp.sh." >&2
  exit 1
fi
if [[ ! -f "${SECRETS_PATH}" ]]; then
  echo "Не найден файл подключения Confluence: ${SECRETS_PATH}. Запусти scripts/setup_mcp.sh." >&2
  exit 1
fi

PYTHON_VERSION="$(${VENV_PYTHON} -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if ! "${VENV_PYTHON}" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 10) else 1)'; then
  echo "MCP должен запускаться под Python 3.10 или новее, найден Python ${PYTHON_VERSION}." >&2
  exit 1
fi

export PAGECREATOR_CONFIG_PATH="${CONFIG_PATH}"
export PAGECREATOR_SECRETS_PATH="${SECRETS_PATH}"

exec "${VENV_PYTHON}" -m confluence_mcp
