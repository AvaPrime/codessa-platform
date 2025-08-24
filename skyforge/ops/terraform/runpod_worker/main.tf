# Runpod GPU Worker Configuration
# Optional spot GPU instances for AI workloads

terraform {
  required_version = ">= 1.0"
  required_providers {
    http = {
      source  = "hashicorp/http"
      version = "~> 3.4"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
  }
}

# Variables for Runpod configuration
variable "runpod_api_key" {
  description = "Runpod API key"
  type        = string
  sensitive   = true
}

variable "gpu_type" {
  description = "GPU type to request"
  type        = string
  default     = "NVIDIA RTX 4090"
}

variable "gpu_count" {
  description = "Number of GPUs to request"
  type        = number
  default     = 1
}

variable "max_bid_per_gpu" {
  description = "Maximum bid per GPU per hour in USD"
  type        = number
  default     = 0.50
}

variable "container_image" {
  description = "Docker container image to run"
  type        = string
  default     = "runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04"
}

variable "container_disk_size" {
  description = "Container disk size in GB"
  type        = number
  default     = 50
}

variable "volume_size" {
  description = "Network volume size in GB"
  type        = number
  default     = 100
}

variable "ssh_public_key" {
  description = "SSH public key for access"
  type        = string
}

variable "tailscale_auth_key" {
  description = "Tailscale auth key for network connectivity"
  type        = string
  sensitive   = true
}

variable "ray_head_ip" {
  description = "IP address of Ray head node"
  type        = string
}

variable "auto_terminate_minutes" {
  description = "Auto-terminate after N minutes of inactivity"
  type        = number
  default     = 60
}

# Local variables
locals {
  startup_script = base64encode(templatefile("${path.module}/startup.sh", {
    tailscale_auth_key = var.tailscale_auth_key
    ray_head_ip       = var.ray_head_ip
    ssh_public_key    = var.ssh_public_key
  }))
  
  pod_config = {
    name           = "ai-dev-worker-${random_id.pod_suffix.hex}"
    imageName      = var.container_image
    gpuCount       = var.gpu_count
    vcpuCount      = 4
    memoryInGb     = 16
    containerDiskInGb = var.container_disk_size
    volumeInGb     = var.volume_size
    volumeMountPath = "/workspace"
    ports          = "22/tcp,8265/tcp,8888/tcp"
    env = [
      {
        key   = "JUPYTER_ENABLE_LAB"
        value = "yes"
      },
      {
        key   = "JUPYTER_TOKEN"
        value = ""
      },
      {
        key   = "RAY_HEAD_IP"
        value = var.ray_head_ip
      }
    ]
    startupScript = local.startup_script
  }
}

# Generate random suffix for pod name
resource "random_id" "pod_suffix" {
  byte_length = 4
}

# Create Runpod spot instance
resource "null_resource" "runpod_spot_pod" {
  triggers = {
    config_hash = sha256(jsonencode(local.pod_config))
  }
  
  # Create pod
  provisioner "local-exec" {
    command = <<-EOT
      curl -X POST "https://api.runpod.io/graphql" \
        -H "Authorization: Bearer ${var.runpod_api_key}" \
        -H "Content-Type: application/json" \
        -d '{
          "query": "mutation { podFindAndDeployOnDemand(input: { name: \"${local.pod_config.name}\", imageName: \"${local.pod_config.imageName}\", gpuCount: ${local.pod_config.gpuCount}, vcpuCount: ${local.pod_config.vcpuCount}, memoryInGb: ${local.pod_config.memoryInGb}, containerDiskInGb: ${local.pod_config.containerDiskInGb}, volumeInGb: ${local.pod_config.volumeInGb}, volumeMountPath: \"${local.pod_config.volumeMountPath}\", ports: \"${local.pod_config.ports}\", env: ${jsonencode(local.pod_config.env)}, startupScript: \"${local.pod_config.startupScript}\" }) { id costPerHr machine { podHostId } } }"
        }' > runpod_response.json
      
      # Extract pod ID
      POD_ID=$(cat runpod_response.json | jq -r '.data.podFindAndDeployOnDemand.id')
      echo "Pod ID: $POD_ID"
      echo $POD_ID > pod_id.txt
    EOT
  }
  
  # Cleanup on destroy
  provisioner "local-exec" {
    when    = destroy
    command = <<-EOT
      if [ -f pod_id.txt ]; then
        POD_ID=$(cat pod_id.txt)
        curl -X POST "https://api.runpod.io/graphql" \
          -H "Authorization: Bearer ${var.runpod_api_key}" \
          -H "Content-Type: application/json" \
          -d '{
            "query": "mutation { podTerminate(input: { podId: \"$POD_ID\" }) { id } }"
          }'
        rm -f pod_id.txt runpod_response.json
      fi
    EOT
  }
}

