variable "region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for ML artefacts"
  type        = string
}

variable "ecr_repo_name" {
  description = "Name of the ECR repository for Docker images"
  type        = string
}

# Uncomment and define additional variables as needed, for example:
# variable "eks_cluster_name" {
#   description = "Name of the EKS cluster"
#   type        = string
# }
