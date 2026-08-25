<#
.SYNOPSIS
    LM Studio Egress Probe - Windows native companion for PID-attributed monitoring.
.DESCRIPTION
    Runs alongside WSL-side egress probe. Captures TCP connections and DNS queries
    attributed to LM Studio processes on Windows (invisible from WSL).
.PARAMETER Duration
    Monitoring duration in seconds (default: 120).
.PARAMETER OutputDir
    Directory for output JSON report (default: current directory).
#>
param(
    [int]$Duration = 120,
    [string]$OutputDir = "."
)
$ReportPath = Join-Path $OutputDir "lms_egress_windows_report.json"
$IntervalSeconds = 2
$LMSProcessNames = @("LM Studio", "llama-server", "lmstudio")
function Get-LMStudioProcesses {
    $procs = @()
    foreach ($name in $LMSProcessNames) {
        $procs += Get-Process -Name $name -ErrorAction SilentlyContinue
    }
    return $procs | Sort-Object Id -Unique
}
function Get-ProcessTree {
    param([int]$ParentPID)
    $children = @()
    $all = Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $ParentPID }
    foreach ($c in $all) {
        $children += $c.ProcessId
        $children += Get-ProcessTree -ParentPID $c.ProcessId
    }
    return $children
}
$Snapshots = @()
$DNSQueries = @()
$StartTime = Get-Date
Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Windows egress probe started (${Duration}s)"
while ((Get-Date) - $StartTime -lt [TimeSpan]::FromSeconds($Duration)) {
    $lmsProcs = Get-LMStudioProcesses
    $allPids = @($lmsProcs | ForEach-Object { $_.Id })
    foreach ($p in $lmsProcs) {
        $allPids += Get-ProcessTree -ParentPID $p.Id
    }
    $snapshot = @{ Timestamp = (Get-Date -Format "o"); LMSPIDs = $allPids }
    $connections = @()
    foreach ($pid in $allPids) {
        try {
            $tcpConns = Get-NetTCPConnection -OwningProcess $pid -ErrorAction SilentlyContinue |
                Select-Object LocalAddress, LocalPort, RemoteAddress, RemotePort, State, OwningProcess
            foreach ($c in $tcpConns) {
                $connections += @{ PID=$pid; LocalAddress=$c.LocalAddress; LocalPort=$c.LocalPort; RemoteAddress=$c.RemoteAddress; RemotePort=$c.RemotePort; State=$c.State }
            }
        } catch {}
    }
    $snapshot.Connections = $connections
    # Check for recent DNS events
    $dnsEvents = @()
    try {
        $dnsEvents = Get-WinEvent -FilterHashtable @{
            LogName='Microsoft-Windows-DNS-Client/Operational'
            ID=3006; StartTime=(Get-Date).AddSeconds(-5)
        } -ErrorAction SilentlyContinue | Select-Object -First 20 |
            ForEach-Object { @{ Timestamp=$_.TimeCreated; QueryName=$_.Properties[0].Value; QueryType=$_.Properties[1].Value } }
    } catch {}
    if ($dnsEvents.Count -gt 0) { $DNSQueries += $dnsEvents }
    $Snapshots += $snapshot
    Start-Sleep -Seconds $IntervalSeconds
}
Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Compiling report..."
$allConns = @()
foreach ($s in $Snapshots) { $allConns += $s.Connections }
$externalConns = $allConns | Where-Object {
    $_.RemoteAddress -notmatch '^127\.' -and $_.RemoteAddress -notmatch '^::1$' -and
    $_.RemoteAddress -notmatch '^0\.0\.0\.0$' -and $_.RemoteAddress -notmatch '^10\.' -and
    $_.RemoteAddress -notmatch '^172\.(1[6-9]|2[0-9]|3[01])\.' -and $_.RemoteAddress -notmatch '^192\.168\.'
}
$report = @{
    Timestamp=(Get-Date -Format "o")
    DurationSeconds=$Duration
    TotalSnapshots=$Snapshots.Count
    TotalDNSQueries=$DNSQueries.Count
    UniqueExternalConnections=($externalConns | ForEach-Object { "$($_.RemoteAddress):$($_.RemotePort)($($_.State))" } | Sort-Object -Unique)
    ExternalConnectionCount=($externalConns | ForEach-Object { "$($_.RemoteAddress):$($_.RemotePort)" } | Sort-Object -Unique).Count
    DNSQueries=$DNSQueries | Select-Object -First 50
    Finding=if ($externalConns.Count -gt 0) { "External connections detected: $(($externalConns | ForEach-Object { "$($_.RemoteAddress):$($_.RemotePort)" } | Sort-Object -Unique) -join ', ')" } else { "No external connections detected" }
}
$reportJson = ConvertTo-Json $report -Depth 10
$reportJson | Out-File -FilePath $ReportPath -Encoding utf8
Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Report saved to $ReportPath"
Write-Host "External connections: $($report.ExternalConnectionCount)"
Write-Host $report.Finding
