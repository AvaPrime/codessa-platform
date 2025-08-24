# Hetzner Cloud Infrastructure - Main Configuration
# Control plane and networking setup

terraform {
  required_version = ">= 1.0"
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
    tailscale = {
      source  = "tailscale/tailscale"
      version = "~> 0.13"
    }
  }
}

# Configure Hetzner Cloud Provider
provider "hcloud" {
  token = var.hcloud_token
}

# Configure Tailscale Provider
provider "tailscale" {
  api_key = var.tailscale_api_key
  tailnet = var.tailscale_tailnet
}

# Create control plane using module
module "control_plane" {
  source = "./modules/control_plane"
  
  # Network configuration
  network_zone     = var.network_zone
  network_ip_range = var.network_ip_range
  
  # Server configuration
  server_type     = var.control_plane_server_type
  server_location = var.server_location
  server_image    = var.server_image
  
  # SSH configuration
  ssh_keys = var.ssh_keys
  
  # Tailscale configuration
  tailscale_auth_key = var.tailscale_auth_key
  
  # Tags
  labels = merge(var.common_labels, {
    role = "control-plane"
    tier = "production"
  })
}

# Create firewall for control plane
resource "hcloud_firewall" "control_plane" {
  name = "control-plane-fw"
  labels = var.common_labels

  # SSH access
  rule {
    direction = "in"
    port      = "22"
    protocol  = "tcp"
    source_ips = var.allowed_ssh_ips
  }

  # Ray head node
  rule {
    direction = "in"
    port      = "8265"
    protocol  = "tcp"
    source_ips = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
  }

  # Monitoring (Prometheus/Grafana)
  rule {
    direction = "in"
    port      = "3000"
    protocol  = "tcp"
    source_ips = var.allowed_monitoring_ips
  }

  rule {
    direction = "in"
    port      = "9090"
    protocol  = "tcp"
    source_ips = var.allowed_monitoring_ips
  }

  # Tailscale
  rule {
    direction = "in"
    port      = "41641"
    protocol  = "udp"
    source_ips = ["0.0.0.0/0"]
  }

  # Allow all outbound
  rule {
    direction = "out"
    protocol  = "tcp"
    destination_ips = ["0.0.0.0/0"]
  }

  rule {
    direction = "out"
    protocol  = "udp"
    destination_ips = ["0.0.0.0/0"]
  }
}

# Attach firewall to control plane
resource "hcloud_firewall_attachment" "control_plane" {
  firewall_id = hcloud_firewall.control_plane.id
  server_ids  = [module.control_plane.server_id]
}

# Create load balancer for high availability (optional)
resource "hcloud_load_balancer" "control_plane" {
  count = var.enable_load_balancer ? 1 : 0
  
  name               = "control-plane-lb"
  load_balancer_type = var.load_balancer_type
  location           = var.server_location
  labels             = var.common_labels

  target {
    type      = "server"
    server_id = module.control_plane.server_id
  }

  service {
    protocol         = "http"
    listen_port      = 80
    destination_port = 8000
    health_check {
      protocol = "http"
      port     = 8000
      path     = "/health"
    }
  }

  service {
    protocol         = "tcp"
    listen_port      = 8265
    destination_port = 8265
  }
}

# Create volume for persistent data
resource "hcloud_volume" "control_plane_data" {
  name     = "control-plane-data"
  size     = var.data_volume_size
  location = var.server_location
  labels   = var.common_labels
}

# Attach volume to control plane
resource "hcloud_volume_attachment" "control_plane_data" {
  volume_id = hcloud_volume.control_plane_data.id
  server_id = module.control_plane.server_id
  automount = true
}

# Create snapshot schedule for backups
resource "hcloud_server_backup" "control_plane" {
  count     = var.enable_backups ? 1 : 0
  server_id = module.control_plane.server_id
  type      = "backup"
  labels    = merge(var.common_labels, {
    backup_schedule = "daily"
  })
}