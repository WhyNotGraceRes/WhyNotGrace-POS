"""Role-based access control.

Backend is the sole enforcer. Every state-changing or business-data-reading
endpoint must depend on require_roles(...) (or require any authenticated
staff via get_current_user). Never rely on the frontend hiding a button.
"""
from app.models.enums import UserRole

# Coarse capability groups referenced by routers. Kept explicit (not
# computed) so the access matrix is easy to audit.
ROLE_FULL_ACCESS = {UserRole.OWNER}
ROLE_OPERATIONAL = {UserRole.OWNER, UserRole.MANAGER}
ROLE_BILLING = {UserRole.OWNER, UserRole.MANAGER, UserRole.CASH_COUNTER}
ROLE_SERVICE = {UserRole.OWNER, UserRole.MANAGER, UserRole.SERVICE_COUNTER}
ROLE_KITCHEN = {UserRole.OWNER, UserRole.MANAGER, UserRole.KITCHEN}
ROLE_DELIVERY = {UserRole.OWNER, UserRole.MANAGER, UserRole.DELIVERY}
ROLE_ANY_STAFF = set(UserRole)
