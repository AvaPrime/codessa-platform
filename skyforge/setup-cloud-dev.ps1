# Cloud Development Environment Setup Script (PowerShell)
# For Windows laptops connecting to cloud VMs
# Author: AI Assistant
# Version: 2.0

param(
    [switch]$InstallTools,
    [switch]$ConfigureSSH,
    [string]$CloudIP = "",
    [string]$Username = "devuser",
    [switch]$SetupPython,
    [switch]$GenerateVMScript,
    [string]$Environment = "powershell",  # Options: powershell, wsl2, remote
    [string]$ProjectRoot = $env:USERPROFILE,
    [string]$RemoteHost = "",
    [string]$RemoteUser = "",
    [switch]$Help
)

# Utility functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Function to check if command exists
function Test-CommandExists {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}
    }
}

# Validate and setup environment
function Initialize-Environment {
    param(
        [string]$Environment,
        [string]$ProjectRoot,
        [string]$RemoteHost,
        [string]$RemoteUser
    )
    
    Write-Host "Initializing environment: $Environment" -ForegroundColor Cyan
    
    switch ($Environment.ToLower()) {
        "powershell" {
            Write-Host "Using native PowerShell environment" -ForegroundColor Green
            if (!(Test-Path $ProjectRoot)) {
                New-Item -ItemType Directory -Path $ProjectRoot -Force | Out-Null
                Write-Host "Created project root: $ProjectRoot" -ForegroundColor Yellow
            }
            return @{
                Type = "powershell"
                ProjectRoot = $ProjectRoot
                VenvPath = Join-Path $ProjectRoot "ai-env"
                ActivateScript = Join-Path $ProjectRoot "activate-ai-env.ps1"
            }
        }
        "wsl2" {
            Write-Host "Checking WSL2 availability..." -ForegroundColor Yellow
            if (!(Test-CommandExists "wsl")) {
                Write-Host "ERROR: WSL is not installed. Please install WSL2 first." -ForegroundColor Red
                Write-Host "Run: wsl --install" -ForegroundColor Yellow
                exit 1
            }
            
            # Convert Windows path to WSL path
            $wslProjectRoot = $ProjectRoot -replace '^([A-Z]):', '/mnt/$1' -replace '\\', '/'
            $wslProjectRoot = $wslProjectRoot.ToLower()
            
            Write-Host "Using WSL2 environment" -ForegroundColor Green
            Write-Host "Windows project root: $ProjectRoot" -ForegroundColor Cyan
            Write-Host "WSL project root: $wslProjectRoot" -ForegroundColor Cyan
            
            return @{
                Type = "wsl2"
                ProjectRoot = $ProjectRoot
                WSLProjectRoot = $wslProjectRoot
                VenvPath = "$wslProjectRoot/ai-env"
                ActivateScript = "$wslProjectRoot/activate-ai-env.sh"
            }
        }
        "remote" {
            if ([string]::IsNullOrEmpty($RemoteHost) -or [string]::IsNullOrEmpty($RemoteUser)) {
                Write-Host "ERROR: RemoteHost and RemoteUser are required for remote environment" -ForegroundColor Red
                Write-Host "Usage: -Environment remote -RemoteHost <hostname> -RemoteUser <username>" -ForegroundColor Yellow
                exit 1
            }
            
            Write-Host "Using remote server environment" -ForegroundColor Green
            Write-Host "Remote host: $RemoteHost" -ForegroundColor Cyan
            Write-Host "Remote user: $RemoteUser" -ForegroundColor Cyan
            
            # Test SSH connection
            Write-Host "Testing SSH connection..." -ForegroundColor Yellow
            $sshTest = ssh -o ConnectTimeout=10 -o BatchMode=yes "$RemoteUser@$RemoteHost" "echo 'SSH connection successful'"
            if ($LASTEXITCODE -ne 0) {
                Write-Host "WARNING: SSH connection test failed. Please ensure SSH keys are configured." -ForegroundColor Yellow
                Write-Host "You may need to run: ssh-copy-id $RemoteUser@$RemoteHost" -ForegroundColor Yellow
            } else {
                Write-Host "SSH connection successful" -ForegroundColor Green
            }
            
            return @{
                Type = "remote"
                RemoteHost = $RemoteHost
                RemoteUser = $RemoteUser
                ProjectRoot = "/home/$RemoteUser/projects"
                VenvPath = "/home/$RemoteUser/ai-env"
                ActivateScript = "/home/$RemoteUser/activate-ai-env.sh"
            }
        }
        default {
            Write-Host "ERROR: Invalid environment '$Environment'. Valid options: powershell, wsl2, remote" -ForegroundColor Red
            exit 1
        }
    }
}

# Install Chocolatey if not present
function Install-Chocolatey {
    if (!(Test-Command "choco")) {
        Write-Info "Installing Chocolatey package manager..."
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        Write-Success "Chocolatey installed successfully"
    } else {
        Write-Info "Chocolatey already installed, skipping..."
    }
}

# Install Scoop if not present
function Install-Scoop {
    if (!(Test-Command "scoop")) {
        Write-Info "Installing Scoop package manager..."
        Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
        Invoke-RestMethod get.scoop.sh | Invoke-Expression
        Write-Success "Scoop installed successfully"
    } else {
        Write-Info "Scoop already installed, skipping..."
    }
}





