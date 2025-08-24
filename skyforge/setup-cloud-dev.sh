#!/bin/bash

# Cloud Development Environment Setup Script
# This script automates the "laptop-brain + cloud-muscle" setup process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   log_error "This script should not be run as root. Please run as a regular user with sudo privileges."
   exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Helper function to create Hetzner Cloud VM
create_hetzner_vm() {
    local vm_name="${1:-dev-muscle}"
    local ssh_key="${2:-my-ssh-key}"
    
    if ! command_exists hcloud; then
        log_error "hcloud CLI not found. Install it first: https://github.com/hetznercloud/cli"
        return 1
    fi
    
    if [[ -z "$HCLOUD_TOKEN" ]]; then
        log_error "HCLOUD_TOKEN environment variable not set"
        return 1
    fi
    
    log_info "Creating Hetzner Cloud VM: $vm_name"
    hcloud server create \
        --name "$vm_name" \
        --image ubuntu-22.04 \
        --type cx41 \
        --ssh-key "$ssh_key" \
        --user-data "#cloud-config
runcmd:
  - echo 'net.ipv4.ip_forward = 1' >> /etc/sysctl.conf
  - sysctl -p"
    
    local vm_ip=$(hcloud server ip "$vm_name")
    log_success "VM created successfully. IP: $vm_ip"
    echo "$vm_ip"
}

# Helper function to create AWS EC2 instance
create_aws_vm() {
    local vm_name="${1:-dev-muscle}"
    local key_name="${2:-my-ssh-key}"
    local security_group="${3:-sg-xxxxxxxx}"
    
    if ! command_exists aws; then
        log_error "AWS CLI not found. Install it first: https://aws.amazon.com/cli/"
        return 1
    fi
    
    log_info "Creating AWS EC2 instance: $vm_name"
    aws ec2 run-instances \
        --image-id ami-0dba2cb6798deb6d8 \
        --instance-type c5.2xlarge \
        --key-name "$key_name" \
        --security-group-ids "$security_group" \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$vm_name}]"
    
    # Wait for instance to be running
    log_info "Waiting for instance to be running..."
    aws ec2 wait instance-running --filters "Name=tag:Name,Values=$vm_name"
    
    local vm_ip=$(aws ec2 describe-instances \
        --filters "Name=tag:Name,Values=$vm_name" "Name=instance-state-name,Values=running" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
    
    log_success "EC2 instance created successfully. IP: $vm_ip"
    echo "$vm_ip"
}

# Phase 1: System Setup and Hardening
phase1_system_setup() {
    log_info "Phase 1: System Setup and Hardening"
    
    # Update system
    log_info "Updating system packages..."
    sudo apt update && sudo apt upgrade -y
    
    # Install essential packages
    log_info "Installing essential packages..."
    sudo apt install -y curl wget git vim htop tree unzip build-essential software-properties-common apt-transport-https ca-certificates gnupg lsb-release
    
    # Configure firewall
    log_info "Configuring firewall..."
    sudo ufw allow ssh
    sudo ufw allow 8000:9000/tcp  # Development servers
    sudo ufw allow 8888/tcp       # Jupyter
    sudo ufw allow 8265/tcp       # Ray Dashboard
    sudo ufw --force enable
    
    log_success "Phase 1 completed: System setup and hardening"
}

# Phase 2: Install Development Stack
phase2_dev_stack() {
    log_info "Phase 2: Installing Development Stack"
    
    # Install Docker
    if ! command_exists docker; then
        log_info "Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
        
        # Install Docker Compose
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        
        log_success "Docker installed successfully"
    else
        log_info "Docker already installed, skipping..."
    fi
    
    # Install Node.js
    if ! command_exists node; then
        log_info "Installing Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
        sudo apt-get install -y nodejs
        log_success "Node.js installed successfully"
    else
        log_info "Node.js already installed, skipping..."
    fi
    
    # Install Python 3.11+
    if ! command_exists python3.11; then
        log_info "Installing Python 3.11..."
        sudo add-apt-repository ppa:deadsnakes/ppa -y
        sudo apt update
        sudo apt install -y python3.11 python3.11-pip python3.11-venv python3.11-dev
        log_success "Python 3.11 installed successfully"
    else
        log_info "Python 3.11 already installed, skipping..."
    fi
    
    # Install Go
    if ! command_exists go; then
        log_info "Installing Go..."
        GO_VERSION="1.21.5"
        wget https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz
        sudo tar -C /usr/local -xzf go${GO_VERSION}.linux-amd64.tar.gz
        echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
        rm go${GO_VERSION}.linux-amd64.tar.gz
        log_success "Go installed successfully"
    else
        log_info "Go already installed, skipping..."
    fi
    
    # Install Rust
    if ! command_exists rustc; then
        log_info "Installing Rust..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source ~/.cargo/env
        log_success "Rust installed successfully"
    else
        log_info "Rust already installed, skipping..."
    fi
    
    log_success "Phase 2 completed: Development stack installed"
}

