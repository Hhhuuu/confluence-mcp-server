#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PYTHON_COMMAND=""
for candidate in python3.10 python3 python; do
  if command -v "${candidate}" >/dev/null 2>&1 && \
    "${candidate}" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 10) else 1)'; then
    PYTHON_COMMAND="${candidate}"
    break
  fi
done

if [[ -z "${PYTHON_COMMAND}" ]]; then
  echo "Не найден Python 3.10 или новее." >&2
  exit 1
fi

exec "${PYTHON_COMMAND}" "${SCRIPT_DIR}/bootstrap_mcp.py" --setup-python "$@"