# Wait for pod to be ready
resource "null_resource" "wait_for_pod" {
  depends_on = [null_resource.runpod_spot_pod]
  
  provisioner "local-exec" {
    command = <<-EOT
      echo "Waiting for pod to be ready..."
      sleep 60
      
      # Get pod status
      POD_ID=$(cat pod_id.txt)
      for i in {1..30}; do
        STATUS=$(curl -s -X POST "https://api.runpod.io/graphql" \
          -H "Authorization: Bearer ${var.runpod_api_key}" \
          -H "Content-Type: application/json" \
          -d '{
            "query": "query { pod(input: { podId: \"'$POD_ID'\" }) { desiredStatus runtime { uptimeInSeconds } } }"
          }' | jq -r '.data.pod.desiredStatus')
        
        if [ "$STATUS" = "RUNNING" ]; then
          echo "Pod is running!"
          break
        fi
        
        echo "Pod status: $STATUS, waiting..."
        sleep 10
      done
    EOT
  }
}

# Get pod information
data "local_file" "pod_id" {
  depends_on = [null_resource.runpod_spot_pod]
  filename   = "${path.module}/pod_id.txt"
}

# Output pod information
output "pod_id" {
  description = "Runpod instance ID"
  value       = try(trimspace(data.local_file.pod_id.content), "")
}

output "pod_name" {
  description = "Runpod instance name"
  value       = local.pod_config.name
}

output "estimated_cost_per_hour" {
  description = "Estimated cost per hour in USD"
  value       = var.max_bid_per_gpu * var.gpu_count
}

output "gpu_configuration" {
  description = "GPU configuration"
  value = {
    type  = var.gpu_type
    count = var.gpu_count
  }
}

output "connection_info" {
  description = "Connection information"
  value = {
    ssh_command = "ssh root@<pod-ip> -p 22"
    jupyter_url = "http://<pod-ip>:8888"
    ray_worker  = "Connected to Ray head at ${var.ray_head_ip}:10001"
  }
}

# Cost monitoring
resource "null_resource" "cost_monitor" {
  depends_on = [null_resource.wait_for_pod]
  
  # Set up cost monitoring script
  provisioner "local-exec" {
    command = <<-EOT
      cat > cost_monitor.sh << 'EOF'
      #!/bin/bash
      POD_ID=$(cat pod_id.txt)
      COST_THRESHOLD=${var.max_bid_per_gpu * var.gpu_count * var.auto_terminate_minutes / 60}
      
      while true; do
        # Get pod runtime
        RUNTIME=$(curl -s -X POST "https://api.runpod.io/graphql" \
          -H "Authorization: Bearer ${var.runpod_api_key}" \
          -H "Content-Type: application/json" \
          -d '{
            "query": "query { pod(input: { podId: \"'$POD_ID'\" }) { runtime { uptimeInSeconds } } }"
          }' | jq -r '.data.pod.runtime.uptimeInSeconds // 0')
        
        RUNTIME_MINUTES=$((RUNTIME / 60))
        
        if [ $RUNTIME_MINUTES -gt ${var.auto_terminate_minutes} ]; then
          echo "Auto-terminating pod after $RUNTIME_MINUTES minutes"
          curl -X POST "https://api.runpod.io/graphql" \
            -H "Authorization: Bearer ${var.runpod_api_key}" \
            -H "Content-Type: application/json" \
            -d '{
              "query": "mutation { podTerminate(input: { podId: \"'$POD_ID'\" }) { id } }"
            }'
          break
        fi
        
        sleep 300  # Check every 5 minutes
      done
      EOF
      
      chmod +x cost_monitor.sh
      nohup ./cost_monitor.sh > cost_monitor.log 2>&1 &
    EOT
  }
}