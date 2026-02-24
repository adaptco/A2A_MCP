# Deployment Guide

This guide provides a comprehensive overview of the deployment pipeline for the MCP Control Plane application.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environments](#environments)
- [Workflows](#workflows)
- [Kubernetes Manifests](#kubernetes-manifests)
- [Docker Compose](#docker-compose)
- [Local Development](#local-development)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Docker
- kubectl
- kustomize
- AWS CLI

## Environments

- **staging**: For testing new features.
- **production**: For the live application.

## Workflows

- `docker-build-push.yml`: Builds and pushes the Docker image to Docker Hub.
- `test.yml`: Runs tests and linting.
- `deploy.yml`: Deploys the application to Kubernetes.

## Kubernetes Manifests

- `deployment.yaml`: Defines the Deployment, Service, ConfigMap, HorizontalPodAutoscaler, and PodDisruptionBudget.
- `rbac.yaml`: Defines the ServiceAccount, Role, and NetworkPolicy.
- `extras.yaml`: Defines a CronJob, ServiceMonitor, and Namespace.

## Docker Compose

- `docker-compose.staging.yaml`: For running the application in a staging environment.
- `docker-compose.prod.yaml`: For running the application in a production environment.

## Local Development

1. Create a `.env.staging` file from the `.env.staging.example` file.
2. Run `docker-compose -f docker-compose.staging.yaml up -d`

## Deployment

1. Manually trigger the `deploy.yml` workflow from the GitHub Actions tab.
2. Select the environment to deploy to.

## Troubleshooting

- ...
