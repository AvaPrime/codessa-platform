# Laptop-Brain + Cloud-Muscle Development Environment Setup

A practical, step-by-step playbook to create a powerful development environment that combines local development with cloud computing resources.

## Overview

| Phase | Goal | Typical Time |
|-------|------|-------------|
| 1️⃣ | Provision & Harden the VM | 10-30 min |
| 2️⃣ | Install the "brain-to-muscle" stack | 20-45 min |
| 3️⃣ | Wire the laptop | 10-30 min |

---

## 1️⃣ PROVISION & HARDEN THE VM

### 1.1 Choose a Provider (cost vs. GPU)

| Provider | Cheapest "GPU-ready" hour (≈) | Easy-to-scale CLI | Good for beginners |
|----------|-------------------------------|-------------------|--------------------|
| **Paperspace Gradient** | $0.45 / hr (P4000) | `paperspace` CLI | 🎓 VS Code Remote works out-of-the-box |
| **RunPod** | $0.38 / hr (RTX 4090) | `runpodctl` | Great for spot-instances |
| **AWS EC2 (g5.xlarge)** | $1.20 / hr (A10G) | `aws` CLI | Deep integration with IAM |
| **Hetzner Cloud** | $0.07 / hr (CPU-only) | `hcloud` CLI | Very cheap for pure-CPU work |

**💡 Quick tip:** Start with a **CPU-only** VM (e.g., 8 vCPU/32 GB RAM) to get the stack running, then add a GPU-enabled instance later when you need AI inference/training.

### 1.2 Spin-up a Basic Ubuntu 22.04 Instance

Below are generic scripts that work on most clouds via their CLI. Replace the placeholders (`<...>`) with your own values.

#### Hetzner Cloud Example

```bash
# Set your API token
export HCLOUD_TOKEN="YOUR_HCLOUD_API_TOKEN"

# 1️⃣ Create a server (8 CPU, 32 GB RAM, Ubuntu 22.04)
hcloud server create \
  --name dev-muscle \
  --image ubuntu-22.04 \
  --type cx41 \
  --ssh-key "my-ssh-key" \
  --user-data "#cloud-config
runcmd:
  - echo 'net.ipv4.ip_forward = 1' >> /etc/sysctl.conf
  - sysctl -p"

# 2️⃣ Capture its public IP
VM_IP=$(hcloud server ip dev-muscle)
echo "Your VM IP: $VM_IP"
```

#### AWS EC2 Example

```bash
# Create EC2 instance
aws ec2 run-instances \
  --image-id ami-0dba2cb6798deb6d8 \   # Ubuntu 22.04 LTS (us-east-1)
  --instance-type c5.2xlarge \
  --key-name my-ssh-key \
  --security-group-ids sg-xxxxxxxx \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=dev-muscle}]'

# Get the instance IP
VM_IP=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=dev-muscle" "Name=instance-state-name,Values=running" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
echo "Your VM IP: $VM_IP"
```

#### RunPod Example (GPU-enabled)

```bash
# Install runpodctl first: pip install runpodctl
runpodctl create pod \
  --name "dev-muscle-gpu" \
  --image-name "runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel-ubuntu22.04" \
  --gpu-type-id "NVIDIA RTX 4090" \
  --container-disk-in-gb 100 \
  --volume-in-gb 50
```

#### Paperspace Example

```bash
# Install paperspace CLI: npm install -g paperspace-node
paperspace machines create \
  --region "East Coast (NY2)" \
  --machineType "P4000" \
  --size 50 \
  --billingType "hourly" \
  --machineName "dev-muscle" \
  --templateId "t0nspur5"  # Ubuntu 22.04 template
```

### 1.3 Recommended VM Specifications

#### For Development (CPU-only)
- **CPU:** 8+ vCPUs
- **RAM:** 32+ GB
- **Storage:** 100+ GB SSD
- **OS:** Ubuntu 22.04 LTS or similar

#### For AI/ML Workloads (GPU-enabled)
- **CPU:** 8+ vCPUs
- **RAM:** 32+ GB
- **GPU:** RTX 4090, A10G, or similar
- **Storage:** 200+ GB SSD
- **OS:** Ubuntu 22.04 LTS with CUDA support

### 1.4 Initial VM Setup & Hardening

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y curl wget git vim htop tree unzip

# Create a non-root user (if not already done)
sudo adduser devuser
sudo usermod -aG sudo devuser

# Configure SSH key authentication
mkdir -p ~/.ssh
chmod 700 ~/.ssh
# Copy your public key to ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Disable password authentication (optional but recommended)
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# Configure firewall
sudo ufw allow ssh
sudo ufw allow 8000:9000/tcp  # For development servers
sudo ufw --force enable
```

---

## 2️⃣ INSTALL THE "BRAIN-TO-MUSCLE" STACK

### 2.1 Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### 2.2 Install Development Tools

```bash
# Install Node.js (via NodeSource)
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Python 3.11+
sudo apt install -y python3.11 python3.11-pip python3.11-venv

