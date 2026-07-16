ф#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

IMAGE_NAME="${CONFLUENCE_MCP_DOCKER_IMAGE:-confluence-mcp:local}"
CONFIG_DIR="${CONFLUENCE_MCP_CONFIG_DIR:-${PROJECT_ROOT}/config}"
SECRETS_DIR="${CONFLUENCE_MCP_SECRETS_DIR:-${PROJECT_ROOT}/secrets}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Не найден docker в PATH. Установи Docker и повтори запуск." >&2
  exit 1
fi

if [[ ! -d "${CONFIG_DIR}" ]]; then
  echo "Не найдена директория конфигурации: ${CONFIG_DIR}" >&2
  exit 1
fi

if [[ ! -d "${SECRETS_DIR}" ]]; then
  echo "Не найдена директория секретов: ${SECRETS_DIR}" >&2
  exit 1
fi

if [[ ! -f "${CONFIG_DIR}/app.yaml" ]]; then
  echo "Не найден файл конфигурации: ${CONFIG_DIR}/app.yaml" >&2
  exit 1
fi

if [[ ! -f "${SECRETS_DIR}/confluence.yaml" ]]; then
  echo "Не найден файл секретов: ${SECRETS_DIR}/confluence.yaml" >&2
  exit 1
fi

exec docker run --rm -i \
  -e PAGECREATOR_RUNTIME_MODE=mcp-stdio \
  -v "${CONFIG_DIR}:/app/config:ro" \
  -v "${SECRETS_DIR}:/app/secrets:ro" \
  "${IMAGE_NAME}"
