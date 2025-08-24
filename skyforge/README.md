# 🚀 Laptop-Brain + Cloud-Muscle Development Environment

A complete implementation guide for creating a powerful development environment that combines local development convenience with cloud computing power.

## 📋 What's Included

This repository contains everything you need to set up a "laptop-brain + cloud-muscle" development environment:

- **📖 Complete Setup Guide** (`cloud-dev-environment-setup.md`) - Detailed 3-phase implementation playbook
- **🔧 Linux Setup Script** (`setup-cloud-dev.sh`) - Automated setup for Ubuntu/Debian cloud VMs
- **💻 Windows Management Script** (`setup-cloud-dev.ps1`) - Local Windows setup and cloud management tools

## Key Features

- **Multi-Environment Support**: Choose between PowerShell, WSL2, or remote server environments
- **Flexible Project Root**: Customize where virtual environments and project files are installed
- **Hybrid Architecture**: Local development with cloud compute resources
- **Automated Setup**: Scripts for both Windows (PowerShell) and Linux (Bash)
- **AI/ML Ready**: Pre-configured with PyTorch, Transformers, LangChain, Ray, Dask
- **Virtual Environment Management**: Proper Python venv setup with automatic pip upgrades across all environments
- **Development Tools**: VS Code integration, Docker, Git, and essential dev tools
- **Cross-Platform Activation Scripts**: Environment-specific activation scripts for easy access
- **Remote Server Support**: Direct setup and management of remote Linux servers via SSH
- **WSL2 Integration**: Seamless setup within Windows Subsystem for Linux 2
- **Cloud Integration**: Support for major cloud providers (AWS, Azure, GCP, Hetzner)
- **Cost Optimization**: Automated shutdown, resource monitoring, and cost alerts
- **Security**: SSH hardening, firewall configuration, and VPN support
- **Installation Testing**: Automatic verification of key package installations

## 🎯 Architecture Overview

```
┌─────────────────┐         ┌─────────────────────────────────┐
│   Laptop Brain  │◄────────┤        Cloud Muscle             │
│                 │         │                                 │
│ • VS Code       │         │ • Docker Containers            │
│ • Git           │         │ • AI/ML Frameworks             │
│ • SSH Client    │         │ • Ray Distributed Computing    │
│ • File Sync     │         │ • Jupyter Lab                  │
│                 │         │ • PostgreSQL, Redis, MinIO     │
└─────────────────┘         └─────────────────────────────────┘
        │                                    │
        └────────── Secure SSH Tunnel ──────┘
```

## 🚀 Quick Start

### Option 1: Cloud VM Setup (Recommended)

1. **Provision a cloud VM** (see provider comparison below)
2. **Run the setup script** on your VM:
   ```bash
   wget https://raw.githubusercontent.com/your-repo/setup-cloud-dev.sh
   chmod +x setup-cloud-dev.sh
   ./setup-cloud-dev.sh
   ```
3. **Configure your laptop** for remote connection
4. **Start developing** with full cloud power!

### Option 2: Local Windows Setup

1. **Run PowerShell as Administrator**
2. **Choose your environment** and execute the setup script:
   ```powershell
   # For local PowerShell environment
   .\setup-cloud-dev.ps1 -Environment powershell
   
   # For WSL2 environment
   .\setup-cloud-dev.ps1 -Environment wsl2 -ProjectRoot "/home/username/projects"
   
   # For remote server environment
   .\setup-cloud-dev.ps1 -Environment remote -RemoteHost "your-server.com" -RemoteUser "ubuntu"
   ```
3. **For non-remote environments**: Deploy to cloud VM using generated scripts
4. **Start development** with your chosen environment setup!

## 🏗️ Implementation Phases

| Phase | Goal | Time | Status |
|-------|------|------|--------|
| **1️⃣ Provision & Harden VM** | Secure, cost-effective server setup | 10-30 min | ✅ Automated |
| **2️⃣ Install Development Stack** | Docker, AI/ML frameworks, tools | 20-45 min | ✅ Automated |
| **3️⃣ Wire the Laptop** | Remote SSH, file sync, VS Code | 10-30 min | ✅ Automated |

## 💰 Cloud Provider Comparison

| Provider | CPU-Only | GPU-Ready | CLI Tool | Best For |
|----------|----------|-----------|----------|----------|
| **Hetzner Cloud** | $0.07/hr | N/A | `hcloud` | 💰 Budget development |
| **RunPod** | N/A | $0.38/hr | `runpodctl` | 🎮 GPU workloads |
| **Paperspace** | $0.10/hr | $0.45/hr | `paperspace` | 🎓 Beginners |
| **AWS EC2** | $0.20/hr | $1.20/hr | `aws` | 🏢 Enterprise |

