# Terraform Variables for Hetzner Cloud Infrastructure

# Provider Configuration
variable "hcloud_token" {
  description = "Hetzner Cloud API token"
  type        = string
  sensitive   = true
}

variable "tailscale_api_key" {
  description = "Tailscale API key for network management"
  type        = string
  sensitive   = true
}

variable "tailscale_tailnet" {
  description = "Tailscale tailnet name"
  type        = string
}

variable "tailscale_auth_key" {
  description = "Tailscale auth key for node registration"
  type        = string
  sensitive   = true
}

# Network Configuration
variable "network_zone" {
  description = "Network zone for Hetzner Cloud resources"
  type        = string
  default     = "eu-central"
}

variable "network_ip_range" {
  description = "IP range for the private network"
  type        = string
  default     = "10.0.0.0/16"
}

# Server Configuration
variable "control_plane_server_type" {
  description = "Server type for control plane"
  type        = string
  default     = "cx31"  # 2 vCPU, 8GB RAM, 80GB SSD
}

variable "server_location" {
  description = "Server location"
  type        = string
  default     = "nbg1"  # Nuremberg
}

variable "server_image" {
  description = "Server image to use"
  type        = string
  default     = "ubuntu-22.04"
}

# SSH Configuration
variable "ssh_keys" {
  description = "List of SSH key names to add to servers"
  type        = list(string)
  default     = []
}

variable "allowed_ssh_ips" {
  description = "List of IP addresses allowed to SSH"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # Restrict this in production
}

variable "allowed_monitoring_ips" {
  description = "List of IP addresses allowed to access monitoring"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # Restrict this in production
}

# Load Balancer Configuration
variable "enable_load_balancer" {
  description = "Enable load balancer for high availability"
  type        = bool
  default     = false
}

variable "load_balancer_type" {
  description = "Load balancer type"
  type        = string
  default     = "lb11"  # Small load balancer
}

# Storage Configuration
variable "data_volume_size" {
  description = "Size of the data volume in GB"
  type        = number
  default     = 50
}

# Backup Configuration
variable "enable_backups" {
  description = "Enable automatic backups"
  type        = bool
  default     = true
}

# Tagging
variable "common_labels" {
  description = "Common labels to apply to all resources"
  type        = map(string)
  default = {
    project     = "ai-development"
    environment = "production"
    managed_by  = "terraform"
  }
}

# Cost Control
variable "max_monthly_cost" {
  description = "Maximum monthly cost threshold in EUR"
  type        = number
  default     = 100
}

variable "cost_alert_email" {
  description = "Email address for cost alerts"
  type        = string
  default     = ""
}

# Security Configuration
variable "enable_private_networking" {
  description = "Enable private networking"
  type        = bool
  default     = true
}

variable "enable_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = true
}

# Development Configuration
variable "development_mode" {
  description = "Enable development mode (less restrictive security)"
  type        = bool
  default     = false
}

variable "auto_shutdown_hours" {
  description = "Hours after which to auto-shutdown development instances"
  type        = number
  default     = 8
}

# Ray Configuration
variable "ray_head_port" {
  description = "Port for Ray head node dashboard"
  type        = number
  default     = 8265
}

variable "ray_worker_ports" {
  description = "Port range for Ray workers"
  type        = object({
    min = number
    max = number
  })
  default = {
    min = 10001
    max = 10100
  }
}

# Monitoring Configuration
variable "prometheus_port" {
  description = "Port for Prometheus"
  type        = number
  default     = 9090
}

variable "grafana_port" {
  description = "Port for Grafana"
  type        = number
  default     = 3000
}

variable "enable_monitoring" {
  description = "Enable monitoring stack (Prometheus/Grafana)"
  type        = bool
  default     = true
}

# GitHub Runner Configuration
variable "github_runner_token" {
  description = "GitHub runner registration token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "github_repo_url" {
  description = "GitHub repository URL for runner registration"
  type        = string
  default     = ""
}

variable "enable_github_runner" {
  description = "Enable GitHub Actions runner"
  type        = bool
  default     = false
}