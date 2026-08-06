#!/usr/bin/env bash

set -euo pipefail

REPOSITORY="https://github.com/Hhhuuu/confluence-mcp-server.git"
INSTALL_DIRECTORY="${PWD}/confluence-mcp-server"
UPDATE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repository) REPOSITORY="$2"; shift 2 ;;
    --install-directory) INSTALL_DIRECTORY="$2"; shift 2 ;;
    --update) UPDATE=true; shift ;;
    --) shift; break ;;
    *) break ;;
  esac
done

if [[ -d "${INSTALL_DIRECTORY}/.git" ]]; then
  if [[ "${UPDATE}" == true ]]; then
    git -C "${INSTALL_DIRECTORY}" pull --ff-only
  fi
elif [[ -e "${INSTALL_DIRECTORY}" ]]; then
  echo "Каталог уже существует и не является git-репозиторием: ${INSTALL_DIRECTORY}" >&2
  exit 1
else
  git clone "${REPOSITORY}" "${INSTALL_DIRECTORY}"
fi

exec "${INSTALL_DIRECTORY}/scripts/setup_mcp.sh" "$@"