**💡 Recommendation:** Start with Hetzner Cloud for CPU-only development, add RunPod GPU instance when needed.

## 🛠️ What Gets Installed

### Development Tools
- **Languages:** Python 3.11+, Node.js LTS, Go 1.21+, Rust
- **Containers:** Docker, Docker Compose
- **Databases:** PostgreSQL, Redis
- **Storage:** MinIO (S3-compatible)
- **Monitoring:** Portainer, htop

### AI/ML Stack
- **Frameworks:** PyTorch, Transformers, LangChain
- **Distributed:** Ray, Dask
- **Notebooks:** Jupyter Lab
- **Data Science:** Pandas, NumPy, Scikit-learn
- **APIs:** FastAPI, Gradio, Streamlit

### Development Environment
- **Editor:** VS Code with Remote-SSH
- **Version Control:** Git
- **Code Quality:** Black, isort, flake8, mypy
- **Testing:** pytest

## 📁 Project Structure After Setup

```
~/cloud-dev-project/
├── docker-compose.yml          # Service orchestration
├── notebooks/                  # Jupyter notebooks
│   └── welcome.ipynb          # Getting started notebook
├── data/                      # Data storage
├── start-dev-env.sh           # Start all services
├── stop-dev-env.sh            # Stop all services
└── status-dev-env.sh          # Check service status

~/ai-env/                      # Python virtual environment
├── bin/activate               # Activation script
└── lib/python3.11/site-packages/  # AI/ML packages

~/.ssh/                        # SSH configuration
└── config                     # SSH connection settings
```

## 🔗 Service Access Points

After setup, access your services at:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Jupyter Lab** | http://localhost:8888 | Token: `devtoken123` |
| **Ray Dashboard** | http://localhost:8265 | No auth required |
| **MinIO Console** | http://localhost:9001 | admin / minioadmin123 |
| **Portainer** | https://localhost:9443 | Setup on first visit |
| **PostgreSQL** | localhost:5432 | devuser / devpass123 |
| **Redis** | localhost:6379 | No auth required |

## 🔧 Daily Workflow

### Starting Your Environment
```bash
# On cloud VM
cd ~/cloud-dev-project
./start-dev-env.sh
```

### Connecting from Laptop
```bash
# SSH connection
ssh cloud-dev

# VS Code Remote
code --remote ssh-remote+cloud-dev
```

### File Synchronization
```bash
# Upload local changes
rsync -avz --exclude 'node_modules' ./local-project/ cloud-dev:~/projects/

# Download remote changes
rsync -avz cloud-dev:~/projects/ ./local-project/
```

### Stopping Services
```bash
# On cloud VM
cd ~/cloud-dev-project
./stop-dev-env.sh
```

## 🐍 Python AI/ML Environment

### Virtual Environment Management

Both Windows and Linux setups now include:
- ✅ **Automatic virtual environment creation** (`~/ai-env` or `%USERPROFILE%\ai-env`)
- ✅ **Automatic pip upgrades** to resolve version warnings
- ✅ **Installation verification** with test imports
- ✅ **Quick activation scripts** for easy environment access
- ✅ **Comprehensive package installation** with progress tracking

### Linux/Cloud VM Quick Start
```bash
# Activate AI environment
source ~/ai-env/bin/activate
# OR use the quick activation script
~/activate-ai-env.sh

# Test installations (automatically done during setup)
python3 -c "
import torch
import transformers
import ray
print(f'PyTorch: {torch.__version__}')
print(f'Transformers: {transformers.__version__}')
print(f'Ray: {ray.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
"

# Start Jupyter Lab
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root

# Start Ray cluster
ray start --head --port=10001 --dashboard-host=0.0.0.0
```

### Windows Setup

#### Environment Options

The script now supports three different environments:

- **PowerShell** (`-Environment powershell`): Sets up Python environment locally in Windows PowerShell
- **WSL2** (`-Environment wsl2`): Sets up Python environment in Windows Subsystem for Linux 2
- **Remote** (`-Environment remote`): Sets up Python environment on a remote Linux server

#### Usage Examples

