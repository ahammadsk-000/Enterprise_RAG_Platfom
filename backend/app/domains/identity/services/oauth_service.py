"""OAuth2 / OIDC SSO (Google, Microsoft) via Authlib.

Providers are registered only when their client id/secret are configured, so the
platform runs locally without SSO. The login route redirects to the provider; the
callback exchanges the code, fetches userinfo, upserts the `User` + `OAuthAccount`,
ensures an organization membership, and issues platform tokens.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from authlib.integrations.starlette_client import OAuth

from app.core.config import get_settings

# Discovery documents for OIDC providers.
_PROVIDER_METADATA = {
    "google": "https://accounts.google.com/.well-known/openid-configuration",
    "microsoft": "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
}


def build_oauth() -> OAuth:
    """Construct an Authlib `OAuth` registry from configured providers."""
    settings = get_settings()
    oauth = OAuth()

    if settings.auth.google_client_id and settings.auth.google_client_secret:
        oauth.register(
            name="google",
            client_id=settings.auth.google_client_id,
            client_secret=settings.auth.google_client_secret,
            server_metadata_url=_PROVIDER_METADATA["google"],
            client_kwargs={"scope": "openid email profile"},
        )

    if settings.auth.microsoft_client_id and settings.auth.microsoft_client_secret:
        oauth.register(
            name="microsoft",
            client_id=settings.auth.microsoft_client_id,
            client_secret=settings.auth.microsoft_client_secret,
            server_metadata_url=_PROVIDER_METADATA["microsoft"],
            client_kwargs={"scope": "openid email profile"},
        )

    return oauth


@lru_cache(maxsize=1)
def get_oauth() -> OAuth:
    """Process-wide OAuth registry (built once from settings)."""
    return build_oauth()


def is_provider_enabled(oauth: OAuth, provider: str) -> bool:
    return provider in _PROVIDER_METADATA and oauth.create_client(provider) is not None


def extract_identity(userinfo: dict[str, Any]) -> tuple[str, str, str | None]:
    """Return `(provider_account_id, email, full_name)` from an OIDC userinfo claim set."""
    account_id = str(userinfo.get("sub") or userinfo.get("oid") or userinfo["email"])
    email = str(userinfo["email"]).lower()
    name = userinfo.get("name")
    return account_id, email, name
