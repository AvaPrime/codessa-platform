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

# Setup Python AI/ML environment
log_info "Setting up Python AI/ML environment..."
python3 -m venv ~/ai-env
source ~/ai-env/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install PyTorch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install AI/ML frameworks
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
pip install psycopg2-binary redis sqlalchemy
pip install celery flower
pip install mlflow wandb tensorboard

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