```powershell
# PowerShell environment (default)
.\setup-cloud-dev.ps1 -Environment powershell

# WSL2 environment
.\setup-cloud-dev.ps1 -Environment wsl2 -ProjectRoot "/home/username/projects"

# Remote server environment
.\setup-cloud-dev.ps1 -Environment remote -RemoteHost "your-server.com" -RemoteUser "ubuntu" -ProjectRoot "/home/ubuntu/projects"

# Custom project root for any environment
.\setup-cloud-dev.ps1 -Environment powershell -ProjectRoot "C:\MyProjects"

# Setup with custom SSH key (for remote)
.\setup-cloud-dev.ps1 -Environment remote -RemoteHost "your-server.com" -RemoteUser "ubuntu" -SSHKeyPath "C:\Users\YourName\.ssh\id_rsa"

# Show help
.\setup-cloud-dev.ps1 -Help
```

#### Environment-Specific Features

**PowerShell Environment:**
- Installs development tools (Git, VS Code, Windows Terminal, etc.)
- Creates Python virtual environment in specified project root
- Generates activation script for easy access

**WSL2 Environment:**
- Sets up Python environment inside WSL2
- Automatically installs Python3 if not available
- Creates cross-platform activation scripts
- Supports Windows-WSL path conversion

**Remote Environment:**
- Sets up Python environment on remote Linux server
- Handles SSH connection and file transfer
- Provides remote activation and Jupyter Lab instructions
- Includes port forwarding examples

#### Activate AI/ML Environment

**PowerShell:**
```powershell
# Quick activation using generated script
& "C:\YourProjectRoot\activate-ai-env.ps1"

# Or activate manually
& "C:\YourProjectRoot\ai-env\Scripts\Activate.ps1"
```

**WSL2:**
```bash
# Activate in WSL2
source /path/to/your/project/activate-ai-env.sh

# Or from Windows
wsl bash -c 'source /path/to/your/project/activate-ai-env.sh && python'
```

**Remote:**
```bash
# SSH and activate
ssh username@server 'source /path/to/project/activate-ai-env.sh'

# Run Jupyter Lab remotely with port forwarding
ssh -L 8888:localhost:8888 username@server 'source /path/to/project/activate-ai-env.sh && jupyter lab --ip=0.0.0.0 --no-browser'
```

#### Test Installations

```powershell
# Test installations (automatically done during setup)
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import transformers; print(f'Transformers: {transformers.__version__}')"
python -c "import ray; print(f'Ray: {ray.__version__}')"  
```

## 🔒 Security Best Practices

- ✅ **SSH Key Authentication** - No password login
- ✅ **Firewall Configuration** - Only necessary ports open
- ✅ **Regular Updates** - Automated security patches
- ✅ **Non-root User** - Principle of least privilege
- ✅ **VPN Option** - Tailscale for private networking

## 💡 Cost Optimization Tips

1. **Use Spot Instances** - Save up to 90% on compute costs
2. **Stop When Idle** - Don't pay for unused resources
3. **Right-size Resources** - Start small, scale as needed
4. **Monitor Usage** - Set up billing alerts
5. **Use CPU-only for Development** - Add GPU only when needed

## 🚨 Troubleshooting

### Common Issues

**SSH Connection Failed**
```bash
# Check SSH service
sudo systemctl status ssh

# Verify firewall
sudo ufw status

# Test connection
ssh -v cloud-dev
```

**Docker Services Won't Start**
```bash
# Check Docker status
sudo systemctl status docker

# Restart Docker
sudo systemctl restart docker

# Check logs
docker-compose logs
```

**Ray Cluster Issues**
```bash
# Check Ray status
ray status

# Restart Ray
ray stop
ray start --head --dashboard-host=0.0.0.0
```

**Port Forwarding Not Working**
```bash
# Check SSH config
cat ~/.ssh/config

# Test port forwarding
ssh -L 8888:localhost:8888 cloud-dev
```

## 📚 Additional Resources

- **VS Code Remote Development** - [Official Guide](https://code.visualstudio.com/docs/remote/ssh)
- **Docker Compose** - [Documentation](https://docs.docker.com/compose/)
- **Ray Distributed Computing** - [Getting Started](https://docs.ray.io/en/latest/)
- **Jupyter Lab** - [User Guide](https://jupyterlab.readthedocs.io/)

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙋‍♂️ Support

If you encounter issues:

1. Check the troubleshooting section above
2. Search existing issues
3. Create a new issue with:
   - Your OS and version
   - Cloud provider used
   - Error messages
   - Steps to reproduce

---

**Happy coding with your laptop-brain + cloud-muscle setup! 🚀**