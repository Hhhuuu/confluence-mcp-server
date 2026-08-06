[CmdletBinding()]
param(
    [string]$BaseUrl,
    [string]$SpaceKey,
    [string]$ApiToken,
    [string]$ApiTokenEnv,
    [string]$AppTemplate,
    [string]$ConfluenceTemplate,
    [switch]$Update,
    [switch]$NonInteractive,
    [switch]$SkipConfig
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$PythonExecutable = $null
$PythonArgs = @()
$PyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($PyLauncher) {
    foreach ($Selector in @("-3.10", "-3")) {
        & $PyLauncher.Source $Selector -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 10) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $PythonExecutable = $PyLauncher.Source
            $PythonArgs = @($Selector)
            break
        }
    }
}

if (-not $PythonExecutable) {
    foreach ($CommandName in @("python3.10", "python3", "python")) {
        $Candidate = Get-Command $CommandName -ErrorAction SilentlyContinue
        if ($Candidate) {
            & $Candidate.Source -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 10) else 1)"
            if ($LASTEXITCODE -eq 0) {
                $PythonExecutable = $Candidate.Source
                break
            }
        }
    }
}

if (-not $PythonExecutable) {
    throw "Не найден Python 3.10 или новее. Установи его и проверь 'py -3 --version'."
}

$Arguments = @($PythonArgs) + @((Join-Path $PSScriptRoot "bootstrap_mcp.py"), "--setup-python", "--windows-project-root", $ProjectRoot)
if ($BaseUrl) { $Arguments += @("--base-url", $BaseUrl) }
if ($SpaceKey) { $Arguments += @("--space-key", $SpaceKey) }
if ($ApiToken) { $Arguments += @("--api-token", $ApiToken) }
if ($ApiTokenEnv) { $Arguments += @("--api-token-env", $ApiTokenEnv) }
if ($AppTemplate) { $Arguments += @("--app-template", $AppTemplate) }
if ($ConfluenceTemplate) { $Arguments += @("--confluence-template", $ConfluenceTemplate) }
if ($Update) { $Arguments += "--update" }
if ($NonInteractive) { $Arguments += "--non-interactive" }
if ($SkipConfig) { $Arguments += "--skip-config" }

& $PythonExecutable @Arguments
exit $LASTEXITCODE
