[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPython = Join-Path $ProjectRoot ".venv-mcp\Scripts\python.exe"
$ConfigPath = if ($env:PAGECREATOR_CONFIG_PATH) { $env:PAGECREATOR_CONFIG_PATH } else { Join-Path $ProjectRoot "config\app.yaml" }
$SecretsPath = if ($env:PAGECREATOR_SECRETS_PATH) { $env:PAGECREATOR_SECRETS_PATH } else { Join-Path $ProjectRoot "secrets\confluence.yaml" }

if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
    throw "Не найден Python MCP-окружения: $VenvPython. Запусти scripts\setup_mcp.ps1."
}
if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    throw "Не найден конфиг: $ConfigPath. Запусти scripts\setup_mcp.ps1."
}
if (-not (Test-Path -LiteralPath $SecretsPath -PathType Leaf)) {
    throw "Не найден файл подключения Confluence: $SecretsPath. Запусти scripts\setup_mcp.ps1."
}

$Version = & $VenvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
& $VenvPython -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "MCP должен запускаться под Python 3.10 или новее, найден Python $Version."
}

$env:PAGECREATOR_CONFIG_PATH = $ConfigPath
$env:PAGECREATOR_SECRETS_PATH = $SecretsPath
& $VenvPython -m confluence_mcp
exit $LASTEXITCODE
