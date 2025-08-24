# Control Plane Module Variables

# Network Configuration
variable "network_zone" {
  description = "Network zone for resources"
  type        = string
  default     = "eu-central"
}

variable "network_ip_range" {
  description = "IP range for the private network"
  type        = string
  default     = "10.0.0.0/16"
}

# Server Configuration
variable "server_type" {
  description = "Server type for control plane"
  type        = string
  default     = "cx31"
  
  validation {
    condition = contains([
      "cx11", "cx21", "cx31", "cx41", "cx51",
      "cpx11", "cpx21", "cpx31", "cpx41", "cpx51",
      "ccx11", "ccx21", "ccx31", "ccx41", "ccx51", "ccx62"
    ], var.server_type)
    error_message = "Server type must be a valid Hetzner Cloud server type."
  }
}

variable "server_location" {
  description = "Server location"
  type        = string
  default     = "nbg1"
  
  validation {
    condition = contains([
      "nbg1", "fsn1", "hel1", "ash", "hil"
    ], var.server_location)
    error_message = "Server location must be a valid Hetzner Cloud location."
  }
}

variable "server_image" {
  description = "Server image to use"
  type        = string
  default     = "ubuntu-22.04"
  
  validation {
    condition = contains([
      "ubuntu-20.04", "ubuntu-22.04", "ubuntu-24.04",
      "debian-11", "debian-12",
      "centos-stream-8", "centos-stream-9",
      "rocky-8", "rocky-9",
      "fedora-38", "fedora-39"
    ], var.server_image)
    error_message = "Server image must be a supported Linux distribution."
  }
}

# SSH Configuration
variable "ssh_keys" {
  description = "List of SSH key IDs to add to the server"
  type        = list(string)
  default     = []
}

# Tailscale Configuration
variable "tailscale_auth_key" {
  description = "Tailscale auth key for node registration"
  type        = string
  sensitive   = true
}

# Labels and Tagging
variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default = {
    project    = "ai-development"
    component  = "control-plane"
    managed_by = "terraform"
  }
}

# High Availability Configuration
variable "enable_floating_ip" {
  description = "Enable floating IP for high availability"
  type        = bool
  default     = false
}

variable "enable_backups" {
  description = "Enable automatic backups"
  type        = bool
  default     = true
}

# Security Configuration
variable "enable_protection" {
  description = "Enable deletion and rebuild protection"
  type        = bool
  default     = true
}

variable "enable_private_networking" {
  description = "Enable private networking"
  type        = bool
  default     = true
}

# TLS Configuration
variable "enable_tls_cert" {
  description = "Enable TLS certificate management"
  type        = bool
  default     = false
}

variable "tls_certificate" {
  description = "TLS certificate content"
  type        = string
  default     = ""
  sensitive   = true
}

variable "tls_private_key" {
  description = "TLS private key content"
  type        = string
  default     = ""
  sensitive   = true
}

# Resource Limits
variable "max_cpu_usage" {
  description = "Maximum CPU usage threshold (percentage)"
  type        = number
  default     = 80
  
  validation {
    condition     = var.max_cpu_usage > 0 && var.max_cpu_usage <= 100
    error_message = "CPU usage threshold must be between 1 and 100."
  }
}

variable "max_memory_usage" {
  description = "Maximum memory usage threshold (percentage)"
  type        = number
  default     = 85
  
  validation {
    condition     = var.max_memory_usage > 0 && var.max_memory_usage <= 100
    error_message = "Memory usage threshold must be between 1 and 100."
  }
}

# Monitoring Configuration
variable "enable_monitoring" {
  description = "Enable monitoring and alerting"
  type        = bool
  default     = true
}

variable "monitoring_retention_days" {
  description = "Number of days to retain monitoring data"
  type        = number
  default     = 30
  
  validation {
    condition     = var.monitoring_retention_days > 0 && var.monitoring_retention_days <= 365
    error_message = "Monitoring retention must be between 1 and 365 days."
  }
}

# Development Configuration
variable "development_mode" {
  description = "Enable development mode features"
  type        = bool
  default     = false
}

variable "auto_shutdown_enabled" {
  description = "Enable automatic shutdown for cost control"
  type        = bool
  default     = false
}

variable "auto_shutdown_time" {
  description = "Time to auto-shutdown (24h format, e.g., '22:00')"
  type        = string
  default     = "22:00"
  
  validation {
    condition     = can(regex("^([01]?[0-9]|2[0-3]):[0-5][0-9]$", var.auto_shutdown_time))
    error_message = "Auto shutdown time must be in HH:MM format (24-hour)."
  }
}

# Backup Configuration
variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7
  
  validation {
    condition     = var.backup_retention_days > 0 && var.backup_retention_days <= 30
    error_message = "Backup retention must be between 1 and 30 days."
  }
}

variable "backup_window" {
  description = "Preferred backup window (UTC time, e.g., '02:00-04:00')"
  type        = string
  default     = "02:00-04:00"
  
  validation {
    condition = can(regex("^([01]?[0-9]|2[0-3]):[0-5][0-9]-([01]?[0-9]|2[0-3]):[0-5][0-9]$", var.backup_window))
    error_message = "Backup window must be in HH:MM-HH:MM format."
  }
}

# Custom Configuration
variable "custom_user_data" {
  description = "Additional user data to append to cloud-init"
  type        = string
  default     = ""
}

variable "additional_packages" {
  description = "Additional packages to install during setup"
  type        = list(string)
  default     = []
}

variable "environment_variables" {
  description = "Environment variables to set on the server"
  type        = map(string)
  default     = {}
  sensitive   = true
}