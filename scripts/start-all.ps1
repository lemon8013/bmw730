#Requires -Version 5.1
<#
.SYNOPSIS
    Start the three VCTN dev services (API, admin web, tools web).

.DESCRIPTION
    Each service launches with Start-Process so it outlives this shell.
    Logs land in scripts/logs/dev-<name>.out.log / .err.log.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts/start-all.ps1
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$python = Join-Path $root 'vctn-api/.venv/Scripts/python.exe'

$services = @(
    @{
        Name = 'vctn-api'
        Dir  = Join-Path $root 'vctn-api'
        File = $python
        Args = '-m uvicorn app.main:app --host 127.0.0.1 --port 8000'
        Url  = 'http://localhost:8000/version'
    }
    @{
        Name = 'vctn-admin-web'
        Dir  = Join-Path $root 'vctn-admin-web'
        File = 'cmd.exe'
        Args = '/c npm run dev'
        Url  = 'http://localhost:5173/'
    }
    @{
        Name = 'vctn-tools-web'
        Dir  = Join-Path $root 'vctn-tools-web'
        File = 'cmd.exe'
        Args = '/c npm run dev'
        Url  = 'http://localhost:5174/'
    }
)

$pids = @{}

foreach ($svc in $services) {
    if ($svc.Name -eq 'vctn-api' -and -not (Test-Path $python)) {
        throw "python not found at $python"
    }

    Write-Host "starting $($svc.Name) ..."
    $proc = Start-Process `
        -FilePath $svc.File `
        -ArgumentList $svc.Args `
        -WorkingDirectory $svc.Dir `
        -RedirectStandardOutput (Join-Path $logDir "dev-$($svc.Name).out.log") `
        -RedirectStandardError (Join-Path $logDir "dev-$($svc.Name).err.log") `
        -WindowStyle Hidden `
        -PassThru

    $pids[$svc.Name] = $proc.Id
    Write-Host "  pid $($proc.Id)"
}

$pids.Keys | ForEach-Object { "$_ = $($pids[$_])" } | Out-File -FilePath (Join-Path $logDir 'pids.txt') -Encoding ascii

Write-Host ''
Write-Host 'waiting for ports ...'
Start-Sleep -Seconds 14

foreach ($svc in $services) {
    try {
        $r = Invoke-WebRequest -Uri $svc.Url -TimeoutSec 10 -UseBasicParsing
        Write-Host ("  [OK ] {0,-16} {1} -> {2}" -f $svc.Name, $svc.Url, $r.StatusCode)
    }
    catch {
        Write-Host ("  [ERR] {0,-16} {1} -> {2}" -f $svc.Name, $svc.Url, $_.Exception.Message)
    }
}