# Install Go
wget https://go.dev/dl/go1.21.5.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
```

### 2.3 Install AI/ML Framework Stack

```bash
# Create Python virtual environment
python3.11 -m venv ~/ai-env
source ~/ai-env/bin/activate

# Install core AI/ML packages
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install transformers datasets accelerate
pip install langchain langchain-community langchain-openai
pip install ray[default] dask[complete]
pip install jupyter jupyterlab
pip install pandas numpy scipy scikit-learn matplotlib seaborn
pip install fastapi uvicorn gradio streamlit

# Install additional tools
pip install black isort flake8 mypy pytest
```

### 2.4 Setup Container Orchestration

Create a `docker-compose.yml` for common services:

```yaml
version: '3.8'

services:
  jupyter:
    image: jupyter/tensorflow-notebook:latest
    ports:
      - "8888:8888"
    volumes:
      - ./notebooks:/home/jovyan/work
    environment:
      - JUPYTER_ENABLE_LAB=yes

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=devdb
      - POSTGRES_USER=devuser
      - POSTGRES_PASSWORD=devpass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data

volumes:
  redis_data:
  postgres_data:
  minio_data:
```

### 2.5 Install Ray Cluster (for distributed computing)

```bash
# Install Ray
pip install "ray[default,serve,tune,rllib]"

# Start Ray head node
ray start --head --port=6379 --dashboard-host=0.0.0.0 --dashboard-port=8265

# Verify Ray is running
ray status
```

---

## 3️⃣ WIRE THE LAPTOP

### 3.1 Setup VS Code Remote SSH

1. **Install VS Code Extensions:**
   - Remote - SSH
   - Remote - SSH: Editing Configuration Files
   - Docker
   - Python
   - Jupyter

2. **Configure SSH connection:**

```bash
# On your laptop, edit ~/.ssh/config
Host cloud-dev
    HostName YOUR_VM_IP
    User devuser
    Port 22
    IdentityFile ~/.ssh/your_private_key
    ForwardAgent yes
    # Port forwarding for common services
    LocalForward 8888 localhost:8888  # Jupyter
    LocalForward 8265 localhost:8265  # Ray Dashboard
    LocalForward 8000 localhost:8000  # Development server
```

3. **Connect to remote:**
   - Open VS Code
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
   - Type "Remote-SSH: Connect to Host"
   - Select `cloud-dev`

### 3.2 Setup File Synchronization

#### Option A: Using rsync (simple)

```bash
# Sync local project to remote
rsync -avz --exclude 'node_modules' --exclude '.git' ./local-project/ devuser@YOUR_VM_IP:~/remote-project/

# Sync back from remote
rsync -avz devuser@YOUR_VM_IP:~/remote-project/ ./local-project/
```

#### Option B: Using Git (recommended)

```bash
# Setup Git on remote
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Clone your repositories
git clone https://github.com/yourusername/your-repo.git
```

### 3.3 Setup CI/CD Hooks

Create a simple webhook server for automatic deployments:

```python
# webhook_server.py
from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    if request.method == 'POST':
        # Verify webhook (implement your security here)
        
        # Pull latest changes
        result = subprocess.run(['git', 'pull'], 
                              cwd='/path/to/your/repo',
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            # Restart services if needed
            subprocess.run(['docker-compose', 'restart'], 
                         cwd='/path/to/your/repo')
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9999)
```

### 3.4 Optional: Private Mesh Networking with Tailscale

```bash
# Install Tailscale on VM
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Install Tailscale on your laptop
# Follow instructions at https://tailscale.com/download

# Now you can access your VM via Tailscale IP without exposing ports
```

---

## 🚀 Quick Start Commands

Once everything is set up, here are the commands to get started:

```bash
# Start all services
docker-compose up -d

# Activate AI environment
source ~/ai-env/bin/activate

# Start Ray cluster
ray start --head --dashboard-host=0.0.0.0

# Start Jupyter Lab
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root

# Check all services
docker ps
ray status
```

## 📊 Monitoring & Management

### Useful Commands

```bash
# Monitor system resources
htop
df -h
nvidia-smi  # For GPU monitoring

# Docker management
docker system prune -a  # Clean up unused containers/images
docker-compose logs -f  # View logs

# Ray management
ray stop  # Stop Ray cluster
ray start --head  # Restart Ray
```

### Access Points

- **Jupyter Lab:** http://localhost:8888
- **Ray Dashboard:** http://localhost:8265
- **MinIO Console:** http://localhost:9001
- **Your App:** http://localhost:8000

---

## 💡 Tips & Best Practices

1. **Cost Management:**
   - Use spot instances when possible
   - Stop VMs when not in use
   - Monitor usage with cloud provider dashboards

2. **Security:**
   - Use SSH keys, not passwords
   - Keep systems updated
   - Use VPN or private networking when possible

3. **Development Workflow:**
   - Use Git for code synchronization
   - Containerize your applications
   - Set up automated backups for important data

4. **Performance:**
   - Use SSD storage
   - Monitor resource usage
   - Scale horizontally with Ray when needed

This setup gives you a powerful, scalable development environment that combines the convenience of local development with the power of cloud computing resources.