---
name: microsoft-foundry-rbac
description: Guide for managing RBAC for Microsoft Foundry resources, including user permissions, managed identity, and service principal setup.
---

# Microsoft Foundry RBAC Management

This skill enables agents to manage and audit Role-Based Access Control (RBAC) for Microsoft Foundry resources.

## Capabilities

- **Avatar Identity**: Map managed identities to agent avatars for seamless resource access.
- **Middleware Enforcement**: Implement policy-as-code checks within the orchestration middleware.
- **Token Gating**: Secure API endpoints via identity-based token validation.

## Workflows

### 1. Role Assignment
Use `az role assignment create` to grant permissions:
```bash
az role assignment create --role "Azure AI User" --assignee "<user-id>" --scope "<foundry-scope>"
```

### 2. Auditing
List current assignments:
```bash
az role assignment list --scope "<foundry-scope>" --output table
```

### 3. Service Principal Setup
Create SP for context-aware automation:
```bash
az ad sp create-for-rbac --name "foundry-cicd-sp" --role "Azure AI User" --scopes "<foundry-scope>"
```

## Best Practices
- Use **Least Privilege**: Start with `Azure AI User`.
- Prefer **Managed Identities** over Service Principals for internal service-to-service communication.
- Audit roles regularly via CI/CD gates.
