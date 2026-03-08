"""RBAC package — Agent onboarding and permission enforcement."""

from rbac.models import AgentRole, AgentRegistration, PermissionCheckRequest
from rbac.client import RBACClient

__all__ = ["AgentRole", "AgentRegistration", "PermissionCheckRequest", "RBACClient"]
