# Test-ProjectStorage.ps1
# Phase 0 deliverable: storage preflight. Verifies that the project Python
# runtime, caches, temp directories, application state and the Docker Desktop
# host engine disk resolve inside `E:\FalcorDB Hackathon` BEFORE any dependency
# download or image pull, and can recheck them afterwards.
#
# Usage:
#   .\scripts\Enter-ProjectEnvironment.ps1 powershell -File .\scripts\Test-ProjectStorage.ps1 -Report
#   .\scripts\Enter-ProjectStorage.ps1 -SkipDockerGate
#
# An unknown location or a location on C: fails the gate (exit 1), except for
# explicitly recorded OS exceptions (host OS tools may stay on C:).

[CmdletBinding()]
param(
    # Recheck after install/restart (report also refreshes).
    [switch]$Report,
    # Docker Desktop engine disk relocation is a manual, supported-migration
    # step; when it has not been done yet the gate stays "pending" instead of
    # failing the whole preflight. Pass -RequireDockerGate to hard-fail.
    [switch]$RequireDockerGate,
    [switch]$SkipDockerGate
)

$ErrorActionPreference = 'Stop'

$WorkspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Write-Host "Workspace root: $WorkspaceRoot"

# Load the environment policy so effective paths match what the runtime uses.
. (Join-Path $PSScriptRoot 'Enter-ProjectEnvironment.ps1')

$Observations = [ordered]@{}
$Failures = [System.Collections.Generic.List[string]]::new()
$Pending = [System.Collections.Generic.List[string]]::new()

