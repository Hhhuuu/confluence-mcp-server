#!/usr/bin/env python3
"""Упрощённая настройка Confluence MCP Server."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "app.yaml"
SECRETS_PATH = PROJECT_ROOT / "secrets" / "confluence.yaml"
PYTHON_WRAPPER = PROJECT_ROOT / "scripts" / "run_mcp.sh"
DOCKER_WRAPPER = PROJECT_ROOT / "scripts" / "run_mcp_docker.sh"
VENV_DIR = PROJECT_ROOT / ".venv-mcp"


def prompt(label: str, default: Optional[str] = None, secret: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        if secret:
            try:
                import getpass

                value = getpass.getpass(f"{label}{suffix}: ")
            except Exception:
                value = input(f"{label}{suffix}: ")
        else:
            value = input(f"{label}{suffix}: ")
        value = value.strip()
        if value:
            return value
        if default is not None:
            return default
        print("Значение не должно быть пустым.")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def render_app_yaml(base_url: str, default_space_key: str) -> str:
    return (
        'confluence:\n'
        f'  base_url: "{base_url}"\n'
        '  deployment: "server"\n'
        '  verify_ssl: false\n'
        f'  default_space_key: "{default_space_key}"\n'
    )


def render_secrets_yaml(api_token: str) -> str:
    return (
        'confluence:\n'
        '  auth_type: "api_token"\n'
        f'  api_token: "{api_token}"\n'
    )


def run_command(cmd: list[str], cwd: Path) -> None:
    print(f"\n$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd), check=True)


def venv_python_path() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def setup_python_env() -> None:
    run_command([sys.executable, "-m", "venv", str(VENV_DIR)], PROJECT_ROOT)
    vpy = str(venv_python_path())
    run_command([vpy, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], PROJECT_ROOT)
    run_command(
        [
            vpy,
            "-m",
            "pip",
            "install",
            "--no-build-isolation",
            "-e",
            "confluence-client",
            "-e",
            "confluence-pagecreator-service",
            "-e",
            "confluence-markdown-service",
            "-e",
            "confluence-mcp-server",
        ],
        PROJECT_ROOT,
    )


def setup_docker(image_name: str) -> None:
    run_command(["docker", "build", "-t", image_name, "."], PROJECT_ROOT)


def build_python_snippet() -> dict:
    return {
        "mcpServers": {
            "confluence-mcp": {
                "command": str(PYTHON_WRAPPER),
            }
        }
    }


def build_docker_snippet() -> dict:
    return {
        "mcpServers": {
            "confluence-mcp": {
                "command": str(DOCKER_WRAPPER),
            }
        }
    }


def write_snippets() -> None:
    write_text(PROJECT_ROOT / ".mcp.local.python.json", json.dumps(build_python_snippet(), ensure_ascii=False, indent=2) + "\n")
    write_text(PROJECT_ROOT / ".mcp.local.docker.json", json.dumps(build_docker_snippet(), ensure_ascii=False, indent=2) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap для Confluence MCP Server")
    parser.add_argument("--base-url")
    parser.add_argument("--space-key")
    parser.add_argument("--api-token")
    parser.add_argument("--setup-python", action="store_true")
    parser.add_argument("--setup-docker", action="store_true")
    parser.add_argument("--docker-image", default="confluence-mcp:local")
    parser.add_argument("--non-interactive", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.non_interactive:
        if not args.base_url or not args.space_key or not args.api_token:
            print("Для --non-interactive нужны --base-url, --space-key и --api-token.", file=sys.stderr)
            return 2
        base_url = args.base_url
        space_key = args.space_key
        api_token = args.api_token
    else:
        print("Настройка Confluence MCP Server")
        print(f"Проект: {PROJECT_ROOT}\n")
        base_url = args.base_url or prompt("Укажи base_url Confluence Server", "https://confluence.example.local")
        space_key = args.space_key or prompt("Укажи default_space_key", "DOC")
        api_token = args.api_token or prompt("Укажи API token", secret=True)

    write_text(CONFIG_PATH, render_app_yaml(base_url, space_key))
    write_text(SECRETS_PATH, render_secrets_yaml(api_token))
    write_snippets()

    print("\nГотово:")
    print(f"- создан {CONFIG_PATH}")
    print(f"- создан {SECRETS_PATH}")
    print(f"- создан {PROJECT_ROOT / '.mcp.local.python.json'}")
    print(f"- создан {PROJECT_ROOT / '.mcp.local.docker.json'}")

    if args.setup_python:
        try:
            setup_python_env()
            print("\nPython MCP окружение подготовлено.")
        except Exception as exc:  # noqa: BLE001
            print(f"\nНе удалось полностью подготовить Python-окружение: {exc}", file=sys.stderr)

    if args.setup_docker:
        try:
            setup_docker(args.docker_image)
            print(f"\nDocker image собран: {args.docker_image}")
        except Exception as exc:  # noqa: BLE001
            print(f"\nНе удалось собрать Docker image: {exc}", file=sys.stderr)

    print("\nДальше можно использовать один из вариантов подключения:")
    print(f"- Python: {PYTHON_WRAPPER}")
    print(f"- Docker: {DOCKER_WRAPPER}")
    print("\nГотовые MCP snippets записаны в:")
    print(f"- {PROJECT_ROOT / '.mcp.local.python.json'}")
    print(f"- {PROJECT_ROOT / '.mcp.local.docker.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
