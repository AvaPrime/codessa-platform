# Simple Project Analysis Script for Codessa Platform

$projects = @(
    'codessa-core',
    'codessa',
    'echoforge',
    'multi-agent-factory',
    'codessa-llm-router',
    'codessa-memory',
    'codessa-metamind',
    'gitguard',
    'echopilot',
    'devgenie',
    'docfoundry',
    'skyforge',
    'aetherion-soulforge',
    'codessa-oss-starter',
    'pondskipperhq'
)

Write-Host "=== CODESSA PLATFORM PROJECT ANALYSIS ===" -ForegroundColor Cyan
Write-Host "Total projects to analyze: $($projects.Count)" -ForegroundColor Green
Write-Host ""

foreach ($project in $projects) {
    $projectPath = "C:\Users\Ava\codessa-platform\$project"
    
    Write-Host "📁 $project" -ForegroundColor Yellow
    
    if (Test-Path $projectPath) {
        Write-Host "   Status: ✅ Exists" -ForegroundColor Green
        
        # Check for key files
        $keyFiles = @()
        if (Test-Path "$projectPath\README.md") { $keyFiles += "README.md" }
        if (Test-Path "$projectPath\package.json") { $keyFiles += "package.json" }
        if (Test-Path "$projectPath\pyproject.toml") { $keyFiles += "pyproject.toml" }
        if (Test-Path "$projectPath\setup.py") { $keyFiles += "setup.py" }
        if (Test-Path "$projectPath\requirements.txt") { $keyFiles += "requirements.txt" }
        if (Test-Path "$projectPath\Dockerfile") { $keyFiles += "Dockerfile" }
        if (Test-Path "$projectPath\.github") { $keyFiles += ".github/" }
        if (Test-Path "$projectPath\src") { $keyFiles += "src/" }
        if (Test-Path "$projectPath\apps") { $keyFiles += "apps/" }
        if (Test-Path "$projectPath\packages") { $keyFiles += "packages/" }
        
        if ($keyFiles.Count -gt 0) {
            Write-Host "   Key files: $($keyFiles -join ', ')" -ForegroundColor White
        }
        
        # Count subdirectories
        $subdirs = Get-ChildItem -Path $projectPath -Directory -ErrorAction SilentlyContinue
        Write-Host "   Subdirectories: $($subdirs.Count)" -ForegroundColor White
        
    } else {
        Write-Host "   Status: ❌ Missing" -ForegroundColor Red
    }
    Write-Host ""
}

Write-Host "Analysis complete!" -ForegroundColor Green