#!/usr/bin/env python3
"""Кроссплатформенная настройка Confluence MCP Server на Python 3.10+."""

from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import subprocess
import sys
from typing import Mapping, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "app.yaml"
SECRETS_PATH = PROJECT_ROOT / "secrets" / "confluence.yaml"
VENV_DIR = PROJECT_ROOT / ".venv-mcp"
MINIMUM_PYTHON = (3, 10)


def require_supported_python() -> None:
    actual = sys.version_info[:2]
    if actual < MINIMUM_PYTHON:
        raise SystemExit(
            "Для настройки MCP нужен Python 3.10 или новее; "
            f"сейчас запущен Python {actual[0]}.{actual[1]}."
        )


def prompt(label: str, default: Optional[str] = None, secret: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        value = (
            getpass.getpass(f"{label}{suffix}: ")
            if secret
            else input(f"{label}{suffix}: ")
        ).strip()
        if value:
            return value
        if default is not None:
            return default
        print("Значение не должно быть пустым.")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def yaml_string(value: str) -> str:
    """Безопасно представить строку как YAML double-quoted scalar."""
    return json.dumps(value, ensure_ascii=False)


def render_app_yaml(base_url: str, default_space_key: str) -> str:
    return (
        "confluence:\n"
        f"  base_url: {yaml_string(base_url)}\n"
        '  deployment: "server"\n'
        "  verify_ssl: false\n"
        f"  default_space_key: {yaml_string(default_space_key)}\n"
    )


def render_secrets_yaml(api_token: str) -> str:
    return (
        "confluence:\n"
        '  auth_type: "api_token"\n'
        f"  api_token: {yaml_string(api_token)}\n"
    )


def render_template(path: Path, values: Mapping[str, str]) -> str:
    text = path.expanduser().resolve().read_text(encoding="utf-8")
    for name, value in values.items():
        text = text.replace("${" + name + "}", value)
    return text if text.endswith("\n") else text + "\n"


def run_command(cmd: list[str], cwd: Path) -> None:
    printable = subprocess.list2cmdline(cmd)
    print(f"\n$ {printable}")
    subprocess.run(cmd, cwd=str(cwd), check=True)


def venv_python_path() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def setup_python_env(update: bool) -> None:
    if not venv_python_path().exists():
        run_command([sys.executable, "-m", "venv", str(VENV_DIR)], PROJECT_ROOT)

    vpy = str(venv_python_path())
    run_command(
        [
            vpy,
            "-c",
            "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 10) else 1)",
        ],
        PROJECT_ROOT,
    )
    pip_command = [vpy, "-m", "pip", "install"]
    if update:
        pip_command.append("--upgrade")
    run_command(pip_command + ["pip", "setuptools", "wheel"], PROJECT_ROOT)
    run_command(
        pip_command
        + [
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


def platform_paths(platform: str, project_root: Optional[str]) -> tuple[str, str, str]:
    if project_root:
        root = (
            PureWindowsPath(project_root)
            if platform == "windows"
            else PurePosixPath(project_root)
        )
    elif platform == "windows":
        root = (
            PureWindowsPath(PROJECT_ROOT)
            if os.name == "nt"
            else PureWindowsPath(r"C:\path\to\confluence-mcp-server")
        )
    elif platform == "linux":
        root = (
            PurePosixPath(PROJECT_ROOT)
            if sys.platform.startswith("linux")
            else PurePosixPath("/opt/confluence-mcp-server")
        )
    else:
        root = (
            PurePosixPath(PROJECT_ROOT)
            if sys.platform == "darwin"
            else PurePosixPath("/Users/user/Tools/confluence-mcp-server")
        )

    if platform == "windows":
        return (
            str(root / ".venv-mcp" / "Scripts" / "python.exe"),
            str(root / "config" / "app.yaml"),
            str(root / "secrets" / "confluence.yaml"),
        )
    return (
        str(root / ".venv-mcp" / "bin" / "python"),
        str(root / "config" / "app.yaml"),
        str(root / "secrets" / "confluence.yaml"),
    )


def build_kilo_config(platform: str, project_root: Optional[str] = None) -> dict:
    """Конфигурация расширения Kilo Code 7.49+ для VS Code."""
    python_path, config_path, secrets_path = platform_paths(platform, project_root)
    return {
        "mcpServers": {
            "confluence-mcp": {
                "command": python_path,
                "args": ["-m", "confluence_mcp"],
                "env": {
                    "PAGECREATOR_CONFIG_PATH": config_path,
                    "PAGECREATOR_SECRETS_PATH": secrets_path,
                },
                "disabled": False,
                "alwaysAllow": [],
            }
        }
    }


def build_kilo_cli_config(platform: str, project_root: Optional[str] = None) -> dict:
    """Конфигурация актуального Kilo CLI."""
    python_path, config_path, secrets_path = platform_paths(platform, project_root)
    return {
        "mcp": {
            "confluence-mcp": {
                "type": "local",
                "command": [python_path, "-m", "confluence_mcp"],
                "environment": {
                    "PAGECREATOR_CONFIG_PATH": config_path,
                    "PAGECREATOR_SECRETS_PATH": secrets_path,
                },
                "enabled": True,
                "timeout": 30000,
            }
        }
    }


def write_kilo_configs(args: argparse.Namespace) -> list[Path]:
    output_dir = PROJECT_ROOT / ".kilo-generated"
    roots = {
        "windows": args.windows_project_root,
        "linux": args.linux_project_root,
        "macos": args.macos_project_root,
    }
    written = []
    for platform, root in roots.items():
        output = output_dir / f"kilo-vscode.{platform}.json"
        write_text(
            output,
            json.dumps(build_kilo_config(platform, root), ensure_ascii=False, indent=2)
            + "\n",
        )
        written.append(output)
        cli_output = output_dir / f"kilo-cli.{platform}.json"
        write_text(
            cli_output,
            json.dumps(
                build_kilo_cli_config(platform, root),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
        )
        written.append(cli_output)
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Настройка Confluence MCP Server (Python 3.10+)"
    )
    parser.add_argument("--base-url")
    parser.add_argument("--space-key")
    parser.add_argument("--api-token")
    parser.add_argument(
        "--api-token-env",
        help="Взять токен из указанной переменной окружения вместо аргумента командной строки",
    )
    parser.add_argument("--app-template", type=Path)
    parser.add_argument("--confluence-template", type=Path)
    parser.add_argument("--setup-python", action="store_true")
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--skip-config", action="store_true")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--windows-project-root")
    parser.add_argument("--linux-project-root")
    parser.add_argument("--macos-project-root")
    return parser.parse_args()


def resolve_values(args: argparse.Namespace) -> tuple[str, str, str]:
    env_token = os.environ.get(args.api_token_env, "") if args.api_token_env else ""
    supplied_token = args.api_token or env_token
    if args.non_interactive:
        missing = [
            name
            for name, value in (
                ("--base-url", args.base_url),
                ("--space-key", args.space_key),
                ("--api-token или --api-token-env", supplied_token),
            )
            if not value
        ]
        if missing:
            raise SystemExit(
                "Для --non-interactive не заданы: " + ", ".join(missing)
            )
        return args.base_url, args.space_key, supplied_token

    print("Настройка Confluence MCP Server")
    print(f"Проект: {PROJECT_ROOT}\n")
    return (
        args.base_url
        or prompt("Укажи base_url Confluence Server", "https://confluence.example.local"),
        args.space_key or prompt("Укажи default_space_key", "DOC"),
        supplied_token or prompt("Укажи API token", secret=True),
    )


def main() -> int:
    require_supported_python()
    args = parse_args()

    created: list[Path] = []
    if not args.skip_config:
        base_url, space_key, api_token = resolve_values(args)
        values = {
            "CONFLUENCE_BASE_URL": base_url,
            "CONFLUENCE_SPACE_KEY": space_key,
            "CONFLUENCE_API_TOKEN": api_token,
        }
        app_content = (
            render_template(args.app_template, values)
            if args.app_template
            else render_app_yaml(base_url, space_key)
        )
        secrets_content = (
            render_template(args.confluence_template, values)
            if args.confluence_template
            else render_secrets_yaml(api_token)
        )
        write_text(CONFIG_PATH, app_content)
        write_text(SECRETS_PATH, secrets_content)
        created.extend([CONFIG_PATH, SECRETS_PATH])

    created.extend(write_kilo_configs(args))

    if args.setup_python:
        setup_python_env(args.update)

    print("\nГотово.")
    for path in created:
        print(f"- создан {path}")
    if args.setup_python:
        print(f"- Python 3.10+ окружение подготовлено: {VENV_DIR}")
    print("\nЗапуск MCP:")
    print(f"- Windows: {PROJECT_ROOT / 'scripts' / 'run_mcp.ps1'}")
    print(f"- Linux/macOS: {PROJECT_ROOT / 'scripts' / 'run_mcp.sh'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
