from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient
from mcp.server.auth.provider import AccessToken, TokenVerifier

from app.config import settings


@dataclass(frozen=True)
class Identity:
    user_id: str
    claims: dict[str, Any]


class SupabaseJwtVerifier(TokenVerifier):
    def __init__(
        self, *, supabase_url: str, audience: str, owner_user_id: str, oauth_client_id: str | None = None,
    ) -> None:
        base_url = supabase_url.rstrip("/")
        self.issuer = f"{base_url}/auth/v1"
        self.audience = audience
        self.owner_user_id = owner_user_id
        self.oauth_client_id = oauth_client_id
        self.jwks = PyJWKClient(f"{self.issuer}/.well-known/jwks.json", cache_keys=True, lifespan=600)

    def _decode(self, token: str) -> dict[str, Any]:
        signing_key = self.jwks.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256", "EdDSA"],
            audience=self.audience,
            issuer=self.issuer,
            options={"require": ["exp", "iss", "sub"]},
        )
        if claims.get("sub") != self.owner_user_id:
            raise jwt.InvalidTokenError("Token does not belong to the configured ContentOps owner.")
        if self.oauth_client_id and claims.get("client_id") != self.oauth_client_id:
            raise jwt.InvalidTokenError("Token was not issued to the configured MCP OAuth client.")
        return claims

    async def verify_claims(self, token: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._decode, token)

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            claims = await self.verify_claims(token)
        except (jwt.PyJWTError, ValueError):
            return None
        raw_scopes = claims.get("scope", "")
        scopes = raw_scopes if isinstance(raw_scopes, list) else str(raw_scopes).split()
        return AccessToken(
            token=token,
            client_id=str(claims.get("client_id", "supabase-auth")),
            scopes=scopes,
            expires_at=int(claims["exp"]),
            subject=str(claims["sub"]),
            claims=claims,
        )


@lru_cache(maxsize=1)
def get_supabase_verifier() -> SupabaseJwtVerifier:
    if not settings.supabase_url or not settings.contentops_owner_user_id:
        raise RuntimeError("Supabase auth requires SUPABASE_URL and CONTENTOPS_OWNER_USER_ID.")
    return SupabaseJwtVerifier(
        supabase_url=settings.supabase_url,
        audience=settings.supabase_jwt_audience,
        owner_user_id=settings.contentops_owner_user_id,
    )


def get_mcp_verifier() -> SupabaseJwtVerifier:
    if not settings.supabase_url or not settings.contentops_owner_user_id or not settings.mcp_public_url:
        raise RuntimeError("MCP requires SUPABASE_URL, CONTENTOPS_OWNER_USER_ID and MCP_PUBLIC_URL.")
    if not settings.mcp_oauth_client_id:
        raise RuntimeError("MCP requires a pre-registered MCP_OAUTH_CLIENT_ID.")
    return SupabaseJwtVerifier(
        supabase_url=settings.supabase_url,
        audience=settings.mcp_public_url,
        owner_user_id=settings.contentops_owner_user_id,
        oauth_client_id=settings.mcp_oauth_client_id,
    )


async def require_identity(
    authorization: Annotated[str | None, Header()] = None,
) -> Identity:
    if settings.auth_mode == "local":
        return Identity(user_id="local-owner", claims={"auth_mode": "local"})

    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A Supabase bearer token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = await get_supabase_verifier().verify_claims(token)
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The Supabase session is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    return Identity(user_id=str(claims["sub"]), claims=claims)
