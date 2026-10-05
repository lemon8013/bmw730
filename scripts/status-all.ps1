#Requires -Version 5.1
<#
.SYNOPSIS
    Report whether the three VCTN dev services are answering.
#>
Set-StrictMode -Version Latest

$services = @(
    @{ Name = 'vctn-api';        Url = 'http://localhost:8000/version' }
    @{ Name = 'vctn-admin-web';  Url = 'http://localhost:5173/' }
    @{ Name = 'vctn-tools-web';  Url = 'http://localhost:5174/' }
)

foreach ($svc in $services) {
    try {
        $r = Invoke-WebRequest -Uri $svc.Url -TimeoutSec 6 -UseBasicParsing
        Write-Host ("  [UP  ] {0,-16} {1} -> {2}" -f $svc.Name, $svc.Url, $r.StatusCode)
    }
    catch {
        Write-Host ("  [DOWN] {0,-16} {1} -> {2}" -f $svc.Name, $svc.Url, $_.Exception.Message)
    }
}