# Phase 3: AI/ML Framework Setup
phase3_ai_setup() {
    log_info "Phase 3: Setting up AI/ML Framework"
    
    # Create Python virtual environment
    if [ ! -d "~/ai-env" ]; then
        log_info "Creating Python virtual environment..."
        python3.11 -m venv ~/ai-env
        source ~/ai-env/bin/activate
        
        # Upgrade pip
        pip install --upgrade pip
        
        # Install PyTorch (CPU version by default, GPU version if CUDA detected)
        if command_exists nvidia-smi; then
            log_info "CUDA detected, installing PyTorch with GPU support..."
            pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
        else
            log_info "Installing PyTorch CPU version..."
            pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
        fi
        
        # Install core AI/ML packages
        log_info "Installing AI/ML packages..."
        pip install transformers datasets accelerate
        pip install langchain langchain-community langchain-openai
        pip install "ray[default,serve,tune,rllib]"
        pip install "dask[complete]"
        pip install jupyter jupyterlab
        pip install pandas numpy scipy scikit-learn matplotlib seaborn plotly
        pip install fastapi uvicorn gradio streamlit
        pip install black isort flake8 mypy pytest
        pip install requests aiohttp httpx
        pip install python-dotenv pydantic
        
        log_success "AI/ML environment created successfully"
    else
        log_info "AI environment already exists, skipping..."
    fi
    
    log_success "Phase 3 completed: AI/ML framework setup"
}

# Phase 4: Create Docker Compose Configuration
phase4_docker_setup() {
    log_info "Phase 4: Creating Docker Compose configuration"
    
    # Create project directory
    mkdir -p ~/cloud-dev-project
    cd ~/cloud-dev-project
    
    # Create docker-compose.yml
    cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  jupyter:
    image: jupyter/tensorflow-notebook:latest
    ports:
      - "8888:8888"
    volumes:
      - ./notebooks:/home/jovyan/work
      - ./data:/home/jovyan/data
    environment:
      - JUPYTER_ENABLE_LAB=yes
      - JUPYTER_TOKEN=devtoken123
    command: start-notebook.sh --NotebookApp.token='devtoken123'

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=devdb
      - POSTGRES_USER=devuser
      - POSTGRES_PASSWORD=devpass123
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U devuser -d devdb"]
      interval: 30s
      timeout: 10s
      retries: 3

  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin123
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  portainer:
    image: portainer/portainer-ce:latest
    ports:
      - "9443:9443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer_data:/data
    command: -H unix:///var/run/docker.sock

volumes:
  redis_data:
  postgres_data:
  minio_data:
  portainer_data:
EOF

    # Create directories
    mkdir -p notebooks data
    
    # Create a sample notebook
    cat > notebooks/welcome.ipynb << 'EOF'
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Welcome to Your Cloud Development Environment\n",
    "\n",
    "This is your cloud-based development environment with:\n",
    "- Jupyter Lab for interactive development\n",
    "- Redis for caching\n",
    "- PostgreSQL for database\n",
    "- MinIO for object storage\n",
    "- Ray for distributed computing\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import sys\n",
    "import torch\n",
    "import pandas as pd\n",
    "import numpy as np\n",
    "\n",
    "print(f'Python version: {sys.version}')\n",
    "print(f'PyTorch version: {torch.__version__}')\n",
    "print(f'CUDA available: {torch.cuda.is_available()}')\n",
    "print(f'Pandas version: {pd.__version__}')\n",
    "print(f'NumPy version: {np.__version__}')"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python",
   "version": "3.11.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
EOF

    log_success "Phase 4 completed: Docker configuration created"
}

# Phase 5: Create Management Scripts
phase5_management_scripts() {
    log_info "Phase 5: Creating management scripts"
    
    cd ~/cloud-dev-project
    
    # Create start script
    cat > start-dev-env.sh << 'EOF'
#!/bin/bash

echo "Starting Cloud Development Environment..."

# Start Docker services
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Activate AI environment and start Ray
source ~/ai-env/bin/activate
ray start --head --dashboard-host=0.0.0.0 --dashboard-port=8265 --disable-usage-stats

echo "Development environment started!"
echo "Access points:"
echo "- Jupyter Lab: http://localhost:8888 (token: devtoken123)"
echo "- Ray Dashboard: http://localhost:8265"
echo "- MinIO Console: http://localhost:9001 (admin/minioadmin123)"
echo "- Portainer: https://localhost:9443"
echo "- PostgreSQL: localhost:5432 (devuser/devpass123)"
echo "- Redis: localhost:6379"
EOF

    # Create stop script
    cat > stop-dev-env.sh << 'EOF'
#!/bin/bash

echo "Stopping Cloud Development Environment..."

# Stop Ray
ray stop

# Stop Docker services
docker-compose down

echo "Development environment stopped!"
EOF

    # Create status script
    cat > status-dev-env.sh << 'EOF'
#!/bin/bash

echo "=== Cloud Development Environment Status ==="
echo

echo "Docker Services:"
docker-compose ps
echo

echo "Ray Status:"
ray status 2>/dev/null || echo "Ray is not running"
echo

echo "System Resources:"
echo "CPU Usage:"
top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1"%"}'
echo "Memory Usage:"
free -h | awk 'NR==2{printf "%.1f/%.1fGB (%.2f%%)\n", $3/1024/1024, $2/1024/1024, $3*100/$2}'
echo "Disk Usage:"
df -h | grep -E '^/dev/' | awk '{print $1 ": " $3 "/" $2 " (" $5 ")"}'
EOF

    # Make scripts executable
    chmod +x start-dev-env.sh stop-dev-env.sh status-dev-env.sh
    
    log_success "Phase 5 completed: Management scripts created"
}

