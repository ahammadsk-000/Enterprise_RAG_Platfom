"""OAuth2 / OIDC SSO endpoints (Google, Microsoft).

Flow:
  GET /auth/oauth/{provider}/login     → 302 redirect to the provider's consent screen
  GET /auth/oauth/{provider}/callback  → exchange code, JIT-provision/login, issue tokens

Providers are only mounted when configured (see `AUTH_*_CLIENT_ID/SECRET`); calling an
unconfigured provider returns 404. State/PKCE are handled by Authlib via the session.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.deps import AuthServiceDep
from app.core.config import get_settings
from app.core.exceptions import AuthError, NotFoundError
from app.domains.identity.services.oauth_service import extract_identity, get_oauth

router = APIRouter()


def _client(provider: str):  # type: ignore[no-untyped-def]
    client = get_oauth().create_client(provider)
    if client is None:
        raise NotFoundError(f"SSO provider '{provider}' is not configured.")
    return client


@router.get("/{provider}/login", summary="Begin SSO login")
async def oauth_login(provider: str, request: Request) -> RedirectResponse:
    client = _client(provider)
    redirect_uri = str(request.url_for("oauth_callback", provider=provider))
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/{provider}/callback", name="oauth_callback", summary="SSO callback")
async def oauth_callback(provider: str, request: Request, service: AuthServiceDep):  # type: ignore[no-untyped-def]
    client = _client(provider)
    try:
        token = await client.authorize_access_token(request)
    except Exception as exc:  # Authlib raises various errors on a bad/expired exchange
        raise AuthError("SSO authorization failed.") from exc

    userinfo = token.get("userinfo")
    if userinfo is None:
        userinfo = await client.userinfo(token=token)

    account_id, email, full_name = extract_identity(dict(userinfo))
    result = await service.sso_login(provider, account_id, email, full_name)

    settings = get_settings()
    if settings.auth.sso_redirect_url:
        fragment = f"access_token={result.tokens.access_token}&refresh_token={result.tokens.refresh_token}"
        return RedirectResponse(url=f"{settings.auth.sso_redirect_url}#{fragment}")
    return JSONResponse(content=result.tokens.model_dump())