# Generate VM setup script
function New-VMScript {
    Write-Info "Generating Linux VM setup script..."
    
    $vmScript = @'
#!/bin/bash
# Cloud Development Environment VM Setup Script
# Run this on your Ubuntu/Debian cloud VM

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Update system
log_info "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install system prerequisites
log_info "Installing system prerequisites..."
sudo apt install -y \
    curl wget git vim nano htop tree \
    build-essential software-properties-common \
    apt-transport-https ca-certificates gnupg lsb-release \
    python3 python3-pip python3-venv \
    nodejs npm \
    golang-go \
    rustc cargo \
    postgresql-client redis-tools \
    unzip zip jq yq \
    rsync openssh-server

# Install Docker
log_info "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo usermod -aG docker $USER
    log_success "Docker installed successfully"
else
    log_info "Docker already installed, skipping..."
fi

# Install Docker Compose
log_info "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    log_success "Docker Compose installed successfully"
else
    log_info "Docker Compose already installed, skipping..."
fi

# Install cloud CLI tools
log_info "Installing cloud CLI tools..."

# Terraform
if ! command -v terraform &> /dev/null; then
    wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
    sudo apt update && sudo apt install -y terraform
fi

# Kubectl
if ! command -v kubectl &> /dev/null; then
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
fi

# Helm
if ! command -v helm &> /dev/null; then
    curl https://baltocdn.com/helm/signing.asc | gpg --dearmor | sudo tee /usr/share/keyrings/helm.gpg > /dev/null
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/helm.gpg] https://baltocdn.com/helm/stable/debian/ all main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list
    sudo apt update && sudo apt install -y helm
fi

# Create Python AI/ML environment
echo "Setting up Python AI/ML environment..."

# Check if Python3 is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 is not installed. Please install Python3 first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "~/ai-env" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv ~/ai-env
    
    if [ ! -f "~/ai-env/bin/activate" ]; then
        echo "ERROR: Failed to create virtual environment. Please check Python installation."
        exit 1
    fi
    
    echo "Virtual environment created successfully"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source ~/ai-env/bin/activate

# Upgrade pip first to avoid warnings
echo "Upgrading pip to latest version..."
python -m pip install --upgrade pip

# Verify pip upgrade
echo "Pip upgraded successfully: $(pip --version)"

# Install AI/ML packages with detailed progress
echo "Installing AI/ML packages..."

# Core ML frameworks
echo "Installing PyTorch with CUDA support..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

echo "Installing Transformers and related packages..."
pip install transformers datasets accelerate tokenizers

echo "Installing LangChain ecosystem..."
pip install langchain langchain-community langchain-openai langchain-core

echo "Installing distributed computing frameworks..."
pip install "ray[default,serve,tune,rllib]" "dask[complete]"

echo "Installing Jupyter and notebook tools..."
pip install jupyter jupyterlab ipython ipywidgets

echo "Installing data science libraries..."
pip install pandas numpy scipy scikit-learn matplotlib seaborn plotly

echo "Installing web frameworks..."
pip install fastapi uvicorn gradio streamlit

echo "Installing development tools..."
pip install black isort flake8 mypy pytest

echo "Installing HTTP and utility libraries..."
pip install requests aiohttp httpx python-dotenv pydantic

echo "Installing additional ML tools..."
pip install mlflow wandb tensorboard

# Create activation script for easy access
cat > ~/activate-ai-env.sh << 'EOF'
#!/bin/bash
# Activate AI/ML Python Environment
echo "Activating AI/ML Python Environment..."
source ~/ai-env/bin/activate
echo "Environment activated. Python location: $(which python)"
echo "Pip version: $(pip --version)"
EOF

chmod +x ~/activate-ai-env.sh

echo "Python AI/ML environment setup completed!"
echo "Environment location: ~/ai-env"
echo "To activate manually: source ~/ai-env/bin/activate"
echo "Quick activation script: ~/activate-ai-env.sh"

# Test installation
echo "Testing key package installations..."
echo "Testing PyTorch..."
python -c "import torch; print(f'✓ PyTorch: {torch.__version__}')" || echo "✗ PyTorch (failed)"

echo "Testing Transformers..."
python -c "import transformers; print(f'✓ Transformers: {transformers.__version__}')" || echo "✗ Transformers (failed)"

echo "Testing Ray..."
python -c "import ray; print(f'✓ Ray: {ray.__version__}')" || echo "✗ Ray (failed)"

echo "Installing database and task queue libraries..."
pip install psycopg2-binary redis sqlalchemy celery flower

deactivate

# Create development directories
log_info "Creating development directories..."
mkdir -p ~/projects ~/data ~/models ~/notebooks ~/scripts