# Phase 6: Create SSH Configuration Template
phase6_ssh_config() {
    log_info "Phase 6: Creating SSH configuration template"
    
    # Get the current IP address
    CURRENT_IP=$(curl -s ifconfig.me || echo "YOUR_VM_IP")
    
    cat > ~/ssh-config-template.txt << EOF
# Add this to your laptop's ~/.ssh/config file
# Replace YOUR_VM_IP with the actual IP address: ${CURRENT_IP}
# Replace your_private_key with the path to your SSH private key

Host cloud-dev
    HostName ${CURRENT_IP}
    User $(whoami)
    Port 22
    IdentityFile ~/.ssh/your_private_key
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
EOF

    log_success "Phase 6 completed: SSH configuration template created"
}

# Show usage information
show_usage() {
    echo "Cloud Development Environment Setup Script"
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --create-hetzner VM_NAME SSH_KEY    Create Hetzner Cloud VM first"
    echo "  --create-aws VM_NAME KEY_NAME SG    Create AWS EC2 instance first"
    echo "  --help                              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                           # Setup on existing VM"
    echo "  $0 --create-hetzner dev-muscle my-ssh-key   # Create Hetzner VM then setup"
    echo "  $0 --create-aws dev-muscle my-key sg-123    # Create AWS instance then setup"
    echo ""
    echo "Environment Variables:"
    echo "  HCLOUD_TOKEN    Required for Hetzner Cloud operations"
    echo "  AWS_PROFILE     Optional for AWS operations"
}

# Main execution
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --create-hetzner)
                if [[ $# -lt 3 ]]; then
                    log_error "--create-hetzner requires VM_NAME and SSH_KEY arguments"
                    show_usage
                    exit 1
                fi
                log_info "Creating Hetzner Cloud VM first..."
                VM_IP=$(create_hetzner_vm "$2" "$3")
                if [[ $? -eq 0 ]]; then
                    log_success "VM created with IP: $VM_IP"
                    log_info "Waiting 30 seconds for VM to be ready..."
                    sleep 30
                else
                    log_error "Failed to create VM"
                    exit 1
                fi
                shift 3
                ;;
            --create-aws)
                if [[ $# -lt 4 ]]; then
                    log_error "--create-aws requires VM_NAME, KEY_NAME, and SECURITY_GROUP arguments"
                    show_usage
                    exit 1
                fi
                log_info "Creating AWS EC2 instance first..."
                VM_IP=$(create_aws_vm "$2" "$3" "$4")
                if [[ $? -eq 0 ]]; then
                    log_success "EC2 instance created with IP: $VM_IP"
                    log_info "Waiting 60 seconds for instance to be ready..."
                    sleep 60
                else
                    log_error "Failed to create EC2 instance"
                    exit 1
                fi
                shift 4
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    log_info "Starting Cloud Development Environment Setup"
    log_info "This will install Docker, Python, Node.js, Go, Rust, and AI/ML frameworks"
    
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Setup cancelled by user"
        exit 0
    fi
    
    # Execute phases
    phase1_system_setup
    phase2_dev_stack
    phase3_ai_setup
    phase4_docker_setup
    phase5_management_scripts
    phase6_ssh_config
    
    log_success "Setup completed successfully!"
    echo
    log_info "Next steps:"
    echo "1. Reboot the system to ensure all changes take effect: sudo reboot"
    echo "2. After reboot, go to ~/cloud-dev-project and run: ./start-dev-env.sh"
    echo "3. Copy the SSH config from ~/ssh-config-template.txt to your laptop's ~/.ssh/config"
    echo "4. Connect from VS Code using Remote-SSH extension"
    echo
    log_info "Access points after starting services:"
    echo "- Jupyter Lab: http://localhost:8888 (token: devtoken123)"
    echo "- Ray Dashboard: http://localhost:8265"
    echo "- MinIO Console: http://localhost:9001 (admin/minioadmin123)"
    echo "- Portainer: https://localhost:9443"
    echo
    log_warning "Remember to configure your cloud provider's firewall to allow the necessary ports!"
    
    if [[ -n "$VM_IP" ]]; then
        echo
        log_info "Your VM IP address is: $VM_IP"
        log_info "Update your SSH config with this IP address"
    fi
}

# Run main function
main "$@"