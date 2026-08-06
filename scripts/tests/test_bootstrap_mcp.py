from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "bootstrap_mcp.py"
SPEC = importlib.util.spec_from_file_location("bootstrap_mcp", SCRIPT_PATH)
assert SPEC and SPEC.loader
bootstrap_mcp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap_mcp)


class BootstrapMcpTests(unittest.TestCase):
    def test_supported_python_requires_at_least_310(self) -> None:
        self.assertEqual(bootstrap_mcp.MINIMUM_PYTHON, (3, 10))

    def test_default_yaml_escapes_user_values(self) -> None:
        rendered = bootstrap_mcp.render_secrets_yaml('token"with\\symbols')

        self.assertIn('api_token: "token\\"with\\\\symbols"', rendered)

    def test_custom_template_replaces_supported_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            template = Path(temp_dir) / "app.yaml.template"
            template.write_text(
                "url: ${CONFLUENCE_BASE_URL}\nspace: ${CONFLUENCE_SPACE_KEY}",
                encoding="utf-8",
            )
            rendered = bootstrap_mcp.render_template(
                template,
                {
                    "CONFLUENCE_BASE_URL": "https://confluence.local",
                    "CONFLUENCE_SPACE_KEY": "DOC",
                },
            )

        self.assertEqual(
            rendered,
            "url: https://confluence.local\nspace: DOC\n",
        )

    def test_windows_kilo_config_uses_absolute_windows_paths(self) -> None:
        config = bootstrap_mcp.build_kilo_config(
            "windows", r"D:\Tools\confluence-mcp-server"
        )
        server = config["mcpServers"]["confluence-mcp"]

        self.assertEqual(
            server["command"],
            r"D:\Tools\confluence-mcp-server\.venv-mcp\Scripts\python.exe",
        )
        self.assertEqual(server["args"], ["-m", "confluence_mcp"])
        self.assertEqual(
            server["env"]["PAGECREATOR_CONFIG_PATH"],
            r"D:\Tools\confluence-mcp-server\config\app.yaml",
        )

    def test_linux_kilo_config_uses_absolute_posix_paths(self) -> None:
        config = bootstrap_mcp.build_kilo_config(
            "linux", "/opt/confluence-mcp-server"
        )
        server = config["mcpServers"]["confluence-mcp"]

        self.assertEqual(
            server["command"],
            "/opt/confluence-mcp-server/.venv-mcp/bin/python",
        )

    def test_windows_kilo_cli_config_uses_current_cli_format(self) -> None:
        config = bootstrap_mcp.build_kilo_cli_config(
            "windows", r"D:\Tools\confluence-mcp-server"
        )
        server = config["mcp"]["confluence-mcp"]

        self.assertEqual(server["type"], "local")
        self.assertEqual(
            server["command"],
            [
                r"D:\Tools\confluence-mcp-server\.venv-mcp\Scripts\python.exe",
                "-m",
                "confluence_mcp",
            ],
        )
        self.assertEqual(
            server["environment"]["PAGECREATOR_SECRETS_PATH"],
            r"D:\Tools\confluence-mcp-server\secrets\confluence.yaml",
        )
        self.assertTrue(server["enabled"])


if __name__ == "__main__":
    unittest.main()
