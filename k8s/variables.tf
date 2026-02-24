variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "The Google Cloud Region"
  type        = string
  default     = "us-central1"
}

variable "target_service_attachment" {
  description = "The URI of the Producer Service Attachment (The private tool's exposure point)"
  type        = string
  # Example: projects/producer-project/regions/us-central1/serviceAttachments/my-tool-attachment
}