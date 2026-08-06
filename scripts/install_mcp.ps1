[CmdletBinding()]
param(
    [string]$Repository = "https://github.com/Hhhuuu/confluence-mcp-server.git",
    [string]$InstallDirectory = (Join-Path $PWD "confluence-mcp-server"),
    [switch]$Update,
    [string[]]$SetupArguments = @()
)

$ErrorActionPreference = "Stop"
$InstallDirectory = [System.IO.Path]::GetFullPath($InstallDirectory)

if (Test-Path -LiteralPath (Join-Path $InstallDirectory ".git")) {
    if ($Update) {
        git -C $InstallDirectory pull --ff-only
        if ($LASTEXITCODE -ne 0) { throw "Не удалось обновить репозиторий." }
    }
} elseif (Test-Path -LiteralPath $InstallDirectory) {
    throw "Каталог уже существует и не является git-репозиторием: $InstallDirectory"
} else {
    git clone $Repository $InstallDirectory
    if ($LASTEXITCODE -ne 0) { throw "Не удалось клонировать репозиторий." }
}

& (Join-Path $InstallDirectory "scripts\setup_mcp.ps1") @SetupArguments
exit $LASTEXITCODE
