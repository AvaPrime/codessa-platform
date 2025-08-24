# Remote AI Development Environment Guide

This guide provides comprehensive instructions for setting up remote development environments for AI/ML workloads, complementing the automated setup provided by our `setup-cloud-dev.ps1` script.

## Overview

Setting up a remote development environment for AI involves creating a development workspace on a remote machine (cloud VM or dedicated server) and accessing it from your local machine. This approach offers:

- **Compute Offloading**: Handle intensive AI/ML tasks on powerful remote hardware
- **Environment Consistency**: Standardized development environments across teams
- **Collaboration**: Shared access to development resources
- **Cost Efficiency**: Pay-per-use cloud resources vs. expensive local hardware

## 1. Choose a Remote Machine

### Cloud Providers

Select from popular cloud providers based on your needs:

- **AWS EC2**: Comprehensive instance types, spot instances for cost savings
- **Google Cloud Platform (GCP)**: Compute Engine with TPU support
- **Azure**: Machine Learning compute instances with integrated ML services
- **Specialized Platforms**: Runpod, Paperspace, Lambda Labs for GPU-focused workloads

### Machine Type Selection

Choose instance types based on your AI workload requirements:

- **CPU-Intensive**: Natural language processing, data preprocessing
- **GPU-Intensive**: Deep learning training, computer vision
- **Memory-Intensive**: Large model inference, big data processing
- **Balanced**: General development and experimentation

**Recommended Configurations:**
```
Light Development:  4 vCPU, 16GB RAM, 100GB SSD
Medium Workloads:   8 vCPU, 32GB RAM, 200GB SSD, 1x GPU (T4/V100)
Heavy Training:     16+ vCPU, 64GB+ RAM, 500GB+ SSD, 2+ GPU (A100/H100)
```

## 2. Remote Environment Setup

### Operating System

Recommended Linux distributions:
- **Ubuntu 20.04/22.04 LTS**: Best compatibility with AI/ML frameworks
- **CentOS/RHEL**: Enterprise environments
- **Amazon Linux**: AWS-optimized

### Networking Configuration

```bash
# Configure static IP (if needed)
sudo netplan apply

# Configure firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 8888  # Jupyter Lab
sudo ufw allow 6006  # TensorBoard
sudo ufw allow 8265  # Ray Dashboard
```

### User Management

```bash
# Create development user
sudo adduser aidev
sudo usermod -aG sudo aidev
sudo usermod -aG docker aidev

# Configure SSH keys
sudo mkdir -p /home/aidev/.ssh
sudo cp ~/.ssh/authorized_keys /home/aidev/.ssh/
sudo chown -R aidev:aidev /home/aidev/.ssh
sudo chmod 700 /home/aidev/.ssh
sudo chmod 600 /home/aidev/.ssh/authorized_keys
```

### Automated Setup with Our Script

Use our enhanced setup script for automated remote environment configuration:

```powershell
# Direct remote setup
.\setup-cloud-dev.ps1 -Environment remote -RemoteHost "your-server.com" -RemoteUser "aidev" -ProjectRoot "/home/aidev/projects"

# With custom SSH key
.\setup-cloud-dev.ps1 -Environment remote -RemoteHost "your-server.com" -RemoteUser "aidev" -SSHKeyPath "C:\Users\YourName\.ssh\id_rsa" -ProjectRoot "/home/aidev/ai-workspace"
```

This automatically:
- Creates Python virtual environment
- Installs comprehensive AI/ML stack (PyTorch, Transformers, LangChain, Ray, etc.)
- Sets up activation scripts
- Tests installations
- Configures development tools

## 3. Connect from Your Local Machine

### SSH Connection

```bash
# Basic SSH connection
ssh aidev@your-server.com

# SSH with port forwarding for Jupyter
ssh -L 8888:localhost:8888 aidev@your-server.com

# SSH with multiple port forwards
ssh -L 8888:localhost:8888 -L 6006:localhost:6006 -L 8265:localhost:8265 aidev@your-server.com
```

### VS Code Remote Development

1. Install the "Remote - SSH" extension in VS Code
2. Configure SSH connection:
   ```
   Host ai-server
       HostName your-server.com
       User aidev
       IdentityFile ~/.ssh/id_rsa
       LocalForward 8888 localhost:8888
       LocalForward 6006 localhost:6006
   ```
3. Connect via Command Palette: "Remote-SSH: Connect to Host"

### File Transfer

```bash
# SCP for single files
scp local-file.py aidev@your-server.com:/home/aidev/projects/

# Rsync for directories
rsync -avz --progress ./local-project/ aidev@your-server.com:/home/aidev/projects/remote-project/

# Using VS Code integrated file explorer (recommended)
# Files can be edited directly through Remote-SSH extension
```

