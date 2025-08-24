# Codessa Platform - Modular Architecture Setup Script
# This script prepares each project for independent GitHub repository management

param(
    [string]$Action = "analyze",
    [string]$ProjectName = "",
    [switch]$DryRun = $false
)

# Define project configurations
$projects = @{
    'codessa-core' = @{
        'type' = 'library'
        'language' = 'mixed'
        'priority' = 'high'
        'description' = 'Core platform libraries and utilities'
    }
    'codessa' = @{
        'type' = 'application'
        'language' = 'typescript'
        'priority' = 'critical'
        'description' = 'Distributed Multi-Agent Reasoning System'
    }
    'echoforge' = @{
        'type' = 'platform'
        'language' = 'hybrid'
        'priority' = 'critical'
        'description' = 'Digital Consciousness Platform'
    }
    'multi-agent-factory' = @{
        'type' = 'service'
        'language' = 'python'
        'priority' = 'high'
        'description' = 'Multi-Agent Factory and Orchestration'
    }
    'codessa-llm-router' = @{
        'type' = 'service'
        'language' = 'python'
        'priority' = 'medium'
        'description' = 'LLM routing and load balancing service'
    }
    'codessa-memory' = @{
        'type' = 'service'
        'language' = 'python'
        'priority' = 'high'
        'description' = 'Memory management and persistence layer'
    }
    'codessa-metamind' = @{
        'type' = 'service'
        'language' = 'typescript'
        'priority' = 'medium'
        'description' = 'Meta-cognitive reasoning system'
    }
    'gitguard' = @{
        'type' = 'tool'
        'language' = 'python'
        'priority' = 'medium'
        'description' = 'Git security and policy enforcement'
    }
    'echopilot' = @{
        'type' = 'extension'
        'language' = 'typescript'
        'priority' = 'low'
        'description' = 'AI-Powered VS Code Extension'
    }
    'devgenie' = @{
        'type' = 'tool'
        'language' = 'mixed'
        'priority' = 'low'
        'description' = 'Development utilities and tools'
    }
    'docfoundry' = @{
        'type' = 'tool'
        'language' = 'python'
        'priority' = 'low'
        'description' = 'Documentation scaffold and generation system'
    }
    'skyforge' = @{
        'type' = 'infrastructure'
        'language' = 'yaml'
        'priority' = 'medium'
        'description' = 'Development environment and infrastructure'
    }
    'aetherion-soulforge' = @{
        'type' = 'infrastructure'
        'language' = 'mixed'
        'priority' = 'low'
        'description' = 'Advanced infrastructure components'
    }
    'codessa-oss-starter' = @{
        'type' = 'template'
        'language' = 'mixed'
        'priority' = 'low'
        'description' = 'OSS project starter templates'
    }
    'pondskipperhq' = @{
        'type' = 'unknown'
        'language' = 'unknown'
        'priority' = 'low'
        'description' = 'Component requiring investigation'
    }
}

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Analyze-Projects {
    Write-ColorOutput "=== CODESSA PLATFORM PROJECT ANALYSIS ===" "Cyan"
    Write-ColorOutput "Total projects: $($projects.Count)" "Green"
    Write-Host ""
    
    foreach ($projectName in $projects.Keys | Sort-Object) {
        $config = $projects[$projectName]
        $projectPath = "C:\Users\Ava\codessa-platform\$projectName"
        
        Write-ColorOutput "📁 $projectName" "Yellow"
        Write-Host "   Type: $($config.type)"
        Write-Host "   Language: $($config.language)"
        Write-Host "   Priority: $($config.priority)"
        Write-Host "   Description: $($config.description)"
        
        if (Test-Path $projectPath) {
            Write-ColorOutput "   Status: ✅ Exists" "Green"
            
            # Check for key files
            $keyFiles = @()
            if (Test-Path "$projectPath\README.md") { $keyFiles += "README.md" }
            if (Test-Path "$projectPath\package.json") { $keyFiles += "package.json" }
            if (Test-Path "$projectPath\pyproject.toml") { $keyFiles += "pyproject.toml" }
            if (Test-Path "$projectPath\setup.py") { $keyFiles += "setup.py" }
            if (Test-Path "$projectPath\Dockerfile") { $keyFiles += "Dockerfile" }
            if (Test-Path "$projectPath\.github") { $keyFiles += ".github/" }
            
            if ($keyFiles.Count -gt 0) {
                Write-Host "   Key files: $($keyFiles -join ', ')"
            }
        } else {
            Write-ColorOutput "   Status: ❌ Missing" "Red"
        }
        Write-Host ""
    }
}

function Prepare-Project {
    param(
        [string]$ProjectName,
        [hashtable]$Config
    )
    
    $projectPath = "C:\Users\Ava\codessa-platform\$ProjectName"
    
    if (-not (Test-Path $projectPath)) {
        Write-ColorOutput "❌ Project $ProjectName does not exist at $projectPath" "Red"
        return
    }
    
    Write-ColorOutput "🔧 Preparing $ProjectName for modular architecture..." "Cyan"
    
    # Create .gitignore if it doesn't exist
    $gitignorePath = "$projectPath\.gitignore"
    if (-not (Test-Path $gitignorePath)) {
        Write-ColorOutput "   Creating .gitignore" "Green"
        if (-not $DryRun) {
            $gitignoreContent = Get-GitignoreTemplate -Language $Config.language
            Set-Content -Path $gitignorePath -Value $gitignoreContent
        }
    }
    
    # Ensure README.md exists
    $readmePath = "$projectPath\README.md"
    if (-not (Test-Path $readmePath)) {
        Write-ColorOutput "   Creating README.md" "Green"
        if (-not $DryRun) {
            $readmeContent = Get-ReadmeTemplate -ProjectName $ProjectName -Config $Config
            Set-Content -Path $readmePath -Value $readmeContent
        }
    }
    
    # Create GitHub workflows directory
    $workflowsPath = "$projectPath\.github\workflows"
    if (-not (Test-Path $workflowsPath)) {
        Write-ColorOutput "   Creating GitHub workflows directory" "Green"
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $workflowsPath -Force | Out-Null
        }
    }
    
    Write-ColorOutput "   ✅ $ProjectName prepared successfully" "Green"
}

