terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ==============================================================================
# 1. Enable Required APIs
# ==============================================================================
resource "google_project_service" "apis" {
  for_each = toset([
    "dialogflow.googleapis.com",      # Vertex AI Agents
    "servicedirectory.googleapis.com", # For Private Webhooks
    "compute.googleapis.com",
    "bigtable.googleapis.com",
    "cloudfunctions.googleapis.com",
    "run.googleapis.com"
  ])
  service            = each.key
  disable_on_destroy = false
}

# ==============================================================================
# 2. Networking (Consumer VPC for the Agent)
# ==============================================================================
resource "google_compute_network" "agent_vpc" {
  name                    = "agent-consumer-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.apis]
}

resource "google_compute_subnetwork" "agent_subnet" {
  name          = "agent-consumer-subnet"
  ip_cidr_range = "10.0.1.0/24"
  region        = var.region
  network       = google_compute_network.agent_vpc.id
}

# ==============================================================================
# 3. Private Service Connect (PSC) Endpoint
# ==============================================================================
# This IP represents the private tool (Bigtable Wrapper) inside the Agent's VPC
resource "google_compute_address" "psc_ip" {
  name         = "tool-psc-ip"
  region       = var.region
  subnetwork   = google_compute_subnetwork.agent_subnet.id
  address_type = "INTERNAL"
}

# The Forwarding Rule points to the Service Attachment of the private tool
resource "google_compute_forwarding_rule" "psc_endpoint" {
  name                  = "tool-psc-endpoint"
  region                = var.region
  network               = google_compute_network.agent_vpc.id
  ip_address            = google_compute_address.psc_ip.id
  target                = var.target_service_attachment # URI from the Producer side
  load_balancing_scheme = ""                            # Required for PSC
}

# ==============================================================================
# 4. Service Directory
# ==============================================================================
# Registers the PSC IP so Vertex AI Agent can "see" it
resource "google_service_directory_namespace" "agent_ns" {
  provider     = google
  namespace_id = "agent-tools"
  location     = var.region
  depends_on   = [google_project_service.apis]
}

resource "google_service_directory_service" "bigtable_service" {
  provider     = google
  service_id   = "bigtable-query"
  namespace    = google_service_directory_namespace.agent_ns.id

  metadata = {
    description = "Private access to Bigtable Tool"
  }
}

resource "google_service_directory_endpoint" "psc_map" {
  provider    = google
  endpoint_id = "psc-endpoint"
  service     = google_service_directory_service.bigtable_service.id
  address     = google_compute_address.psc_ip.address
  port        = 8080
}

# ==============================================================================
# 5. Vertex AI Agent (Dialogflow CX)
# ==============================================================================
resource "google_dialogflow_cx_agent" "main_agent" {
  display_name          = "enterprise-data-agent"
  location              = var.region
  default_language_code = "en"
  time_zone             = "America/Los_Angeles"

  advanced_settings {
    logging_settings {
      enable_stackdriver_logging = true
    }
  }

  depends_on = [google_project_service.apis]
}

# Output the Service Directory URI to configure the Webhook manually or via API
output "service_directory_uri" {
  value = "projects/${var.project_id}/locations/${var.region}/namespaces/${google_service_directory_namespace.agent_ns.namespace_id}/services/${google_service_directory_service.bigtable_service.service_id}"
}