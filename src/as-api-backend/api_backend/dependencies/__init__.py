"""This module provides dependencies for the API backend.

It includes functions to verify the source IP address of incoming requests
and ensure it matches a whitelisted IP address stored in AWS Systems Manager
(SSM).
"""

# Local Modules
from api_backend.dependencies.dependencies import (
    verify_source_ip,
    get_current_user,
    get_allowed_ip_from_ssm,
    require_admin_user,
)

__all__ = [
    "verify_source_ip",
    "get_current_user",
    "get_allowed_ip_from_ssm",
    "require_admin_user",
]