function Get-GitignoreTemplate {
    param([string]$Language)
    
    $template = @(
        "# Dependencies",
        "node_modules/",
        "__pycache__/",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".Python",
        "build/",
        "develop-eggs/",
        "dist/",
        "downloads/",
        "eggs/",
        ".eggs/",
        "lib/",
        "lib64/",
        "parts/",
        "sdist/",
        "var/",
        "wheels/",
        "*.egg-info/",
        ".installed.cfg",
        "*.egg",
        "",
        "# IDEs",
        ".vscode/",
        ".idea/",
        "*.swp",
        "*.swo",
        "*~",
        "",
        "# OS",
        ".DS_Store",
        ".DS_Store?",
        "._*",
        ".Spotlight-V100",
        ".Trashes",
        "ehthumbs.db",
        "Thumbs.db",
        "",
        "# Logs",
        "logs",
        "*.log",
        "npm-debug.log*",
        "yarn-debug.log*",
        "yarn-error.log*",
        "",
        "# Environment",
        ".env",
        ".env.local",
        ".env.development.local",
        ".env.test.local",
        ".env.production.local",
        "",
        "# Cache",
        ".cache/",
        ".parcel-cache/",
        ".next/",
        "out/",
        "",
        "# Coverage",
        "coverage/",
        ".nyc_output/",
        "",
        "# Temporary",
        "*.tmp",
        "*.temp"
    )
    
    return $template -join "`n"
}

function Get-ReadmeTemplate {
    param(
        [string]$ProjectName,
        [hashtable]$Config
    )
    
    $template = @(
        "# $ProjectName",
        "",
        "$($Config.description)",
        "",
        "## Overview",
        "",
        "This is part of the Codessa Platform modular architecture. Each component is designed to be independently deployable and maintainable.",
        "",
        "## Type",
        "- **Component Type**: $($Config.type)",
        "- **Primary Language**: $($Config.language)",
        "- **Priority**: $($Config.priority)",
        "",
        "## Getting Started",
        "",
        "### Prerequisites",
        "",
        "[Add prerequisites here]",
        "",
        "### Installation",
        "",
        "[Add installation instructions here]",
        "",
        "### Usage",
        "",
        "[Add usage examples here]",
        "",
        "## Development",
        "",
        "### Setup",
        "",
        "[Add development setup instructions here]",
        "",
        "### Testing",
        "",
        "[Add testing instructions here]",
        "",
        "## Contributing",
        "",
        "Please read our [Contributing Guidelines](../CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.",
        "",
        "## License",
        "",
        "[Add license information here]",
        "",
        "## Related Projects",
        "",
        "This project is part of the Codessa Platform ecosystem:",
        "",
        "- [codessa-core](../codessa-core) - Core platform libraries",
        "- [echoforge](../echoforge) - Digital Consciousness Platform",
        "- [multi-agent-factory](../multi-agent-factory) - Multi-Agent Factory",
        "",
        "[Add other relevant project links here]"
    )
    
    return $template -join "`n"
}

# Main execution logic
switch ($Action.ToLower()) {
    "analyze" {
        Analyze-Projects
    }
    "prepare" {
        if ($ProjectName) {
            if ($projects.ContainsKey($ProjectName)) {
                Prepare-Project -ProjectName $ProjectName -Config $projects[$ProjectName]
            } else {
                Write-ColorOutput "❌ Unknown project: $ProjectName" "Red"
                Write-ColorOutput "Available projects: $($projects.Keys -join ', ')" "Yellow"
            }
        } else {
            Write-ColorOutput "🔧 Preparing all projects for modular architecture..." "Cyan"
            foreach ($projectName in $projects.Keys | Sort-Object) {
                Prepare-Project -ProjectName $projectName -Config $projects[$projectName]
            }
        }
    }
    "execute" {
        Write-ColorOutput "🚀 Executing modular architecture setup..." "Cyan"
        Write-ColorOutput "This would create GitHub repositories and set up CI/CD pipelines." "Yellow"
        Write-ColorOutput "Implementation pending GitHub API integration." "Yellow"
    }
    default {
        Write-ColorOutput "Usage: .\setup-modular-architecture.ps1 -Action [analyze|prepare|execute] [-ProjectName projectname] [-DryRun]" "Yellow"
        Write-ColorOutput "" ""
        Write-ColorOutput "Actions:" "Cyan"
        Write-ColorOutput "  analyze  - Analyze current project structure" "White"
        Write-ColorOutput "  prepare  - Prepare projects for modular architecture" "White"
        Write-ColorOutput "  execute  - Execute the modular architecture setup" "White"
        Write-ColorOutput "" ""
        Write-ColorOutput "Examples:" "Cyan"
        Write-ColorOutput "  .\setup-modular-architecture.ps1 -Action analyze" "White"
        Write-ColorOutput "  .\setup-modular-architecture.ps1 -Action prepare -ProjectName echoforge" "White"
        Write-ColorOutput "  .\setup-modular-architecture.ps1 -Action prepare -DryRun" "White"
    }
}