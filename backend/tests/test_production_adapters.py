import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import create_autospec

import jwt
import psycopg
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt import InvalidTokenError
from pytest import raises

from app.auth import SupabaseJwtVerifier
from app.content.repository import _PostgresConnection


def test_postgres_adapter_translates_placeholders_for_single_and_batch_writes() -> None:
    raw = create_autospec(psycopg.Connection, instance=True, spec_set=True)
    cursor = create_autospec(psycopg.Cursor, instance=True, spec_set=True)
    raw.cursor.return_value.__enter__.return_value = cursor
    connection = _PostgresConnection(raw)

    connection.execute("INSERT INTO sample VALUES (?, ?)", ("one", 1))
    connection.executemany("INSERT INTO sample VALUES (?, ?)", [("two", 2), ("three", 3)])

    raw.execute.assert_called_once_with("INSERT INTO sample VALUES (%s, %s)", ("one", 1))
    cursor.executemany.assert_called_once_with("INSERT INTO sample VALUES (%s, %s)", [("two", 2), ("three", 3)])
    raw.cursor.return_value.__exit__.assert_called_once()


def test_supabase_verifier_accepts_only_the_configured_owner() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier = SupabaseJwtVerifier(
        supabase_url="https://project.supabase.co",
        audience="authenticated",
        owner_user_id="owner-id",
    )
    verifier.jwks = SimpleNamespace(
        get_signing_key_from_jwt=lambda _: SimpleNamespace(key=private_key.public_key())
    )
    base_claims = {
        "aud": "authenticated",
        "iss": "https://project.supabase.co/auth/v1",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
    }
    owner_token = jwt.encode({**base_claims, "sub": "owner-id"}, private_key, algorithm="RS256")
    stranger_token = jwt.encode({**base_claims, "sub": "stranger-id"}, private_key, algorithm="RS256")

    assert asyncio.run(verifier.verify_claims(owner_token))["sub"] == "owner-id"
    with raises(InvalidTokenError):
        asyncio.run(verifier.verify_claims(stranger_token))
