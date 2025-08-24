#!/bin/bash
# Runpod Worker Startup Script
# Configures the GPU worker environment and connects to Ray cluster

set -e

echo "Starting Runpod worker setup..."

# Update system
apt-get update
apt-get install -y curl wget git htop vim tmux unzip jq tree

# Install Tailscale for secure networking
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up --authkey=${tailscale_auth_key} --hostname=runpod-worker-$(hostname)

# Configure SSH
mkdir -p /root/.ssh
echo "${ssh_public_key}" >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
chmod 700 /root/.ssh

# Start SSH service
service ssh start
systemctl enable ssh

# Install Python packages for AI/ML
pip install --upgrade pip
pip install ray[default] jupyter jupyterlab pandas numpy matplotlib seaborn scikit-learn
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install transformers datasets accelerate diffusers

# Configure Jupyter
mkdir -p /root/.jupyter
cat > /root/.jupyter/jupyter_lab_config.py << EOF
c.ServerApp.ip = '0.0.0.0'
c.ServerApp.port = 8888
c.ServerApp.open_browser = False
c.ServerApp.token = ''
c.ServerApp.password = ''
c.ServerApp.allow_root = True
c.ServerApp.notebook_dir = '/workspace'
EOF

# Create workspace directories
mkdir -p /workspace/{data,models,notebooks,scripts}
chmod -R 755 /workspace

# Configure Ray worker
cat > /workspace/ray_worker.py << EOF
import ray
import os
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_ray_worker():
    """Start Ray worker and connect to head node"""
    head_ip = "${ray_head_ip}"
    
    try:
        # Connect to Ray cluster
        ray.init(address=f"ray://{head_ip}:10001")
        logger.info(f"Successfully connected to Ray head at {head_ip}")
        
        # Keep worker alive
        while True:
            time.sleep(60)
            if not ray.is_initialized():
                logger.warning("Ray connection lost, attempting to reconnect...")
                ray.init(address=f"ray://{head_ip}:10001")
                
    except Exception as e:
        logger.error(f"Failed to connect to Ray head: {e}")
        # Fallback: start local Ray instance
        ray.init()
        logger.info("Started local Ray instance")

if __name__ == "__main__":
    start_ray_worker()
EOF

# Create systemd service for Ray worker
cat > /etc/systemd/system/ray-worker.service << EOF
[Unit]
Description=Ray Worker Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/workspace
ExecStart=/usr/bin/python3 /workspace/ray_worker.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=/workspace
Environment=RAY_TMPDIR=/workspace/ray_tmp

[Install]
WantedBy=multi-user.target
EOF

# Create Jupyter service
cat > /etc/systemd/system/jupyter.service << EOF
[Unit]
Description=Jupyter Lab Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/workspace
ExecStart=/usr/local/bin/jupyter lab --config=/root/.jupyter/jupyter_lab_config.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=/workspace

[Install]
WantedBy=multi-user.target
EOF

# Create GPU monitoring script
cat > /workspace/gpu_monitor.py << EOF
import GPUtil
import psutil
import time
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def monitor_resources():
    """Monitor GPU and system resources"""
    while True:
        try:
            # Get GPU info
            gpus = GPUtil.getGPUs()
            gpu_info = []
            for gpu in gpus:
                gpu_info.append({
                    'id': gpu.id,
                    'name': gpu.name,
                    'load': gpu.load * 100,
                    'memory_used': gpu.memoryUsed,
                    'memory_total': gpu.memoryTotal,
                    'memory_percent': (gpu.memoryUsed / gpu.memoryTotal) * 100,
                    'temperature': gpu.temperature
                })
            
            # Get system info
            system_info = {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'timestamp': datetime.now().isoformat()
            }
            
            # Log resource usage
            status = {
                'gpus': gpu_info,
                'system': system_info
            }
            
            with open('/workspace/resource_status.json', 'w') as f:
                json.dump(status, f, indent=2)
            
            # Log high usage
            for gpu in gpu_info:
                if gpu['load'] > 90:
                    logger.warning(f"High GPU load: {gpu['name']} at {gpu['load']:.1f}%")
                if gpu['memory_percent'] > 90:
                    logger.warning(f"High GPU memory: {gpu['name']} at {gpu['memory_percent']:.1f}%")
            
            if system_info['cpu_percent'] > 90:
                logger.warning(f"High CPU usage: {system_info['cpu_percent']:.1f}%")
            
            time.sleep(30)  # Monitor every 30 seconds
            
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    monitor_resources()
EOF

