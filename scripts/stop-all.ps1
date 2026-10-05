#Requires -Version 5.1
<#
.SYNOPSIS
    Stop the VCTN dev services started by start-all.ps1.

.DESCRIPTION
    Resolves the listeners on ports 8000 / 5173 / 5174 and stops their owning
    processes. Skips ports that nothing is listening on.
#>
Set-StrictMode -Version Latest

$ports = @(8000, 5173, 5174)

foreach ($port in $ports) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($null -eq $conn) {
        Write-Host "  [-- ] port $port not listening"
        continue
    }
    $conn | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
        $owner = Get-Process -Id $_ -ErrorAction SilentlyContinue
        Write-Host "  [KILL] port $port -> pid $_ ($($owner.ProcessName))"
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
    }
}

Write-Host 'done'