## 4. Development Workflow

### Activate AI Environment

```bash
# SSH into server
ssh aidev@your-server.com

# Activate AI environment (created by our script)
source /home/aidev/projects/activate-ai-env.sh

# Verify installation
python -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')"
```

### Start Development Services

```bash
# Start Jupyter Lab
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root

# Start TensorBoard
tensorboard --logdir=./logs --host=0.0.0.0 --port=6006

# Start Ray cluster (if using distributed computing)
ray start --head --dashboard-host=0.0.0.0 --dashboard-port=8265
```

### Version Control Integration

```bash
# Clone your repositories
git clone https://github.com/your-username/ai-project.git
cd ai-project

# Configure Git (if not done)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Work with branches
git checkout -b feature/remote-development
# ... make changes ...
git add .
git commit -m "Implement remote training pipeline"
git push origin feature/remote-development
```

## 5. Advanced Features

### Development Containers

For reproducible environments, consider using Docker containers:

```dockerfile
# Dockerfile for AI development
FROM pytorch/pytorch:2.0.1-cuda11.7-cudnn8-devel

RUN apt-get update && apt-get install -y \
    git \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

RUN pip install transformers datasets accelerate jupyter

WORKDIR /workspace
EXPOSE 8888

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--allow-root", "--no-browser"]
```

### VPN Setup (Enhanced Security)

For sensitive projects, consider VPN access:

```bash
# Install WireGuard
sudo apt install wireguard

# Generate keys
wg genkey | tee privatekey | wg pubkey > publickey

# Configure WireGuard server
sudo nano /etc/wireguard/wg0.conf
```

### Resource Monitoring

```bash
# Monitor GPU usage
watch -n 1 nvidia-smi

# Monitor system resources
htop

# Monitor disk usage
df -h
du -sh /home/aidev/projects/*
```

## 6. Cost Optimization

### Automated Shutdown

```bash
# Create auto-shutdown script
echo '#!/bin/bash
if [ $(who | wc -l) -eq 0 ]; then
    sudo shutdown -h now
fi' > /home/aidev/auto-shutdown.sh

# Add to crontab (check every 30 minutes)
crontab -e
# Add: */30 * * * * /home/aidev/auto-shutdown.sh
```

### Spot Instances

Use cloud provider spot instances for significant cost savings:
- AWS Spot Instances: Up to 90% savings
- GCP Preemptible VMs: Up to 80% savings
- Azure Spot VMs: Up to 90% savings

### Storage Optimization

```bash
# Clean up unused packages
sudo apt autoremove
sudo apt autoclean

# Clean pip cache
pip cache purge

# Clean conda cache (if using conda)
conda clean --all
```

## 7. Troubleshooting

### Common Issues

**SSH Connection Issues:**
```bash
# Check SSH service
sudo systemctl status ssh

# Restart SSH service
sudo systemctl restart ssh

# Check firewall
sudo ufw status
```

**GPU Not Detected:**
```bash
# Check NVIDIA drivers
nvidia-smi

# Reinstall CUDA toolkit
sudo apt install nvidia-cuda-toolkit

# Verify PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"
```

**Out of Memory:**
```bash
# Check memory usage
free -h

# Check GPU memory
nvidia-smi

# Clear Python cache
python -c "import torch; torch.cuda.empty_cache()"
```

## 8. Integration with Our Setup Script

Our `setup-cloud-dev.ps1` script automates many of these steps:

### Features Covered
- ✅ Python virtual environment setup
- ✅ AI/ML library installation (PyTorch, Transformers, etc.)
- ✅ Development tools configuration
- ✅ SSH key management
- ✅ Activation script generation
- ✅ Installation testing

### Manual Steps Still Needed
- Cloud instance provisioning
- Operating system installation
- Network security configuration
- Advanced monitoring setup
- Cost optimization scripts

### Recommended Workflow

1. **Provision Cloud Instance**: Use cloud provider console/CLI
2. **Run Our Setup Script**: `setup-cloud-dev.ps1 -Environment remote`
3. **Configure Additional Security**: Firewall, VPN if needed
4. **Set Up Monitoring**: Resource usage, cost alerts
5. **Implement Auto-shutdown**: For cost optimization

## Conclusion

Remote AI development environments provide powerful, scalable, and cost-effective solutions for AI/ML workloads. Our automated setup script handles the complex software configuration, while this guide covers the infrastructure and advanced configuration aspects.

For questions or issues, refer to the main project documentation or create an issue in the repository.