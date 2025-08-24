# File: make.ps1
# Purpose: Windows-friendly task runner mirroring Makefile targets with uv-based dependency management.

param(
  [Parameter(Position=0)] [string] $Task = "help",
  [string] $S,
  [string] $N,
  [string] $SUBJECT,
  [string] $DATA
)

# -------- Config --------
$Env:COMPOSE_FILE = $Env:COMPOSE_FILE ? $Env:COMPOSE_FILE : "infra/docker/docker-compose.yml"
$Env:ENV_FILE     = $Env:ENV_FILE     ? $Env:ENV_FILE     : ".env"
$API_PORT         = $Env:API_PORT     ? $Env:API_PORT     : "8000"
$API_HEALTH       = $Env:API_HEALTH   ? $Env:API_HEALTH   : "/"
$NATS_MONITOR     = $Env:NATS_MONITOR ? $Env:NATS_MONITOR : "8222"

$DC = "docker compose -f `"$Env:COMPOSE_FILE`" --env-file `"$Env:ENV_FILE`""

function Step($msg) { Write-Host "==> $msg" -ForegroundColor Yellow }
function Ok($msg)   { Write-Host "✓ $msg" -ForegroundColor Green }
function Die($msg)  { Write-Error $msg; exit 1 }

function Test-Cmd($name) {
  $null = Get-Command $name -ErrorAction SilentlyContinue
  if (-not $?) { Die "Missing required command: $name" }
}

function Help {
  @"
Multi-Agent Factory — make.ps1 tasks

  help                Show this help
  verify              Verify tools (python, uv, docker, compose, curl, nats) and lint compose
  venv                Create .venv with uv
  install             Install runtime deps (uv pip install -e .)
  install-dev         Install dev deps (uv pip install -e .[dev])
  install-test        Install test deps (uv pip install -e .[test])
  install-all         Install dev+test deps (uv pip install -e .[dev,test])
  lock                Compile requirements*.txt from pyproject via uv
  up                  docker compose up --build -d
  up-dev              docker compose --profile dev up --build -d db redis nats api-dev
  down                docker compose down
  down-v              docker compose down -v --remove-orphans
  restart             docker compose restart
  ps                  docker compose ps
  logs                docker compose logs --since=10m (requires -S <service>)
  tail                docker compose logs -f        (requires -S <service>)
  stats               docker stats
  top                 docker compose top            (requires -S <service>)
  curl                Probe API: GET http://127.0.0.1:$API_PORT$API_HEALTH
  nats-health         Check NATS /healthz
  nats-pub            Publish via nats CLI (requires -SUBJECT and -DATA)
  scale               Scale a service (requires -S <service> and -N <count>)
  db-shell            psql shell in db container
  redis-cli           redis-cli in redis container
  smoke               Basic end-to-end smoke test (API + NATS)
  clean               Remove pyc/__pycache__ and prune Docker junk
"@ | Write-Host
}

