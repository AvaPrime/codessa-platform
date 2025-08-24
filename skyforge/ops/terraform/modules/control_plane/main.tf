# Control Plane Module - Main Configuration
# Handles server creation, networking, and basic setup

terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
  }
}

# Create private network
resource "hcloud_network" "main" {
  name     = "ai-dev-network"
  ip_range = var.network_ip_range
  labels   = var.labels
}

# Create network subnet
resource "hcloud_network_subnet" "main" {
  type         = "cloud"
  network_id   = hcloud_network.main.id
  network_zone = var.network_zone
  ip_range     = var.network_ip_range
}

# Create SSH key resource if provided
resource "hcloud_ssh_key" "default" {
  count      = length(var.ssh_keys) > 0 ? 0 : 1
  name       = "control-plane-key"
  public_key = file("~/.ssh/id_rsa.pub")
  labels     = var.labels
}

# Create control plane server
resource "hcloud_server" "control_plane" {
  name        = "control-plane"
  image       = var.server_image
  server_type = var.server_type
  location    = var.server_location
  labels      = var.labels
  
  # SSH keys
  ssh_keys = length(var.ssh_keys) > 0 ? var.ssh_keys : [hcloud_ssh_key.default[0].id]
  
  # Enable backups and protection
  backups        = true
  delete_protection = true
  rebuild_protection = true
  
  # User data for initial setup
  user_data = templatefile("${path.module}/cloud-init.yml", {
    tailscale_auth_key = var.tailscale_auth_key
    hostname          = "control-plane"
  })
  
  # Network configuration
  network {
    network_id = hcloud_network.main.id
    ip         = cidrhost(var.network_ip_range, 10)  # .10 for control plane
  }
  
  # Ensure network subnet exists first
  depends_on = [hcloud_network_subnet.main]
  
  # Lifecycle management
  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      user_data,  # Prevent recreation on user_data changes
    ]
  }
}

# Create placement group for future scaling
resource "hcloud_placement_group" "control_plane" {
  name   = "control-plane-group"
  labels = var.labels
  type   = "spread"  # Spread across different physical hosts
}

# Create server with placement group
resource "hcloud_server_network" "control_plane" {
  server_id = hcloud_server.control_plane.id
  network_id = hcloud_network.main.id
  ip = cidrhost(var.network_ip_range, 10)
}

# Create floating IP for high availability (optional)
resource "hcloud_floating_ip" "control_plane" {
  count         = var.enable_floating_ip ? 1 : 0
  type          = "ipv4"
  home_location = var.server_location
  labels        = var.labels
  description   = "Floating IP for control plane high availability"
}

# Assign floating IP to server
resource "hcloud_floating_ip_assignment" "control_plane" {
  count          = var.enable_floating_ip ? 1 : 0
  floating_ip_id = hcloud_floating_ip.control_plane[0].id
  server_id      = hcloud_server.control_plane.id
}

# Create primary IP (IPv4)
resource "hcloud_primary_ip" "control_plane_ipv4" {
  name          = "control-plane-ipv4"
  datacenter    = "${var.server_location}-dc14"
  type          = "ipv4"
  assignee_id   = hcloud_server.control_plane.id
  auto_delete   = false
  labels        = var.labels
}

# Create primary IP (IPv6)
resource "hcloud_primary_ip" "control_plane_ipv6" {
  name          = "control-plane-ipv6"
  datacenter    = "${var.server_location}-dc14"
  type          = "ipv6"
  assignee_id   = hcloud_server.control_plane.id
  auto_delete   = false
  labels        = var.labels
}

# Create certificate for TLS (optional)
resource "hcloud_certificate" "control_plane" {
  count = var.enable_tls_cert ? 1 : 0
  name  = "control-plane-cert"
  labels = var.labels
  
  certificate = var.tls_certificate
  private_key = var.tls_private_key
}

# Local provisioner for post-creation tasks
resource "null_resource" "control_plane_setup" {
  depends_on = [hcloud_server.control_plane]
  
  # Trigger on server changes
  triggers = {
    server_id = hcloud_server.control_plane.id
  }
  
  # Wait for server to be ready
  provisioner "local-exec" {
    command = "sleep 30"  # Wait for server to boot
  }
  
  # Test SSH connectivity
  provisioner "local-exec" {
    command = "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 root@${hcloud_server.control_plane.ipv4_address} 'echo Server is ready'"
  }
}

# Data source for server info
data "hcloud_server" "control_plane" {
  id = hcloud_server.control_plane.id
  depends_on = [hcloud_server.control_plane]
}