# Create Docker Compose configuration
log_info "Creating Docker Compose configuration..."
cat > ~/docker-compose.yml << '\''EOF'\''
version: '\''3.8'\''

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15
    container_name: dev-postgres
    environment:
      POSTGRES_DB: devdb
      POSTGRES_USER: devuser
      POSTGRES_PASSWORD: devpass123
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    restart: unless-stopped

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: dev-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  # MinIO Object Storage
  minio:
    image: minio/minio:latest
    container_name: dev-minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin123
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    restart: unless-stopped

  # Jupyter Lab
  jupyter:
    image: jupyter/tensorflow-notebook:latest
    container_name: dev-jupyter
    ports:
      - "8888:8888"
    environment:
      JUPYTER_ENABLE_LAB: "yes"
      JUPYTER_TOKEN: "devtoken123"
    volumes:
      - ./notebooks:/home/jovyan/work
      - ./data:/home/jovyan/data
    restart: unless-stopped

  # MLflow Tracking Server
  mlflow:
    image: python:3.9-slim
    container_name: dev-mlflow
    command: >
      bash -c "pip install mlflow psycopg2-binary &&
               mlflow server --host 0.0.0.0 --port 5000
               --backend-store-uri postgresql://devuser:devpass123@postgres:5432/devdb
               --default-artifact-root s3://mlflow-artifacts/
               --serve-artifacts"
    ports:
      - "5000:5000"
    depends_on:
      - postgres
      - minio
    environment:
      MLFLOW_S3_ENDPOINT_URL: http://minio:9000
      AWS_ACCESS_KEY_ID: minioadmin
      AWS_SECRET_ACCESS_KEY: minioadmin123
    restart: unless-stopped

  # Ray Head Node
  ray-head:
    image: rayproject/ray:latest
    container_name: dev-ray-head
    command: ray start --head --dashboard-host=0.0.0.0 --dashboard-port=8265 --block
    ports:
      - "8265:8265"
      - "10001:10001"
    volumes:
      - ./projects:/workspace
    restart: unless-stopped

  # Portainer (Container Management)
  portainer:
    image: portainer/portainer-ce:latest
    container_name: dev-portainer
    ports:
      - "9443:9443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer_data:/data
    restart: unless-stopped

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: dev-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - jupyter
      - mlflow
      - ray-head
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  minio_data:
  portainer_data:
EOF

# Create Nginx configuration
log_info "Creating Nginx configuration..."
cat > ~/nginx.conf << '\''EOF'\''
events {
    worker_connections 1024;
}

