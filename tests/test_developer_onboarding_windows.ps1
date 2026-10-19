# Self-contained Windows regression; Docker/WSL are controlled adapters, no Pester required.
$ErrorActionPreference='Stop'
$repository=Split-Path $PSScriptRoot
$scratch=Join-Path $repository ('.local/onboarding-acl-tests/'+[guid]::NewGuid().ToString())
$shell=(Get-Process -Id $PID).Path
$adapter=Join-Path $PSScriptRoot 'fixtures/dev_windows_adapter.ps1'
$cases=0
function Invoke-Case([string]$Root,[string]$Scenario,[int]$Expected) {
    $output=& $shell -NoProfile -File $adapter -Root $Root -Scenario $Scenario 2>&1 | Out-String
    if ($LASTEXITCODE -ne $Expected) { throw "Scenario $Scenario returned $LASTEXITCODE instead of $Expected. $output" }
    if ($output -match 'synthetic-regression-password') { throw 'Password appeared in output.' }
    $script:cases++
}
function New-Checkout([string]$Name) {
    $root=Join-Path $scratch $Name
    New-Item -ItemType Directory -Force (Join-Path $root 'docker') | Out-Null
    Copy-Item (Join-Path $repository 'dev.ps1') (Join-Path $root 'dev.ps1')
    Copy-Item (Join-Path $repository 'docker/api.Dockerfile') (Join-Path $root 'docker/api.Dockerfile')
    return $root
}
function Assert-Private([string]$Path) {
    $acl=Get-Acl -LiteralPath $Path
    $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    if (-not $acl.AreAccessRulesProtected -or @($acl.Access | Where-Object { $_.IsInherited -or $_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -ne $sid }).Count) { throw 'New file is not current-user only.' }
}
$savedWeb=$env:FINCATHON_WEB_PORT; $savedApi=$env:FINCATHON_API_PORT
$listeners=@()
try {
    # Ask Windows for free explicit ports, then release before the child preflight.
    foreach ($i in 1..2) { $listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,0); $listener.Start(); $listeners+=,$listener }
    $env:FINCATHON_WEB_PORT=[string]$listeners[0].LocalEndpoint.Port
    $env:FINCATHON_API_PORT=[string]$listeners[1].LocalEndpoint.Port
    foreach ($listener in $listeners) { $listener.Stop() }
    foreach ($failure in @('build-failure','partial-failure')) {
        $root=New-Checkout $failure
        Invoke-Case $root $failure $(if ($failure -eq 'build-failure') {37} else {23})
        $password=Join-Path $root '.local/db-password'
        Assert-Private $password
        $hash=(Get-FileHash -LiteralPath $password).Hash
        if ($failure -eq 'build-failure') { Assert-Private (Join-Path $root '.env') }
        Invoke-Case $root 'success' 0
        Assert-Private $password; Assert-Private (Join-Path $root '.env')
        if ((Get-FileHash -LiteralPath $password).Hash -ne $hash) { throw 'Retry replaced the password.' }
    }
    $root=New-Checkout 'existing'
    New-Item -ItemType Directory -Force (Join-Path $root '.local') | Out-Null
    $snapshots=@{}
    foreach ($name in @('.env','.local/db-password')) {
        $path=Join-Path $root $name; [IO.File]::WriteAllText($path,'existing-operator-configuration')
        $snapshots[$name]=@((Get-FileHash -LiteralPath $path).Hash,(Get-Acl -LiteralPath $path).Sddl)
    }
    Invoke-Case $root 'existing' 0
    foreach ($name in $snapshots.Keys) {
        $path=Join-Path $root $name
        if ((Get-FileHash -LiteralPath $path).Hash -ne $snapshots[$name][0] -or (Get-Acl -LiteralPath $path).Sddl -ne $snapshots[$name][1]) { throw 'Existing operator file or ACL changed.' }
    }
    foreach ($scenario in @('native-partial-failure','native-build-failure')) {
        $root=New-Checkout $scenario
        Invoke-Case $root $scenario 1
        Assert-Private (Join-Path $root '.local/db-password')
        if ($scenario -eq 'native-build-failure') { Assert-Private (Join-Path $root '.env') }
    }
    "Windows private-file regression: $cases launcher cases passed."
} finally {
    foreach ($listener in $listeners) { $listener.Stop() }
    $env:FINCATHON_WEB_PORT=$savedWeb; $env:FINCATHON_API_PORT=$savedApi
}
