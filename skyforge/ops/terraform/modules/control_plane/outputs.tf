# Control Plane Module Outputs

# Server Information
output "server_id" {
  description = "ID of the control plane server"
  value       = hcloud_server.control_plane.id
}

output "server_name" {
  description = "Name of the control plane server"
  value       = hcloud_server.control_plane.name
}

output "public_ip" {
  description = "Public IPv4 address of the control plane server"
  value       = hcloud_server.control_plane.ipv4_address
}

output "private_ip" {
  description = "Private IP address of the control plane server"
  value       = hcloud_server_network.control_plane.ip
}

output "ipv6_address" {
  description = "IPv6 address of the control plane server"
  value       = hcloud_server.control_plane.ipv6_address
}

# Network Information
output "network_id" {
  description = "ID of the private network"
  value       = hcloud_network.main.id
}

output "network_name" {
  description = "Name of the private network"
  value       = hcloud_network.main.name
}

output "network_ip_range" {
  description = "IP range of the private network"
  value       = hcloud_network.main.ip_range
}

output "subnet_id" {
  description = "ID of the network subnet"
  value       = hcloud_network_subnet.main.id
}

# Server Specifications
output "server_type" {
  description = "Server type of the control plane"
  value       = hcloud_server.control_plane.server_type
}

output "server_location" {
  description = "Location of the control plane server"
  value       = hcloud_server.control_plane.location
}

output "server_datacenter" {
  description = "Datacenter of the control plane server"
  value       = hcloud_server.control_plane.datacenter
}

output "server_image" {
  description = "Image used for the control plane server"
  value       = hcloud_server.control_plane.image
}

# High Availability Information
output "floating_ip" {
  description = "Floating IP address (if enabled)"
  value       = var.enable_floating_ip ? hcloud_floating_ip.control_plane[0].ip_address : null
}

output "floating_ip_id" {
  description = "ID of the floating IP (if enabled)"
  value       = var.enable_floating_ip ? hcloud_floating_ip.control_plane[0].id : null
}

# Primary IP Information
output "primary_ipv4_id" {
  description = "ID of the primary IPv4 address"
  value       = hcloud_primary_ip.control_plane_ipv4.id
}

output "primary_ipv6_id" {
  description = "ID of the primary IPv6 address"
  value       = hcloud_primary_ip.control_plane_ipv6.id
}

# Security Information
output "ssh_keys" {
  description = "SSH keys associated with the server"
  value       = hcloud_server.control_plane.ssh_keys
}

output "backups_enabled" {
  description = "Whether backups are enabled"
  value       = hcloud_server.control_plane.backups
}

output "delete_protection" {
  description = "Whether delete protection is enabled"
  value       = hcloud_server.control_plane.delete_protection
}

output "rebuild_protection" {
  description = "Whether rebuild protection is enabled"
  value       = hcloud_server.control_plane.rebuild_protection
}

# Resource Status
output "server_status" {
  description = "Current status of the server"
  value       = hcloud_server.control_plane.status
}

output "server_created" {
  description = "Creation timestamp of the server"
  value       = hcloud_server.control_plane.created
}

# Connection Information
output "ssh_connection" {
  description = "SSH connection string"
  value       = "ssh root@${hcloud_server.control_plane.ipv4_address}"
}

output "ssh_connection_private" {
  description = "SSH connection string using private IP"
  value       = "ssh root@${hcloud_server_network.control_plane.ip}"
}

# Service URLs
output "service_urls" {
  description = "URLs for various services"
  value = {
    ssh        = "ssh://root@${hcloud_server.control_plane.ipv4_address}:22"
    ray        = "http://${hcloud_server.control_plane.ipv4_address}:8265"
    prometheus = "http://${hcloud_server.control_plane.ipv4_address}:9090"
    grafana    = "http://${hcloud_server.control_plane.ipv4_address}:3000"
    jupyter    = "http://${hcloud_server.control_plane.ipv4_address}:8888"
  }
}

# Labels and Metadata
output "labels" {
  description = "Labels applied to the server"
  value       = hcloud_server.control_plane.labels
}

output "placement_group_id" {
  description = "ID of the placement group"
  value       = hcloud_placement_group.control_plane.id
}

# Certificate Information
output "certificate_id" {
  description = "ID of the TLS certificate (if enabled)"
  value       = var.enable_tls_cert ? hcloud_certificate.control_plane[0].id : null
}

# Resource Costs (Estimated)
output "estimated_costs" {
  description = "Estimated monthly costs in EUR"
  value = {
    server = {
      cx11  = 3.29
      cx21  = 5.83
      cx31  = 10.05
      cx41  = 16.17
      cx51  = 28.45
      cpx11 = 4.51
      cpx21 = 8.21
      cpx31 = 15.12
      cpx41 = 28.45
      cpx51 = 54.89
    }[var.server_type]
    floating_ip = var.enable_floating_ip ? 1.19 : 0
    backups     = var.enable_backups ? 20 : 0  # Percentage of server cost
  }
}

# Ansible Integration
output "ansible_host_vars" {
  description = "Host variables for Ansible integration"
  value = {
    ansible_host                 = hcloud_server.control_plane.ipv4_address
    ansible_user                 = "root"
    ansible_ssh_private_key_file = "~/.ssh/id_rsa"
    server_id                    = hcloud_server.control_plane.id
    server_type                  = hcloud_server.control_plane.server_type
    private_ip                   = hcloud_server_network.control_plane.ip
    public_ip                    = hcloud_server.control_plane.ipv4_address
    network_id                   = hcloud_network.main.id
    location                     = hcloud_server.control_plane.location
    datacenter                   = hcloud_server.control_plane.datacenter
  }
}

# Development Information
output "development_info" {
  description = "Development environment information"
  value = {
    development_mode      = var.development_mode
    auto_shutdown_enabled = var.auto_shutdown_enabled
    auto_shutdown_time    = var.auto_shutdown_time
    monitoring_enabled    = var.enable_monitoring
  }
}

# Health Check Information
output "health_endpoints" {
  description = "Health check endpoints"
  value = {
    server_ping = "ping ${hcloud_server.control_plane.ipv4_address}"
    ssh_check   = "ssh -o ConnectTimeout=5 root@${hcloud_server.control_plane.ipv4_address} 'echo OK'"
    http_check  = "curl -f http://${hcloud_server.control_plane.ipv4_address}:8000/health || echo 'Service not ready'"
  }
}