param([string]$Root,[string]$Scenario)
$ErrorActionPreference='Stop'
function Assert-PrivateFiles {
    if ($Scenario -eq 'existing') { return }
    $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    foreach ($name in @('.env','.local/db-password')) {
        $acl=Get-Acl -LiteralPath (Join-Path $Root $name)
        if (-not $acl.AreAccessRulesProtected -or @($acl.Access | Where-Object { $_.IsInherited -or $_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -ne $sid }).Count) {
            throw 'Private files were not restricted before build.'
        }
    }
}
function Prepare-TestFiles {
    New-Item -ItemType Directory -Force (Join-Path $Root '.local') | Out-Null
    $password=Join-Path $Root '.local/db-password'
    if (-not (Test-Path -LiteralPath $password)) { [IO.File]::WriteAllText($password,'synthetic-regression-password') }
    if ($Scenario -like '*partial*') { $global:LASTEXITCODE=23; return }
    $environment=Join-Path $Root '.env'
    if (-not (Test-Path -LiteralPath $environment)) { [IO.File]::WriteAllText($environment,'SYNTHETIC_REGRESSION_ONLY=1') }
    $global:LASTEXITCODE=0
}
function docker {
    $global:LASTEXITCODE=0
    $line=$args -join ' '
    if ($args[0] -eq 'info') { if ($Scenario -notlike 'native-*') { $global:LASTEXITCODE=1 }; return }
    if ($line -eq 'compose up --help') { '--wait-timeout'; return }
    if ($args[0] -eq 'volume' -or $line -match ' reusable ') { $global:LASTEXITCODE=1; return }
    if ($line -match ' prepare ') { Prepare-TestFiles; return }
    if ($args[-1] -eq 'build') { Assert-PrivateFiles; $global:LASTEXITCODE=37; return }
    if ($args[0] -in @('ps','compose')) { return }
    throw 'Unexpected Docker operation in regression adapter.'
}
function wsl.exe {
    $global:LASTEXITCODE=0
    if ($args[1] -eq 'wslpath') { '/checkout'; return }
    if ($args[1] -eq 'docker') { return }
    if ($args[1] -ne 'env') { throw 'Unexpected WSL operation.' }
    if ($args -contains '--prepare-only') { Prepare-TestFiles; return }
    if (-not (Test-Path -LiteralPath (Join-Path $Root '.env'))) { throw 'Preparation was not separated from startup.' }
    Assert-PrivateFiles
    if ($Scenario -eq 'build-failure') { $global:LASTEXITCODE=37 }
}
function Start-Process { [pscustomobject]@{Id=$PID;StartTime=(Get-Process -Id $PID).StartTime} }
function Invoke-WebRequest { [pscustomobject]@{StatusCode=200} }
& (Join-Path $Root 'dev.ps1') up
exit $LASTEXITCODE
