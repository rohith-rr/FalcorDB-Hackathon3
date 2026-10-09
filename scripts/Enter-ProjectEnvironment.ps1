# Enter-ProjectEnvironment.ps1
# Phase 0 deliverable: applies the workspace storage policy
# (docs/design/workspace_setup.md) to the current process and its children.
#
# Usage:  . .\scripts\Enter-ProjectEnvironment.ps1
#         .\scripts\Enter-ProjectEnvironment.ps1 python --version   (run-through mode)
#
# The script derives the workspace root from its own location, creates only
# workspace directories, and never changes HOME/USERPROFILE/APPDATA/
# LOCALAPPDATA/CODEX_HOME or machine-wide package settings.

[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CommandArguments
)

$ErrorActionPreference = 'Stop'

# Derive the workspace root from this script's location (scripts/ is one level down).
$WorkspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Write-Verbose "Workspace root: $WorkspaceRoot"

function Join-Workspace {
    param([string]$Relative)
    $full = [System.IO.Path]::GetFullPath((Join-Path $WorkspaceRoot $Relative))
    if (-not $full.StartsWith($WorkspaceRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Resolved path '$full' escapes the workspace root '$WorkspaceRoot'."
    }
    return $full
}

# --- Directories required by the workspace policy -------------------------
$Directories = @(
    (Join-Workspace '.local\tmp'),
    (Join-Workspace '.local\downloads'),
    (Join-Workspace '.local\cache\pip'),
    (Join-Workspace '.local\cache\uv'),
    (Join-Workspace '.local\cache\npm'),
    (Join-Workspace '.local\tools\uv'),
    (Join-Workspace '.local\tools\python'),
    (Join-Workspace '.local\tools\bin'),
    (Join-Workspace '.local\tools\uv-tools'),
    (Join-Workspace '.local\tools\npm'),
    (Join-Workspace '.local\config'),
    (Join-Workspace '.local\secrets'),
    (Join-Workspace '.local\logs'),
    (Join-Workspace '.local\state\falkordb'),
    (Join-Workspace '.local\state\retained'),
    (Join-Workspace '.local\state\bundles'),
    (Join-Workspace '.local\state\content'),
    (Join-Workspace '.local\state\git'),
    (Join-Workspace '.local\state\conversations')
)
foreach ($dir in $Directories) {
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# --- Environment settings (docs/design/workspace_setup.md) ----------------
$TempDir = Join-Workspace '.local\tmp'
$env:TEMP = $TempDir
$env:TMP = $TempDir
$env:TMPDIR = $TempDir

$env:PIP_CACHE_DIR = Join-Workspace '.local\cache\pip'
$env:UV_CACHE_DIR = Join-Workspace '.local\cache\uv'
$env:UV_PYTHON_INSTALL_DIR = Join-Workspace '.local\tools\python'
$env:UV_PYTHON_BIN_DIR = Join-Workspace '.local\tools\bin'
$env:UV_TOOL_BIN_DIR = Join-Workspace '.local\tools\bin'
$env:UV_TOOL_DIR = Join-Workspace '.local\tools\uv-tools'
$env:UV_PROJECT_ENVIRONMENT = Join-Workspace 'backend\.venv'
$env:PYTHONNOUSERSITE = '1'

$env:npm_config_cache = Join-Workspace '.local\cache\npm'
$env:npm_config_prefix = Join-Workspace '.local\tools\npm'
$env:npm_config_userconfig = Join-Workspace '.local\config\npmrc'
if (-not (Test-Path -LiteralPath $env:npm_config_userconfig)) {
    Set-Content -LiteralPath $env:npm_config_userconfig -Value '' -NoNewline
}

$env:DOCKER_CONFIG = Join-Workspace '.local\config\docker'

# --- Project-local uv executable -----------------------------------------
$UvExecutable = Join-Workspace '.local\tools\uv\uv.exe'
if (Test-Path -LiteralPath $UvExecutable) {
    # Put the project-local uv first on PATH for this process and children.
    $uvDir = Split-Path -Parent $UvExecutable
    if (-not (($env:PATH -split ';') -contains $uvDir)) {
        $env:PATH = "$uvDir;$env:PATH"
    }
}

# --- Backend venv activation (when present) -------------------------------
$VenvHome = Join-Workspace 'backend\.venv'
$VenvScripts = Join-Path $VenvHome 'Scripts'
if (Test-Path -LiteralPath (Join-Path $VenvScripts 'python.exe')) {
    if (-not (($env:PATH -split ';') -contains $VenvScripts)) {
        $env:PATH = "$VenvScripts;$env:PATH"
    }
    $env:VIRTUAL_ENV = $VenvHome
}

# --- Summary --------------------------------------------------------------
Write-Host "Project environment applied (workspace: $WorkspaceRoot)"
Write-Host "  TEMP/TMP:            $env:TEMP"
Write-Host "  PIP_CACHE_DIR:       $env:PIP_CACHE_DIR"
Write-Host "  UV_CACHE_DIR:        $env:UV_CACHE_DIR"
Write-Host "  UV_PYTHON_INSTALL_DIR: $env:UV_PYTHON_INSTALL_DIR"
Write-Host "  UV_PROJECT_ENVIRONMENT: $env:UV_PROJECT_ENVIRONMENT"
Write-Host "  DOCKER_CONFIG:       $env:DOCKER_CONFIG"
if (Test-Path -LiteralPath $UvExecutable) {
    Write-Host "  uv:                  $UvExecutable"
} else {
    Write-Warning "uv is not installed at $UvExecutable; run the bootstrap in scripts/Test-ProjectStorage.ps1 notes or download the pinned archive to .local\tools\uv."
}
if ($env:VIRTUAL_ENV) {
    Write-Host "  VIRTUAL_ENV:         $env:VIRTUAL_ENV"
}

# --- Run-through mode -----------------------------------------------------
if ($CommandArguments) {
    & @($CommandArguments)
    exit $LASTEXITCODE
}