# Install GPU monitoring dependencies
pip install GPUtil psutil

# Create GPU monitoring service
cat > /etc/systemd/system/gpu-monitor.service << EOF
[Unit]
Description=GPU Monitor Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/workspace
ExecStart=/usr/bin/python3 /workspace/gpu_monitor.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# Create cost tracking script
cat > /workspace/cost_tracker.sh << EOF
#!/bin/bash
# Track usage and estimated costs

START_TIME=\$(date +%s)
COST_PER_HOUR=0.50  # Adjust based on actual cost

while true; do
    CURRENT_TIME=\$(date +%s)
    RUNTIME_SECONDS=\$((CURRENT_TIME - START_TIME))
    RUNTIME_HOURS=\$(echo "scale=2; \$RUNTIME_SECONDS / 3600" | bc)
    ESTIMATED_COST=\$(echo "scale=2; \$RUNTIME_HOURS * \$COST_PER_HOUR" | bc)
    
    echo "{\"runtime_hours\": \$RUNTIME_HOURS, \"estimated_cost\": \$ESTIMATED_COST, \"timestamp\": \"\$(date -Iseconds)\"}" > /workspace/cost_status.json
    
    sleep 300  # Update every 5 minutes
done
EOF

chmod +x /workspace/cost_tracker.sh

# Create cost tracking service
cat > /etc/systemd/system/cost-tracker.service << EOF
[Unit]
Description=Cost Tracker Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/workspace
ExecStart=/bin/bash /workspace/cost_tracker.sh
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
EOF

# Install bc for calculations
apt-get install -y bc

# Create health check endpoint
cat > /workspace/health_check.py << EOF
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            health_status = {
                'status': 'healthy',
                'services': {
                    'ray': os.path.exists('/workspace/ray_tmp'),
                    'jupyter': True,
                    'gpu_monitor': os.path.exists('/workspace/resource_status.json'),
                    'cost_tracker': os.path.exists('/workspace/cost_status.json')
                }
            }
            
            self.wfile.write(json.dumps(health_status).encode())
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8000), HealthHandler)
    server.serve_forever()
EOF

# Create health check service
cat > /etc/systemd/system/health-check.service << EOF
[Unit]
Description=Health Check Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/workspace
ExecStart=/usr/bin/python3 /workspace/health_check.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start services
systemctl daemon-reload
systemctl enable ray-worker
systemctl enable jupyter
systemctl enable gpu-monitor
systemctl enable cost-tracker
systemctl enable health-check

# Start services
systemctl start ray-worker
systemctl start jupyter
systemctl start gpu-monitor
systemctl start cost-tracker
systemctl start health-check

# Create welcome script
cat > /workspace/welcome.py << EOF
import torch
import ray
from datetime import datetime

print("=" * 60)
print("🚀 Runpod AI Development Worker Ready!")
print("=" * 60)
print(f"Timestamp: {datetime.now()}")
print(f"CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU Count: {torch.cuda.device_count()}")
    for i in range(torch.cuda.device_count()):
        print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
print(f"Ray Head IP: ${ray_head_ip}")
print("\nServices:")
print("- Jupyter Lab: http://localhost:8888")
print("- Health Check: http://localhost:8000/health")
print("- SSH: ssh root@<pod-ip>")
print("\nDirectories:")
print("- Workspace: /workspace")
print("- Data: /workspace/data")
print("- Models: /workspace/models")
print("- Notebooks: /workspace/notebooks")
print("=" * 60)
EOF

# Run welcome script
python3 /workspace/welcome.py

# Create completion marker
touch /workspace/.setup_complete
echo "$(date): Runpod worker setup completed" >> /workspace/setup.log

echo "Runpod worker setup completed successfully!"