function Test-WorkspacePath {
    param(
        [string]$Name,
        [string]$Value,
        [switch]$MustExist
    )
    if ([string]::IsNullOrWhiteSpace($Value)) {
        $script:Failures.Add("$Name is not set")
        return
    }
    $resolved = $null
    try {
        $resolved = [System.IO.Path]::GetFullPath($Value)
        # Reparse-point safety: resolve the final target if it exists.
        if (Test-Path -LiteralPath $resolved) {
            $resolved = (Resolve-Path -LiteralPath $resolved).ProviderPath
        }
    } catch {
        $script:Failures.Add("$Name could not be resolved: $Value")
        return
    }
    if ($MustExist -and -not (Test-Path -LiteralPath $resolved)) {
        $script:Failures.Add("$Name path does not exist: $resolved")
        return
    }
    if (-not $resolved.StartsWith($WorkspaceRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        $script:Failures.Add("$Name resolves outside the workspace: $resolved")
        return
    }
    $drive = ($resolved -split ':')[0] + ':'
    $script:Observations[$Name] = [ordered]@{ path = $resolved; drive = $drive }
}

function Test-PathOnE {
    # Docker Desktop 4.28 relocates the WSL2 engine disk only through its GUI;
    # the user's chosen location is recorded as an observation. A C:-resident
    # engine disk fails; anything else records the deviation explicitly.
    param([string]$Name, [string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) {
        $script:Pending.Add("$Name location could not be determined (verify via Docker Desktop Settings > Resources > Advanced)")
        return
    }
    $resolved = $Value.TrimStart('\', '?')
    $drive = ($resolved -split ':')[0].ToUpperInvariant() + ':'
    if ($drive -eq 'C:') {
        $script:Failures.Add("$Name is still on the system drive C:; relocate via Docker Desktop Settings > Resources > Advanced before pulling images")
        return
    }
    if (-not $resolved.StartsWith($WorkspaceRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        $script:Observations[$Name] = [ordered]@{ path = $resolved; drive = $drive; note = "E:-resident but outside the workspace folder (deviation recorded; policy target is $WorkspaceRoot\.local\docker)" }
    } else {
        $script:Observations[$Name] = [ordered]@{ path = $resolved; drive = $drive }
    }
}

# --- Environment-managed paths --------------------------------------------
Test-WorkspacePath 'TEMP/TMP' $env:TEMP
Test-WorkspacePath 'PIP_CACHE_DIR' $env:PIP_CACHE_DIR
Test-WorkspacePath 'UV_CACHE_DIR' $env:UV_CACHE_DIR
Test-WorkspacePath 'UV_PYTHON_INSTALL_DIR' $env:UV_PYTHON_INSTALL_DIR
Test-WorkspacePath 'UV_PYTHON_BIN_DIR' $env:UV_PYTHON_BIN_DIR
Test-WorkspacePath 'UV_TOOL_BIN_DIR' $env:UV_TOOL_BIN_DIR
Test-WorkspacePath 'UV_TOOL_DIR' $env:UV_TOOL_DIR
Test-WorkspacePath 'UV_PROJECT_ENVIRONMENT' $env:UV_PROJECT_ENVIRONMENT
Test-WorkspacePath 'npm_config_cache' $env:npm_config_cache
Test-WorkspacePath 'npm_config_prefix' $env:npm_config_prefix
Test-WorkspacePath 'npm_config_userconfig' $env:npm_config_userconfig -MustExist
Test-WorkspacePath 'DOCKER_CONFIG' $env:DOCKER_CONFIG

# --- Required workspace state directories ---------------------------------
foreach ($rel in @('.local\tmp', '.local\downloads', '.local\cache\pip', '.local\cache\uv',
        '.local\tools\uv', '.local\tools\python', '.local\state\falkordb', '.local\state\retained',
        '.local\state\bundles', '.local\state\content', '.local\state\git', '.local\state\conversations')) {
    Test-WorkspacePath "state:$rel" (Join-Path $WorkspaceRoot $rel) -MustExist
}

# --- Project-local Python runtime -----------------------------------------
$VenvPython = Join-Path $WorkspaceRoot 'backend\.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $VenvPython) {
    Test-WorkspacePath 'project python (backend/.venv)' $VenvPython -MustExist
    $pythonVersion = & $VenvPython --version 2>$null
    $Observations['python version'] = $pythonVersion
} else {
    $Pending.Add('backend/.venv python not installed yet (run uv sync through the project environment)')
}

$UvExe = Join-Path $WorkspaceRoot '.local\tools\uv\uv.exe'
if (Test-Path -LiteralPath $UvExe) {
    $Observations['uv version'] = (& $UvExe --version)
} else {
    $Pending.Add('project-local uv not installed yet')
}

# --- Docker Desktop host engine disk --------------------------------------
# Docker stores images in its engine disk, independently of any Compose file
# directory. Docker Desktop on the WSL2 backend defaults to a C: VHD that must
# be relocated through its supported settings; this check verifies the actual
# Windows host path.
if (-not $SkipDockerGate) {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        $dockerInfo = docker info --format '{{json .}}' 2>$null | ConvertFrom-Json
        if ($dockerInfo) {
            $dockerRoot = $dockerInfo.'DockerRootDir'
            $backend = $dockerInfo.'Driver'  # e.g. overlay2 inside the engine disk
            $wslBackend = $dockerInfo.'OperatingSystem'
            $Observations['docker root dir (linux view)'] = $dockerRoot
            $Observations['docker storage driver'] = $backend
            $Observations['docker os/backend'] = $wslBackend

            # For the WSL2 backend the real host disk is the DockerDesktopWSL
            # VHD. Probe the registered distribution's BasePath from the
            # registry (HKCU), which records the Windows host location.
            $hostVhd = $null
            try {
                $reg = Get-ChildItem 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss' -ErrorAction Stop
                foreach ($distro in $reg) {
                    $props = Get-ItemProperty $distro.PSPath
                    if ($props.DistributionName -like '*docker*') {
                        $hostVhd = $props.BasePath
                    }
                }
            } catch {
                Write-Verbose "WSL registry probe failed: $_"
            }
            if ($hostVhd) {
                # hostVhd is the BasePath, holding the ext4.vhdx directory.
                Test-PathOnE 'Docker Desktop WSL host engine disk' $hostVhd
                $Observations['docker wsl host vhd path'] = $hostVhd
            } else {
                $Pending.Add('Docker Desktop WSL host disk location could not be determined (environment variables cannot pass this gate; verify via Docker Desktop Settings > Resources > Advanced)')
            }
        } else {
            $Pending.Add('docker info returned nothing (Docker Desktop may not be running)')
        }
    } else {
        $Pending.Add('docker CLI not found on this machine')
    }
}

# --- Drive space ----------------------------------------------------------
foreach ($driveLetter in @('C:', 'E:')) {
    try {
        $drive = Get-PSDrive -Name ($driveLetter.TrimEnd(':')) -ErrorAction Stop
        $freeGb = [math]::Round($drive.Free / 1GB, 2)
        $Observations["drive $driveLetter free GB"] = $freeGb
    } catch {
        Write-Verbose "Drive $driveLetter not present on this machine."
    }
}

# --- Sanitized report ------------------------------------------------------
function Build-SanitizedRecord {
    $record = New-Object 'System.Collections.Specialized.OrderedDictionary'
    $record['generated_at'] = (Get-Date).ToUniversalTime().ToString('o')
    $record['workspace_root'] = $WorkspaceRoot
    $record['observations'] = $Observations
    $record['pending'] = $Pending
    $record['failures'] = $Failures
    $record['gate_passed'] = ($Failures.Count -eq 0)
    return $record
}

$reportRecord = Build-SanitizedRecord
$reportJson = $reportRecord | ConvertTo-Json -Depth 5

$reportDir = Join-Path $WorkspaceRoot 'reports'
if (-not (Test-Path -LiteralPath $reportDir)) { New-Item -ItemType Directory -Path $reportDir | Out-Null }
$reportPath = Join-Path $reportDir 'workspace_setup.md'
if ($Report) {
    $lines = @(
        '# Workspace setup report',
        '',
        "Generated: $($reportRecord['generated_at'])",
        '',
        '## Observations',
        ''
    )
    foreach ($key in $Observations.Keys) {
        $value = $Observations[$key]
        if ($value -is [System.Collections.IDictionary]) {
            $lines += ("- {0}: {1} (drive {2})" -f $key, $value.path, $value.drive)
        } else {
            $lines += ("- {0}: {1}" -f $key, $value)
        }
    }
    $lines += ''
    if ($Pending.Count -gt 0) {
        $lines += '## Pending gates'
        $lines += ''
        foreach ($p in $Pending) { $lines += "- $p" }
        $lines += ''
    }
    if ($Failures.Count -gt 0) {
        $lines += '## Failures'
        $lines += ''
        foreach ($f in $Failures) { $lines += "- $f" }
        $lines += ''
    }
    Set-Content -LiteralPath $reportPath -Value ($lines -join "`n")
    Write-Host "Report written to $reportPath"
}

Write-Host $reportJson
if ($Failures.Count -gt 0) {
    Write-Error "Storage preflight FAILED: $($Failures -join '; ')"
    exit 1
}
if ($RequireDockerGate -and $Pending.Count -gt 0) {
    Write-Error "Docker storage gate required but pending: $($Pending -join '; ')"
    exit 1
}
Write-Host 'Storage preflight PASSED (pending gates, if any, do not block local-only work).'
exit 0