switch ($Task.ToLower()) {

  "help" { Help; break }

  "verify" {
    Step "Verifying local toolchain..."
    Test-Cmd python
    Test-Cmd uv
    Test-Cmd docker
    Test-Cmd curl
    $natsCmd = Get-Command nats -ErrorAction SilentlyContinue
    if (-not $natsCmd) { Write-Host "Note: 'nats' CLI not found; messaging tests may be limited." -ForegroundColor Yellow }
    docker version    | Out-Null
    docker compose version | Out-Null
    Step "Linting compose file..."
    cmd /c "$DC config -q" | Out-Null
    Ok "Verified tools and compose config"
    break
  }

  # === DEPENDENCY MANAGEMENT ===
  "venv" {
    Step "Creating virtual environment (.venv) with uv"
    uv venv
    Ok "Created .venv. Activate with: .\.venv\Scripts\Activate.ps1"
    break
  }

  "install" {
    Step "Installing production dependencies (uv)"
    uv pip install -e .
    Ok "Installed runtime deps"
    break
  }

  "install-dev" {
    Step "Installing development dependencies (uv)"
    uv pip install -e ".[dev]"
    Ok "Installed dev deps"
    break
  }

  "install-test" {
    Step "Installing test dependencies (uv)"
    uv pip install -e ".[test]"
    Ok "Installed test deps"
    break
  }

  "install-all" {
    Step "Installing all dependencies (dev + test) (uv)"
    uv pip install -e ".[dev,test]"
    Ok "Installed dev+test deps"
    break
  }

  "lock" {
    Step "Compiling lockfiles via uv"
    uv pip compile pyproject.toml -o requirements.txt
    uv pip compile --extra dev  pyproject.toml -o requirements-dev.txt
    uv pip compile --extra test pyproject.toml -o requirements-test.txt
    Ok "Generated requirements*.txt"
    break
  }

  # ======== Infra Controls ========
  "up"      { Step "Starting services";        cmd /c "$DC up --build -d"; Ok "Up"; break }
  "up-dev"  { Step "Starting dev services";    cmd /c "$DC --profile dev up --build -d db redis nats api-dev"; Ok "Up (dev)"; break }
  "down"    { Step "Stopping services";        cmd /c "$DC down"; Ok "Down"; break }
  "down-v"  { Step "Stopping & pruning vols";  cmd /c "$DC down -v --remove-orphans"; Ok "Down -v"; break }
  "restart" { Step "Restarting services";      cmd /c "$DC restart"; Ok "Restarted"; break }
  "ps"      { cmd /c "$DC ps"; break }
  "logs"    {
    if (-not $S) { Die "Usage: .\make.ps1 logs -S <service>" }
    cmd /c "$DC logs --since=10m $S"; break
  }
  "tail"    {
    if (-not $S) { Die "Usage: .\make.ps1 tail -S <service>" }
    cmd /c "$DC logs -f $S"; break
  }
  "stats"   { docker stats; break }
  "top"     {
    if (-not $S) { Die "Usage: .\make.ps1 top -S <service>" }
    cmd /c "$DC top $S"; break
  }

  # ======== Probes & Messaging ========
  "curl" {
    $url = "http://127.0.0.1:$API_PORT$API_HEALTH"
    Step "GET $url"
    try {
      (Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 3) | Out-Null
      Ok "API is healthy"
    } catch {
      Die "API health check FAILED"
    }
    break
  }

  "nats-health" {
    $url = "http://127.0.0.1:$NATS_MONITOR/healthz"
    Step "GET $url"
    try {
      $resp = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 3
      if ($resp.Content -match "ok") { Ok "NATS is healthy" } else { Die "NATS health check FAILED" }
    } catch { Die "NATS health check FAILED" }
    break
  }

  "nats-pub" {
    if (-not $SUBJECT -or -not $DATA) { Die "Usage: .\make.ps1 nats-pub -SUBJECT tasks.doc_writer -DATA '{\"x\":1}'" }
    nats pub $SUBJECT $DATA
    break
  }

  "scale" {
    if (-not $S -or -not $N) { Die "Usage: .\make.ps1 scale -S <service> -N <count>" }
    cmd /c "$DC up -d --scale $S=$N"
    break
  }

  # ======== Shells ========
  "db-shell"   { cmd /c "$DC exec db psql -U ${Env:POSTGRES_USER}-${null} -d ${Env:POSTGRES_DB}-${null}"; break }
  "redis-cli"  { cmd /c "$DC exec redis redis-cli"; break }

  # ======== Smoke & Clean ========
  "smoke" {
    Step "Ensuring stack is up"
    & $PSCommandPath up | Out-Null
    Step "Waiting for API"
    $url = "http://127.0.0.1:$API_PORT$API_HEALTH"
    $ok = $false
    for ($i=0; $i -lt 60; $i++) {
      try { (Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2) | Out-Null; $ok = $true; break } catch { Start-Sleep -Seconds 2 }
    }
    if (-not $ok) { Die "API not ready" } else { Ok "API ready" }
    Step "Checking NATS"
    $natsUrl = "http://127.0.0.1:$NATS_MONITOR/healthz"
    try {
      $resp = Invoke-WebRequest -UseBasicParsing -Uri $natsUrl -TimeoutSec 3
      if ($resp.Content -match "ok") { Ok "NATS ready" } else { Die "NATS not ready" }
    } catch { Die "NATS not ready" }
    Write-Host "Optional: nats pub tasks.doc_writer '{\"task_id\":\"smoke\",\"text\":\"hello\"}'"
    break
  }

  "clean" {
    Step "Cleaning Python artifacts"
    Get-ChildItem -Recurse -Include __pycache__ | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Include *.pyc     | Remove-Item -Force -ErrorAction SilentlyContinue
    Step "Pruning Docker junk"
    docker system prune -f
    docker volume prune -f
    docker network prune -f
    docker image prune -f
    docker container prune -f
    docker builder prune -f
    Ok "Clean complete"
    break
  }

  default { Help }
}
