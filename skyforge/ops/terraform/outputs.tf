# Terraform Outputs for Hetzner Cloud Infrastructure

# Server Information
output "control_plane_id" {
  description = "ID of the control plane server"
  value       = module.control_plane.server_id
}

output "control_plane_public_ip" {
  description = "Public IP address of the control plane server"
  value       = module.control_plane.public_ip
}

output "control_plane_private_ip" {
  description = "Private IP address of the control plane server"
  value       = module.control_plane.private_ip
}

output "control_plane_ipv6" {
  description = "IPv6 address of the control plane server"
  value       = module.control_plane.ipv6_address
}

# Network Information
output "network_id" {
  description = "ID of the private network"
  value       = module.control_plane.network_id
}

output "network_ip_range" {
  description = "IP range of the private network"
  value       = var.network_ip_range
}

# Load Balancer Information
output "load_balancer_public_ip" {
  description = "Public IP of the load balancer"
  value       = var.enable_load_balancer ? hcloud_load_balancer.control_plane[0].ipv4 : null
}

output "load_balancer_ipv6" {
  description = "IPv6 address of the load balancer"
  value       = var.enable_load_balancer ? hcloud_load_balancer.control_plane[0].ipv6 : null
}

# Storage Information
output "data_volume_id" {
  description = "ID of the data volume"
  value       = hcloud_volume.control_plane_data.id
}

output "data_volume_device" {
  description = "Device path of the data volume"
  value       = hcloud_volume_attachment.control_plane_data.device
}

# Firewall Information
output "firewall_id" {
  description = "ID of the control plane firewall"
  value       = hcloud_firewall.control_plane.id
}

# SSH Information
output "ssh_connection_string" {
  description = "SSH connection string for the control plane"
  value       = "ssh root@${module.control_plane.public_ip}"
}

# Service URLs
output "ray_dashboard_url" {
  description = "URL for Ray dashboard"
  value       = "http://${module.control_plane.public_ip}:${var.ray_head_port}"
}

output "grafana_url" {
  description = "URL for Grafana dashboard"
  value       = var.enable_monitoring ? "http://${module.control_plane.public_ip}:${var.grafana_port}" : null
}

output "prometheus_url" {
  description = "URL for Prometheus"
  value       = var.enable_monitoring ? "http://${module.control_plane.public_ip}:${var.prometheus_port}" : null
}

# Ansible Inventory Information
output "ansible_inventory" {
  description = "Ansible inventory information in YAML format"
  value = yamlencode({
    all = {
      hosts = {
        control_plane = {
          ansible_host = module.control_plane.public_ip
          ansible_user = "root"
          private_ip   = module.control_plane.private_ip
          server_id    = module.control_plane.server_id
          server_type  = var.control_plane_server_type
          location     = var.server_location
        }
      }
      vars = {
        network_ip_range     = var.network_ip_range
        tailscale_tailnet    = var.tailscale_tailnet
        ray_head_port        = var.ray_head_port
        prometheus_port      = var.prometheus_port
        grafana_port         = var.grafana_port
        data_volume_device   = hcloud_volume_attachment.control_plane_data.device
        enable_monitoring    = var.enable_monitoring
        enable_github_runner = var.enable_github_runner
        github_repo_url      = var.github_repo_url
      }
    }
    control_plane = {
      hosts = ["control_plane"]
    }
    ray_head = {
      hosts = ["control_plane"]
    }
    monitoring = {
      hosts = var.enable_monitoring ? ["control_plane"] : []
    }
    github_runners = {
      hosts = var.enable_github_runner ? ["control_plane"] : []
    }
  })
}

# Cost Information
output "estimated_monthly_cost" {
  description = "Estimated monthly cost in EUR"
  value = {
    server_cost = {
      cx31 = 15.12  # Approximate cost for cx31
    }
    volume_cost = var.data_volume_size * 0.0476  # €0.0476 per GB per month
    load_balancer_cost = var.enable_load_balancer ? 5.83 : 0  # lb11 cost
    total_estimated = 15.12 + (var.data_volume_size * 0.0476) + (var.enable_load_balancer ? 5.83 : 0)
  }
}

# Security Information
output "security_summary" {
  description = "Security configuration summary"
  value = {
    firewall_enabled     = true
    private_network      = var.enable_private_networking
    deletion_protection  = var.enable_protection
    backup_enabled       = var.enable_backups
    tailscale_enabled    = true
    ssh_keys_count       = length(var.ssh_keys)
    allowed_ssh_sources  = length(var.allowed_ssh_ips)
  }
}

# Tailscale Information
output "tailscale_info" {
  description = "Tailscale network information"
  value = {
    tailnet = var.tailscale_tailnet
    node_name = "control-plane-${module.control_plane.server_id}"
  }
  sensitive = false
}

# Development Information
output "development_info" {
  description = "Development environment information"
  value = {
    development_mode = var.development_mode
    auto_shutdown_hours = var.auto_shutdown_hours
    devcontainer_ready = true
    vscode_remote_ready = true
  }
}

# Backup Information
output "backup_info" {
  description = "Backup configuration information"
  value = {
    backups_enabled = var.enable_backups
    backup_schedule = "daily"
    volume_snapshots = true
    retention_policy = "7 days"
  }
}