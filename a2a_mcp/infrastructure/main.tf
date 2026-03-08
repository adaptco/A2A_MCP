terraform {
  required_version = ">= 1.3"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

# Configure the AWS provider. Set the region via a variable.
provider "aws" {
  region = var.region
}

# S3 bucket for storing training data and model artefacts.
resource "aws_s3_bucket" "ml_artifacts" {
  bucket = var.s3_bucket_name
  acl    = "private"

  versioning {
    enabled = true
  }
  tags = {
    Name = "ml-artifacts"
  }
}

# ECR repository to host Docker images for inference services.
resource "aws_ecr_repository" "ml_ecr" {
  name = var.ecr_repo_name

  image_tag_mutability = "MUTABLE"
  tags = {
    Name = "ml-ecr"
  }
}

# Additional resources such as IAM roles, Kubernetes clusters and service accounts can be added here.
# For example, to provision an EKS cluster you could use the AWS EKS module:
# module "eks" {
#   source          = "terraform-aws-modules/eks/aws"
#   cluster_name    = var.eks_cluster_name
#   cluster_version = "1.27"
#   vpc_id          = module.vpc.vpc_id
#   subnet_ids      = module.vpc.private_subnets
#   ...
# }