http {
    upstream jupyter {
        server jupyter:8888;
    }
    
    upstream mlflow {
        server mlflow:5000;
    }
    
    upstream ray {
        server ray-head:8265;
    }
    
    server {
        listen 80;
        server_name _;
        
        location /jupyter/ {
            proxy_pass http://jupyter/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        location /mlflow/ {
            proxy_pass http://mlflow/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        location /ray/ {
            proxy_pass http://ray/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

# Create management scripts
log_info "Creating management scripts..."

# Start development environment
cat > ~/start-dev-env.sh << '\''EOF'\''
#!/bin/bash
echo "Starting development environment..."
docker-compose up -d
echo "Development environment started!"
echo "Services available at:"
echo "  - Jupyter Lab: http://localhost:8888 (token: devtoken123)"
echo "  - MLflow: http://localhost:5000"
echo "  - Ray Dashboard: http://localhost:8265"
echo "  - MinIO Console: http://localhost:9001 (admin/minioadmin123)"
echo "  - Portainer: https://localhost:9443"
echo "  - PostgreSQL: localhost:5432 (devuser/devpass123)"
echo "  - Redis: localhost:6379"
EOF

# Stop development environment
cat > ~/stop-dev-env.sh << '\''EOF'\''
#!/bin/bash
echo "Stopping development environment..."
docker-compose down
echo "Development environment stopped!"
EOF

# Status check
cat > ~/status-dev-env.sh << '\''EOF'\''
#!/bin/bash
echo "Development Environment Status"
echo "============================="
echo ""
echo "Docker containers:"
docker-compose ps
echo ""
echo "System resources:"
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '\''{print $2}'\'' | awk -F'\''%'\'' '\''{print $1}'\'')"
echo "Memory Usage: $(free -m | awk '\''NR==2{printf "%.1f%%", $3*100/$2}'\'')"
echo "Disk Usage: $(df -h / | awk '\''NR==2{print $5}'\'')"
echo ""
echo "AI Environment:"
source ~/ai-env/bin/activate
echo "Python: $(python --version)"
echo "PyTorch: $(python -c "import torch; print(torch.__version__)" 2>/dev/null || echo "Not installed")"
echo "CUDA Available: $(python -c "import torch; print(torch.cuda.is_available())" 2>/dev/null || echo "N/A")"
deactivate
EOF

# Make scripts executable
chmod +x ~/start-dev-env.sh ~/stop-dev-env.sh ~/status-dev-env.sh

# Create sample project structure
log_info "Creating sample project structure..."
mkdir -p ~/projects/sample-ai-project/{src,tests,data,models,notebooks,configs}

cat > ~/projects/sample-ai-project/README.md << '\''EOF'\''
# Sample AI Project

This is a template for AI/ML projects in the cloud development environment.

## Structure
- `src/`: Source code
- `tests/`: Unit tests
- `data/`: Data files
- `models/`: Trained models
- `notebooks/`: Jupyter notebooks
- `configs/`: Configuration files

## Getting Started
1. Activate the AI environment: `source ~/ai-env/bin/activate`
2. Start development services: `~/start-dev-env.sh`
3. Open Jupyter Lab: http://localhost:8888
4. Start coding!
EOF

# Setup SSH for remote access
log_info "Configuring SSH..."
sudo systemctl enable ssh
sudo systemctl start ssh

# Create devuser if it doesn'\''t exist
if ! id "devuser" &>/dev/null; then
    sudo useradd -m -s /bin/bash devuser
    sudo usermod -aG sudo,docker devuser
    sudo mkdir -p /home/devuser/.ssh
    sudo chown devuser:devuser /home/devuser/.ssh
    sudo chmod 700 /home/devuser/.ssh
    log_info "Created devuser account. Please set up SSH keys."
fi

log_success "Cloud development environment setup completed!"
log_info "Next steps:"
log_info "1. Copy your SSH public key to ~/.ssh/authorized_keys"
log_info "2. Start the development environment: ./start-dev-env.sh"
log_info "3. Check status: ./status-dev-env.sh"
log_info "4. Connect from your laptop using the Windows PowerShell script"

echo ""
log_info "Rebooting in 10 seconds to ensure all changes take effect..."
sleep 10
sudo reboot
'@
    
    $scriptPath = "$env:USERPROFILE\setup-cloud-vm.sh"
    Set-Content -Path $scriptPath -Value $vmScript
    Write-Success "VM setup script generated at $scriptPath"
    Write-Info "Copy this script to your cloud VM and run: chmod +x setup-cloud-vm.sh && ./setup-cloud-vm.sh"
}

# Install development tools
function Install-DevelopmentTools {
    Write-Info "Installing development tools..."
    
    if (!(Test-Administrator)) {
        Write-Error-Custom "This function requires administrator privileges. Please run as administrator."
        exit 1
    }
    
    # Install package managers
    Install-Chocolatey
    Install-Scoop
    
    # Install essential tools via Chocolatey
    Write-Info "Installing essential development tools..."
    $chocoPackages = @(
        "git",
        "vscode",
        "docker-desktop",
        "nodejs",
        "python",
        "golang",
        "rust",
        "openssh",
        "putty",
        "winscp",
        "postman",
        "dbeaver",
        "redis-desktop-manager"
    )
    
    foreach ($package in $chocoPackages) {
        if (choco list --local-only $package | Select-String $package) {
            Write-Info "$package already installed, skipping..."
        } else {
            Write-Info "Installing $package..."
            choco install $package -y
        }
    }
    
    # Install additional tools via Scoop
    Write-Info "Installing additional tools via Scoop..."
    scoop bucket add extras
    scoop bucket add versions
    
    $scoopPackages = @(
        "curl",
        "wget",
        "jq",
        "yq",
        "terraform",
        "kubectl",
        "helm",
        "azure-cli",
        "aws",
        "gcloud"
    )
    
    foreach ($package in $scoopPackages) {
        if (scoop list $package -eq $null) {
            Write-Info "$package already installed, skipping..."
        } else {
            Write-Info "Installing $package..."
            scoop install $package
        }
    }
    
    # Install VS Code extensions
    Write-Info "Installing VS Code extensions..."
    $vscodeExtensions = @(
        "ms-vscode-remote.remote-ssh",
        "ms-vscode-remote.remote-ssh-edit",
        "ms-azuretools.vscode-docker",
        "ms-python.python",
        "ms-python.black-formatter",
        "ms-toolsai.jupyter",
        "golang.go",
        "rust-lang.rust-analyzer",
        "bradlc.vscode-tailwindcss",
        "esbenp.prettier-vscode",
        "ms-vscode.powershell"
    )
    
    foreach ($extension in $vscodeExtensions) {
        Write-Info "Installing VS Code extension: $extension"
        code --install-extension $extension
    }
    
    Write-Success "Development tools installation completed!"
}

# Configure SSH connection
function Set-SSHConnection {
    param(
        [string]$CloudIP,
        [string]$Username = "devuser"
    )
    
    Write-Info "Configuring SSH connection to $CloudIP..."
    
    # Create SSH config directory if it doesn't exist
    $sshConfigDir = "$env:USERPROFILE\.ssh"
    if (!(Test-Path $sshConfigDir)) {
        New-Item -ItemType Directory -Path $sshConfigDir -Force
    }
    
    # Generate SSH key if it doesn't exist
    $keyPath = "$sshConfigDir\cloud-dev-key"
    if (!(Test-Path $keyPath)) {
        Write-Info "Generating SSH key pair..."
        ssh-keygen -t rsa -b 4096 -f $keyPath -N '""' -C "cloud-dev-$(Get-Date -Format 'yyyy-MM-dd')"
        Write-Success "SSH key pair generated at $keyPath"
        Write-Info "Public key content (copy this to your cloud VM):"
        Write-Host (Get-Content "$keyPath.pub") -ForegroundColor Green
    }
    
    # Create SSH config
    $sshConfigPath = "$sshConfigDir\config"
    $sshConfig = @"
# Cloud Development Environment Configuration
Host cloud-dev
    HostName $CloudIP
    User $Username
    Port 22
    IdentityFile ~/.ssh/cloud-dev-key
    ForwardAgent yes
    # Port forwarding for services
    LocalForward 8888 localhost:8888  # Jupyter Lab
    LocalForward 8265 localhost:8265  # Ray Dashboard
    LocalForward 9001 localhost:9001  # MinIO Console
    LocalForward 9443 localhost:9443  # Portainer
    LocalForward 5432 localhost:5432  # PostgreSQL
    LocalForward 6379 localhost:6379  # Redis
    LocalForward 8000 localhost:8000  # Development server
    LocalForward 8080 localhost:8080  # Alternative dev server
"@
    
    if (Test-Path $sshConfigPath) {
        $existingConfig = Get-Content $sshConfigPath -Raw
        if ($existingConfig -notmatch "Host cloud-dev") {
            Add-Content -Path $sshConfigPath -Value "`n$sshConfig"
            Write-Success "SSH configuration added to existing config file"
        } else {
            Write-Info "SSH configuration already exists, skipping..."
        }
    } else {
        Set-Content -Path $sshConfigPath -Value $sshConfig
        Write-Success "SSH configuration created at $sshConfigPath"
    }
    
    Write-Success "SSH connection configuration completed!"
}

# Setup Python environment
function Setup-PythonEnvironment {
    param(
        [hashtable]$EnvConfig = @{}
    )
    
    if ($EnvConfig.Count -eq 0) {
        # Default to PowerShell environment if no config provided
        $EnvConfig = Initialize-Environment -Environment "powershell" -ProjectRoot $ProjectRoot -RemoteHost $RemoteHost -RemoteUser $RemoteUser
    }
    
    Write-Host "Setting up Python AI/ML environment in $($EnvConfig.Type) environment..." -ForegroundColor Cyan
    
    switch ($EnvConfig.Type) {
        "powershell" {
            Setup-PythonEnvironment-PowerShell -EnvConfig $EnvConfig
        }
        "wsl2" {
            Setup-PythonEnvironment-WSL2 -EnvConfig $EnvConfig
        }
        "remote" {
            Setup-PythonEnvironment-Remote -EnvConfig $EnvConfig
        }
    }
}

# Setup Python environment in PowerShell
function Setup-PythonEnvironment-PowerShell {
    param([hashtable]$EnvConfig)
    
    Write-Host "Setting up Python AI/ML environment in PowerShell..." -ForegroundColor Yellow
    
    # Check if Python is available
    if (!(Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: Python is not installed or not in PATH. Please install Python first." -ForegroundColor Red
        return
    }
    
    $aiEnvPath = $EnvConfig.VenvPath
    
    if (!(Test-Path $aiEnvPath)) {
        Write-Info "Creating Python virtual environment at $aiEnvPath..."
        python -m venv $aiEnvPath
        
        if (!(Test-Path "$aiEnvPath\Scripts\Activate.ps1")) {
            Write-Error-Custom "Failed to create virtual environment. Please check Python installation."
            return
        }
        
        Write-Success "Virtual environment created successfully"
    } else {
        Write-Info "Virtual environment already exists at $aiEnvPath"
    }
    
    # Activate virtual environment
    Write-Info "Activating virtual environment..."
    & "$aiEnvPath\Scripts\Activate.ps1"
    
    # Upgrade pip first to avoid warnings
    Write-Info "Upgrading pip to latest version..."
    & "$aiEnvPath\Scripts\python.exe" -m pip install --upgrade pip
    
    # Verify pip upgrade
    $pipVersion = & "$aiEnvPath\Scripts\pip.exe" --version
    Write-Success "Pip upgraded successfully: $pipVersion"
    
    # Install AI/ML packages
    Write-Info "Installing AI/ML packages..."
    
    # Core ML frameworks
    Write-Info "Installing PyTorch with CUDA support..."
    & "$aiEnvPath\Scripts\pip.exe" install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    
    Write-Info "Installing Transformers and related packages..."
    & "$aiEnvPath\Scripts\pip.exe" install transformers datasets accelerate tokenizers
    
    Write-Info "Installing LangChain ecosystem..."
    & "$aiEnvPath\Scripts\pip.exe" install langchain langchain-community langchain-openai langchain-core
    
    Write-Info "Installing distributed computing frameworks..."
    & "$aiEnvPath\Scripts\pip.exe" install "ray[default,serve,tune,rllib]" "dask[complete]"
    
    Write-Info "Installing Jupyter and notebook tools..."
    & "$aiEnvPath\Scripts\pip.exe" install jupyter jupyterlab ipython ipywidgets
    
    Write-Info "Installing data science libraries..."
    & "$aiEnvPath\Scripts\pip.exe" install pandas numpy scipy scikit-learn matplotlib seaborn plotly
    
    Write-Info "Installing web frameworks..."
    & "$aiEnvPath\Scripts\pip.exe" install fastapi uvicorn gradio streamlit
    
    Write-Info "Installing development tools..."
    & "$aiEnvPath\Scripts\pip.exe" install black isort flake8 mypy pytest
    
    Write-Info "Installing HTTP and utility libraries..."
    & "$aiEnvPath\Scripts\pip.exe" install requests aiohttp httpx python-dotenv pydantic
    
    Write-Info "Installing additional ML tools..."
    & "$aiEnvPath\Scripts\pip.exe" install mlflow wandb tensorboard
    
    # Create activation script for easy access
    $activateScript = @"
# Activate AI/ML Python Environment
Write-Host "Activating AI/ML Python Environment..." -ForegroundColor Green
& "$aiEnvPath\Scripts\Activate.ps1"
Write-Host "Environment activated. Python location: `$(Get-Command python).Source" -ForegroundColor Cyan
Write-Host "Pip version: `$(pip --version)" -ForegroundColor Cyan
"@
    
    Set-Content -Path $EnvConfig.ActivateScript -Value $activateScript
    
    Write-Host "Python AI/ML environment setup completed!" -ForegroundColor Green
    Write-Host "Environment location: $aiEnvPath" -ForegroundColor Cyan
    Write-Host "To activate manually: & '$aiEnvPath\Scripts\Activate.ps1'" -ForegroundColor Cyan
    Write-Host "Quick activation script: & '$($EnvConfig.ActivateScript)'" -ForegroundColor Cyan
    
    # Test installation
    Write-Host "Testing key package installations..." -ForegroundColor Yellow
    $testResults = @()
    
    try {
        & "$aiEnvPath\Scripts\python.exe" -c "import torch; print(f'PyTorch: {torch.__version__}')"
        $testResults += "✓ PyTorch"
    } catch {
        $testResults += "✗ PyTorch (failed)"
    }
    
    try {
        & "$aiEnvPath\Scripts\python.exe" -c "import transformers; print(f'Transformers: {transformers.__version__}')"
        $testResults += "✓ Transformers"
    } catch {
        $testResults += "✗ Transformers (failed)"
    }
    
    try {
        & "$aiEnvPath\Scripts\python.exe" -c "import ray; print(f'Ray: {ray.__version__}')"
        $testResults += "✓ Ray"
    } catch {
        $testResults += "✗ Ray (failed)"
    }
    
    Write-Host "Installation test results:" -ForegroundColor Yellow
    foreach ($result in $testResults) {
        if ($result.StartsWith("✓")) {
            Write-Host "  $result" -ForegroundColor Green
        } else {
            Write-Host "  $result" -ForegroundColor Red
        }
    }
}

# Setup Python environment in WSL2
function Setup-PythonEnvironment-WSL2 {
    param([hashtable]$EnvConfig)
    
    Write-Host "Setting up Python AI/ML environment in WSL2..." -ForegroundColor Yellow
    
    # Ensure WSL project directory exists
    $wslCreateDir = "mkdir -p '$($EnvConfig.WSLProjectRoot)'"
    wsl bash -c $wslCreateDir
    
    # Create the Python setup script for WSL
    $wslSetupScript = @"
#!/bin/bash
set -e

echo "Setting up Python AI/ML environment in WSL2..."

# Check if Python3 is available
if ! command -v python3 &> /dev/null; then
    echo "Installing Python3..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
fi

# Create virtual environment
echo "Creating virtual environment at $($EnvConfig.VenvPath)..."
if [ ! -d "$($EnvConfig.VenvPath)" ]; then
    python3 -m venv $($EnvConfig.VenvPath)
    echo "Virtual environment created successfully"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source $($EnvConfig.VenvPath)/bin/activate

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install AI/ML packages
echo "Installing PyTorch with CUDA support..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

echo "Installing Transformers and related packages..."
pip install transformers datasets accelerate tokenizers

echo "Installing LangChain ecosystem..."
pip install langchain langchain-community langchain-openai langchain-core

echo "Installing distributed computing frameworks..."
pip install "ray[default,serve,tune,rllib]" "dask[complete]"

echo "Installing Jupyter and notebook tools..."
pip install jupyter jupyterlab ipython ipywidgets

echo "Installing data science libraries..."
pip install pandas numpy scipy scikit-learn matplotlib seaborn plotly

echo "Installing web frameworks..."
pip install fastapi uvicorn gradio streamlit

echo "Installing development tools..."
pip install black isort flake8 mypy pytest

echo "Installing HTTP and utility libraries..."
pip install requests aiohttp httpx python-dotenv pydantic

echo "Installing additional ML tools..."
pip install mlflow wandb tensorboard

# Create activation script
cat > $($EnvConfig.ActivateScript) << 'EOF'
#!/bin/bash
echo "Activating AI/ML Python Environment..."
source $($EnvConfig.VenvPath)/bin/activate
echo "Environment activated. Python location: `$(which python)`"
echo "Pip version: `$(pip --version)`"
EOF

chmod +x $($EnvConfig.ActivateScript)

echo "Testing installations..."
python -c "import torch; print(f'✓ PyTorch: {torch.__version__}')" || echo "✗ PyTorch (failed)"
python -c "import transformers; print(f'✓ Transformers: {transformers.__version__}')" || echo "✗ Transformers (failed)"
python -c "import ray; print(f'✓ Ray: {ray.__version__}')" || echo "✗ Ray (failed)"

echo "Python AI/ML environment setup completed in WSL2!"
echo "Environment location: $($EnvConfig.VenvPath)"
echo "Activation script: $($EnvConfig.ActivateScript)"
"@
    
    # Write the script to a temporary file and execute it in WSL
    $tempScript = [System.IO.Path]::GetTempFileName() + ".sh"
    Set-Content -Path $tempScript -Value $wslSetupScript -Encoding UTF8
    
    try {
        # Copy script to WSL and execute
        $wslTempScript = "/tmp/wsl-python-setup.sh"
        Get-Content $tempScript | wsl bash -c "cat > $wslTempScript"
        wsl bash -c "chmod +x $wslTempScript && $wslTempScript"
        
        Write-Host "WSL2 Python environment setup completed!" -ForegroundColor Green
        Write-Host "To activate in WSL: source $($EnvConfig.ActivateScript)" -ForegroundColor Cyan
        Write-Host "To access from Windows: wsl bash -c 'source $($EnvConfig.ActivateScript) && python'" -ForegroundColor Cyan
    }
    finally {
        # Clean up temporary files
        Remove-Item $tempScript -ErrorAction SilentlyContinue
        wsl bash -c "rm -f /tmp/wsl-python-setup.sh" -ErrorAction SilentlyContinue
    }
}

# Setup Python environment on remote server
function Setup-PythonEnvironment-Remote {
    param([hashtable]$EnvConfig)
    
    Write-Host "Setting up Python AI/ML environment on remote server..." -ForegroundColor Yellow
    Write-Host "Remote: $($EnvConfig.RemoteUser)@$($EnvConfig.RemoteHost)" -ForegroundColor Cyan
    
    # Create the Python setup script for remote server
    $remoteSetupScript = @"
#!/bin/bash
set -e

echo "Setting up Python AI/ML environment on remote server..."

# Check if Python3 is available
if ! command -v python3 &> /dev/null; then
    echo "Installing Python3..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
fi

# Create project directory
mkdir -p $($EnvConfig.ProjectRoot)

# Create virtual environment
echo "Creating virtual environment at $($EnvConfig.VenvPath)..."
if [ ! -d "$($EnvConfig.VenvPath)" ]; then
    python3 -m venv $($EnvConfig.VenvPath)
    echo "Virtual environment created successfully"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source $($EnvConfig.VenvPath)/bin/activate

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install AI/ML packages
echo "Installing PyTorch with CUDA support..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

echo "Installing Transformers and related packages..."
pip install transformers datasets accelerate tokenizers

echo "Installing LangChain ecosystem..."
pip install langchain langchain-community langchain-openai langchain-core

echo "Installing distributed computing frameworks..."
pip install "ray[default,serve,tune,rllib]" "dask[complete]"

echo "Installing Jupyter and notebook tools..."
pip install jupyter jupyterlab ipython ipywidgets

echo "Installing data science libraries..."
pip install pandas numpy scipy scikit-learn matplotlib seaborn plotly

echo "Installing web frameworks..."
pip install fastapi uvicorn gradio streamlit

echo "Installing development tools..."
pip install black isort flake8 mypy pytest

echo "Installing HTTP and utility libraries..."
pip install requests aiohttp httpx python-dotenv pydantic

echo "Installing additional ML tools..."
pip install mlflow wandb tensorboard

# Create activation script
cat > $($EnvConfig.ActivateScript) << 'EOF'
#!/bin/bash
echo "Activating AI/ML Python Environment..."
source $($EnvConfig.VenvPath)/bin/activate
echo "Environment activated. Python location: `$(which python)`"
echo "Pip version: `$(pip --version)`"
EOF

chmod +x $($EnvConfig.ActivateScript)

echo "Testing installations..."
python -c "import torch; print(f'✓ PyTorch: {torch.__version__}')" || echo "✗ PyTorch (failed)"
python -c "import transformers; print(f'✓ Transformers: {transformers.__version__}')" || echo "✗ Transformers (failed)"
python -c "import ray; print(f'✓ Ray: {ray.__version__}')" || echo "✗ Ray (failed)"

echo "Python AI/ML environment setup completed on remote server!"
echo "Environment location: $($EnvConfig.VenvPath)"
echo "Activation script: $($EnvConfig.ActivateScript)"
"@
    
    # Create temporary script file
    $tempScript = [System.IO.Path]::GetTempFileName() + ".sh"
    Set-Content -Path $tempScript -Value $remoteSetupScript -Encoding UTF8
    
    try {
        # Copy script to remote server and execute
        $remoteScript = "/tmp/remote-python-setup.sh"
        scp $tempScript "$($EnvConfig.RemoteUser)@$($EnvConfig.RemoteHost):$remoteScript"
        ssh "$($EnvConfig.RemoteUser)@$($EnvConfig.RemoteHost)" "chmod +x $remoteScript && $remoteScript"
        
        Write-Host "Remote Python environment setup completed!" -ForegroundColor Green
        Write-Host "To activate remotely: ssh $($EnvConfig.RemoteUser)@$($EnvConfig.RemoteHost) 'source $($EnvConfig.ActivateScript)'" -ForegroundColor Cyan
        Write-Host "To run Jupyter remotely: ssh -L 8888:localhost:8888 $($EnvConfig.RemoteUser)@$($EnvConfig.RemoteHost) 'source $($EnvConfig.ActivateScript) && jupyter lab --ip=0.0.0.0 --no-browser'" -ForegroundColor Cyan
    }
    catch {
        Write-Host "ERROR: Failed to setup remote environment: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Please ensure SSH access is properly configured." -ForegroundColor Yellow
    }
    finally {
        # Clean up temporary files
        Remove-Item $tempScript -ErrorAction SilentlyContinue
        ssh "$($EnvConfig.RemoteUser)@$($EnvConfig.RemoteHost)" "rm -f /tmp/remote-python-setup.sh" -ErrorAction SilentlyContinue
    }
}

# Show help
function Show-Help {
    Write-Host "Cloud Development Environment Setup Script" -ForegroundColor Green
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\setup-cloud-dev.ps1 [options]" -ForegroundColor White
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -InstallTools       Install development tools (Git, VS Code, Docker, etc.)" -ForegroundColor White
    Write-Host "  -ConfigureSSH       Configure SSH connection to cloud VM" -ForegroundColor White
    Write-Host "  -SetupPython        Setup Python AI/ML environment" -ForegroundColor White
    Write-Host "  -GenerateVMScript   Generate Linux setup script for cloud VM" -ForegroundColor White
    Write-Host "  -Environment        Target environment: 'powershell', 'wsl2', or 'remote' (default: powershell)" -ForegroundColor White
    Write-Host "  -ProjectRoot        Root directory for project files (default: %USERPROFILE%)" -ForegroundColor White
    Write-Host "  -RemoteHost         Remote server hostname/IP (required for -Environment remote)" -ForegroundColor White
    Write-Host "  -RemoteUser         Remote server username (required for -Environment remote)" -ForegroundColor White
    Write-Host "  -CloudIP            Cloud VM IP address (for SSH configuration)" -ForegroundColor White
    Write-Host "  -Username           Username for cloud VM (default: devuser)" -ForegroundColor White
    Write-Host "  -Help               Show this help message" -ForegroundColor White
    Write-Host ""
    Write-Host "Environment Options:" -ForegroundColor Yellow
    Write-Host "  powershell          Setup in native Windows PowerShell environment" -ForegroundColor White
    Write-Host "  wsl2                Setup in Windows Subsystem for Linux 2" -ForegroundColor White
    Write-Host "  remote              Setup on a remote Linux server via SSH" -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\setup-cloud-dev.ps1 -InstallTools -SetupPython" -ForegroundColor Green
    Write-Host "  .\setup-cloud-dev.ps1 -SetupPython -Environment wsl2 -ProjectRoot C:\\Projects" -ForegroundColor Green
    Write-Host "  .\setup-cloud-dev.ps1 -SetupPython -Environment remote -RemoteHost 192.168.1.100 -RemoteUser ubuntu" -ForegroundColor Green
    Write-Host "  .\setup-cloud-dev.ps1 -ConfigureSSH -CloudIP 192.168.1.100 -Username devuser" -ForegroundColor Green
    Write-Host "  .\setup-cloud-dev.ps1 -GenerateVMScript" -ForegroundColor Green
    Write-Host ""
    Write-Host "What this script does:" -ForegroundColor Cyan
    Write-Host "  LocalSetup:"
    Write-Host "    - Installs Chocolatey and Scoop package managers"
    Write-Host "    - Installs development tools (Git, VS Code, Docker, etc.)"
    Write-Host "    - Sets up Python AI/ML environment"
    Write-Host "    - Installs VS Code extensions"
    Write-Host ""
    Write-Host "  CloudManagement:"
    Write-Host "    - Creates SSH configuration for cloud VM"
    Write-Host "    - Generates management scripts"
    Write-Host "    - Sets up file synchronization tools"
    Write-Host ""
    Write-Host "  GenerateVMScript:"
    Write-Host "    - Creates Linux setup script for cloud VM"
    Write-Host "    - Installs Docker, AI/ML tools, and development stack"
    Write-Host "    - Sets up Docker Compose configuration"
}

# Main execution logic
if ($Help) {
    Show-Help
    exit 0
}

Write-Host "=== Cloud Development Environment Setup ===" -ForegroundColor Cyan
Write-Host "Starting setup process..." -ForegroundColor Yellow

# Initialize environment configuration
$envConfig = Initialize-Environment -Environment $Environment -ProjectRoot $ProjectRoot -RemoteHost $RemoteHost -RemoteUser $RemoteUser

if ($InstallTools) {
    Install-DevelopmentTools
}

if ($ConfigureSSH) {
    if ([string]::IsNullOrEmpty($CloudIP)) {
        Write-Error-Custom "CloudIP parameter is required when using -ConfigureSSH"
        exit 1
    }
    Set-SSHConnection -CloudIP $CloudIP -Username $Username
}

if ($SetupPython) {
    Setup-PythonEnvironment -EnvConfig $envConfig
}

if ($GenerateVMScript) {
    New-VMScript
}

if (!$InstallTools -and !$ConfigureSSH -and !$SetupPython -and !$GenerateVMScript) {
    Show-Help
}

Write-Host "\n=== Setup Complete! ===" -ForegroundColor Green
Write-Host "Your $Environment development environment is ready." -ForegroundColor White
if ($Environment -eq "remote") {
    Write-Host "Remote environment configured at: $($envConfig.RemoteUser)@$($envConfig.RemoteHost)" -ForegroundColor Cyan
} else {
    Write-Host "Check the generated files in the current directory." -ForegroundColor White
}