param(
    [string]$Command = 'help',
    [ValidateSet('demo','normal')][string]$Mode = 'demo'
)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
function Usage { 'Usage: .\dev.ps1 {up|stop|doctor|account} [-Mode demo|normal]'; 'up defaults to the seeded offline demo; account needs normal mode and an interactive terminal.' }
if ($Command -in @('help','-h','--help')) { Usage; exit 0 }
if ($Command -notin @('up','stop','doctor','account')) { Usage; exit 2 }
$project = if ($env:COMPOSE_PROJECT_NAME) { $env:COMPOSE_PROJECT_NAME } else { 'fincathon' }
if ($project -notmatch '^[a-z0-9][a-z0-9_-]*$') { Write-Error 'Invalid COMPOSE_PROJECT_NAME.'; exit 2 }
$webPort = if ($env:FINCATHON_WEB_PORT) { $env:FINCATHON_WEB_PORT } else { '3000' }
$apiPort = if ($env:FINCATHON_API_PORT) { $env:FINCATHON_API_PORT } else { '8000' }
foreach ($port in @($webPort,$apiPort)) { if ($port -notmatch '^\d+$' -or [int]$port -lt 1 -or [int]$port -gt 65535) { throw 'Invalid explicit loopback port.' } }
if ($webPort -eq $apiPort) { throw 'Web and API ports must differ.' }
$keeperFile = Join-Path $root ".local\dev\$project\wsl-keeper.json"
function Get-OwnedKeeper {
    if (-not (Test-Path -LiteralPath $keeperFile)) { return $null }
    try {
        $saved = Get-Content -LiteralPath $keeperFile -Raw | ConvertFrom-Json
        $process = Get-Process -Id $saved.pid -ErrorAction SilentlyContinue
        if ($process -and $process.ProcessName -eq 'wsl' -and $process.StartTime.ToUniversalTime().Ticks -eq ([datetime]$saved.started).ToUniversalTime().Ticks -and $saved.checkout -eq $root -and $saved.project -eq $project) { return $process }
    } catch { }
    return $null
}
function Protect-NewFile([string]$Path) {
    $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    & icacls.exe $Path /inheritance:r /grant:r "*${sid}:(F)" /q *> $null
    if ($LASTEXITCODE) { throw 'Could not restrict the new local file to the current Windows user.' }
}
function Check-WindowsPorts([string]$Published) {
    foreach ($port in @($webPort,$apiPort)) {
        if ($Published.Contains("127.0.0.1:$port->")) { continue }
        $probe=New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback,[int]$port)
        try { $probe.Start() } catch { throw "Loopback port $port is occupied. Stop its owner explicitly or set FINCATHON_WEB_PORT / FINCATHON_API_PORT." } finally { $probe.Stop() }
    }
}
$native = $false
if (Get-Command docker -ErrorAction SilentlyContinue) {
    & docker info --format '{{.ServerVersion}}' *> $null
    $native = $LASTEXITCODE -eq 0
}
if (-not $native) {
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { throw 'Docker is unavailable. Start Docker Desktop with Compose, or configure Docker in your default WSL distribution.' }
    & wsl.exe --exec docker info --format '{{.ServerVersion}}' *> $null
    if ($LASTEXITCODE) { throw 'No usable Docker daemon in Windows or default WSL. Start Docker Desktop or Docker in default WSL, then run .\dev.ps1 doctor.' }
    $linuxRoot = (& wsl.exe --exec wslpath -a -u $root | Out-String).Trim()
    if ($LASTEXITCODE -or -not $linuxRoot.StartsWith('/')) { throw 'Cannot translate checkout path for default WSL.' }
    if ($Command -eq 'up') {
        $published=(& wsl.exe --exec docker ps --filter "label=com.docker.compose.project=$project" --format '{{.Ports}}' | Out-String)
        if ($LASTEXITCODE) { throw 'Cannot inspect published ports; no services were changed.' }
        Check-WindowsPorts $published
    }
    $arguments = @('--exec','env',"COMPOSE_PROJECT_NAME=$project","FINCATHON_WEB_PORT=$webPort","FINCATHON_API_PORT=$apiPort",'bash',"$linuxRoot/dev",$Command,'--mode',$Mode)
    $envExisted = Test-Path -LiteralPath (Join-Path $root '.env')
    $passwordExisted = Test-Path -LiteralPath (Join-Path $root '.local\db-password')
    if ($Command -eq 'up') {
        # Prepare separately so Windows ACLs are applied before builds/services.
        # Finally also covers partial preparation and preserves its exit status.
        try {
            & wsl.exe @arguments --prepare-only
            $result = $LASTEXITCODE
        } finally {
            foreach ($entry in @(@('.env',$envExisted),@('.local\db-password',$passwordExisted))) {
                if (-not $entry[1] -and (Test-Path -LiteralPath (Join-Path $root $entry[0]))) { Protect-NewFile (Join-Path $root $entry[0]) }
            }
        }
        if ($result) { exit $result }
    }
    & wsl.exe @arguments
    $result = $LASTEXITCODE
    if ($result) { exit $result }
    if ($Command -eq 'up') {
        if (-not (Get-OwnedKeeper)) {
            $keeper = Start-Process -FilePath 'wsl.exe' -ArgumentList @('--exec','sleep','infinity') -WindowStyle Hidden -PassThru
            $directory = Split-Path $keeperFile
            New-Item -ItemType Directory -Force -Path $directory | Out-Null
            $metadata = @{ pid=$keeper.Id; started=$keeper.StartTime.ToUniversalTime().ToString('o'); checkout=$root; project=$project } | ConvertTo-Json
            [IO.File]::WriteAllText($keeperFile,$metadata)
            Protect-NewFile $keeperFile
        }
        $reachable = $false
        for ($attempt=0; $attempt -lt 20; $attempt++) {
            try { $response=Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$webPort/" -TimeoutSec 2; if ($response.StatusCode -eq 200) { $reachable=$true; break } } catch { }
            Start-Sleep -Milliseconds 500
        }
        if (-not $reachable) { throw "Services started inside WSL, but Windows cannot reach port $webPort. Run .\dev.ps1 doctor and check WSL localhost forwarding; data is retained." }
        'Windows loopback access verified.'
    } elseif ($Command -eq 'stop') {
        $keeper = Get-OwnedKeeper
        if ($keeper) {
            $allIds = @(& wsl.exe --exec docker ps -q)
            if ($LASTEXITCODE) { throw 'Cannot verify unrelated services; the owned WSL helper was retained.' }
            $selectedIds = @(& wsl.exe --exec docker ps -q --filter "label=com.docker.compose.project=$project")
            if ($LASTEXITCODE) { throw 'Cannot verify project services; the owned WSL helper was retained.' }
            $other = @($allIds | Where-Object { $_ -notin $selectedIds })
            if ($other.Count) { 'WSL helper retained while unrelated containers are running.' } else { Stop-Process -Id $keeper.Id }
        }
    }
    exit 0
}

# Native Windows Docker CLI adapter. Shared checks/bootstrap run in containers.
Push-Location $root
try {
    function D {
        # BuildKit writes normal progress to stderr.  With the script-wide Stop
        # preference, PowerShell otherwise turns that progress into a terminating
        # NativeCommandError before Docker's exit code can be checked.
        $previousErrorActionPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            & docker @args
            $dockerExitCode = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }
        if ($dockerExitCode) { throw 'Docker command failed. Run .\dev.ps1 doctor; existing data is retained.' }
    }
    $pythonImage = ((Get-Content docker/api.Dockerfile -TotalCount 1) -split '\s+')[1]
    function Helper { D run --rm --mount "type=bind,src=$root,dst=/checkout" $pythonImage python /checkout/scripts/dev_bootstrap.py @args }
    D compose version | Out-Null
    $composeHelp = D compose up --help | Out-String
    if (-not $composeHelp.Contains('--wait-timeout')) { throw 'Docker Compose lacks --wait-timeout. Update the Compose plugin, then run .\dev.ps1 doctor.' }
    $ids = @(D ps -aq --filter "label=com.docker.compose.project=$project")
    $inventory = 'unknown 0 0'
    if ($ids.Count) {
        $raw = D inspect @ids | Out-String
        $options = @('inventory','--root-label',$root)
        if ($Command -eq 'up') { $options += @('--mode',$Mode) }
        $inventory = ($raw | & docker run --rm -i --mount "type=bind,src=$root,dst=/checkout,readonly" $pythonImage python /checkout/scripts/dev_bootstrap.py @options | Out-String).Trim()
        if ($LASTEXITCODE) { throw 'Project ownership or runtime mode conflict; no services were changed.' }
    }
    $current,$running,$total = $inventory -split ' '
    if ($Command -ne 'up' -and $current -ne 'unknown') { $Mode=$current }
    $compose = @('compose','-p',$project,'-f',"$root/compose.yaml")
    if ($Mode -eq 'demo') { $compose += @('-f',"$root/compose.demo.yaml") }
    D @compose config --quiet | Out-Null
    function Ready([int]$Timeout=90) { D run --rm --network "${project}_default" --mount "type=bind,src=$root,dst=/checkout,readonly" $pythonImage python /checkout/scripts/dev_bootstrap.py ready --mode $Mode --timeout $Timeout }
    if ($Command -eq 'doctor') {
        "Docker/Compose: available; checkout ownership: valid; mode: $current; running containers: $running."
        if ([int]$running) { Ready 5 } else { 'Project stopped. Run .\dev.ps1 up.' }
    } elseif ($Command -eq 'stop') {
        if ([int]$total) { D @compose stop }
        if (Test-Path -LiteralPath ".local/dev/$project/state.json") { Helper state --project $project --mode $Mode --ready no }
        'Project stopped; volumes, credentials and unrelated services retained.'
    } elseif ($Command -eq 'account') {
        if ($Mode -ne 'normal' -or -not [int]$running) { throw 'Start normal mode: .\dev.ps1 up -Mode normal' }
        if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected) { throw 'Account setup requires an interactive terminal; no password argument is supported.' }
        $email=Read-Host 'Email'; $display=Read-Host 'Display name'; $organization=Read-Host 'Organization'
        D @compose exec api python scripts/bootstrap_account.py --email $email --name $display --organization $organization
    } else {
        '[preflight] Docker, Compose and project ownership checked.'
        $published=D ps --filter "label=com.docker.compose.project=$project" --format '{{.Ports}}' | Out-String
        Check-WindowsPorts $published
        & docker run --rm --mount "type=bind,src=$root,dst=/checkout" $pythonImage python /checkout/scripts/dev_bootstrap.py reusable --project $project --mode $Mode
        $reuse=$LASTEXITCODE -eq 0
        if ([int]$running -and $reuse -and $published.Contains("127.0.0.1:$webPort->") -and $published.Contains("127.0.0.1:$apiPort->")) { Ready 5; "Ready: http://127.0.0.1:$webPort | mode=$Mode | existing healthy instance reused."; exit 0 }
        & docker volume inspect "${project}_postgres" *> $null; $existingDb=[int]($LASTEXITCODE -eq 0)
        & docker volume inspect "${project}_runtime" *> $null; $existingRuntime=[int]($LASTEXITCODE -eq 0)
        $envExisted=Test-Path -LiteralPath .env; $passwordExisted=Test-Path -LiteralPath .local/db-password
        '[prepare] Creating only missing local configuration.'
        try {
            Helper prepare --project $project --existing-db $existingDb --existing-runtime $existingRuntime
        } finally {
            if (-not $envExisted -and (Test-Path -LiteralPath .env)) { Protect-NewFile (Join-Path $root '.env') }
            if (-not $passwordExisted -and (Test-Path -LiteralPath .local/db-password)) { Protect-NewFile (Join-Path $root '.local/db-password') }
        }
        $logdir=Join-Path $root ".local/dev/$project"
        function Stage([string]$Label,[scriptblock]$Action) {
            "[$Label]"
            try { & $Action *> (Join-Path $logdir "$Label.log") } catch { throw "Stage $Label failed. Inspect $logdir/$Label.log and run .\dev.ps1 doctor. Existing data retained." }
        }
        Stage build { D @compose build }
        Stage database { D @compose up -d --force-recreate --wait --wait-timeout 90 postgres }
        Stage key-check { D @compose run --rm --no-deps -T api python scripts/dev_bootstrap.py key }
        Stage services { D @compose up -d --force-recreate }
        if ($Mode -eq 'demo') { Stage seed { D @compose run --rm -T seed } }
        Stage readiness { Ready 90 }
        Helper state --project $project --mode $Mode --ready yes
        "Ready: http://127.0.0.1:$webPort | mode=$Mode"
        if ($Mode -eq 'demo') { 'SYNTHETIC OFFLINE DEMO: use Enter demo; no provider keys or personal login required.' } else { 'Run .\dev.ps1 account to provision a normal local owner.' }
        'Stop: .\dev.ps1 stop | Diagnose: .\dev.ps1 doctor | Live acceptance is separate.'
    }
} catch { Write-Error $_.Exception.Message; exit 1 } finally { Pop-Location }
