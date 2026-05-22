"""Identity ORM models. Importing this package registers all tables on Base.metadata."""

from app.domains.identity.models.api_key import ApiKey
from app.domains.identity.models.membership import Membership
from app.domains.identity.models.oauth_account import OAuthAccount
from app.domains.identity.models.organization import Organization
from app.domains.identity.models.permission import Permission, Role, role_permissions
from app.domains.identity.models.user import User

__all__ = [
    "ApiKey",
    "Membership",
    "OAuthAccount",
    "Organization",
    "Permission",
    "Role",
    "User",
    "role_permissions",
]
