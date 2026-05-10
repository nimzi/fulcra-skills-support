"""
Authentication utilities for Fulcra API
"""

from __future__ import annotations

import datetime
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Tuple

try:
    from fulcra_api.core import FulcraAPI, FULCRA_OIDC_DOMAIN, FULCRA_OIDC_CLIENT_ID
except ImportError:
    FulcraAPI = None
    FULCRA_OIDC_DOMAIN = None
    FULCRA_OIDC_CLIENT_ID = None


class FulcraAuthError(RuntimeError):
    """Raised when authentication operations fail"""
    pass


@dataclass(slots=True)
class TokenData:
    """Container for Fulcra authentication tokens"""
    access_token: Optional[str]
    refresh_token: Optional[str]
    access_token_expiration: Optional[datetime.datetime]

    @classmethod
    def from_dict(cls, data: dict) -> "TokenData":
        """Create TokenData from dictionary (e.g., loaded from JSON)"""
        exp = data.get("access_token_expiration") or data.get("expiration")
        if isinstance(exp, str):
            exp = parse_iso_datetime(exp)
        return cls(
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            access_token_expiration=exp,
        )

    def to_dict(self) -> dict:
        """Convert TokenData to dictionary for JSON serialization"""
        payload = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "access_token_expiration": self.access_token_expiration,
        }
        if isinstance(payload["access_token_expiration"], datetime.datetime):
            payload["access_token_expiration"] = payload["access_token_expiration"].isoformat()
        return payload


@dataclass(slots=True)
class TokenStore:
    """Manages persistent storage of authentication tokens"""
    path: Path

    def load(self) -> Optional[TokenData]:
        """Load token from file, return None if file doesn't exist"""
        if not self.path.exists():
            return None
        try:
            data = json.loads(self.path.read_text())
            return TokenData.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            raise FulcraAuthError(f"Invalid token file format: {e}")

    def save(self, token: TokenData) -> None:
        """Save token to file with secure permissions"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(token.to_dict(), indent=2))
        os.chmod(self.path, 0o600)


class TokenManager:
    """High-level token management operations"""
    
    def __init__(self, oidc_domain: Optional[str] = None, oidc_client_id: Optional[str] = None):
        self.oidc_domain = oidc_domain
        self.oidc_client_id = oidc_client_id
    
    def get_authenticated_client(self, token_store: TokenStore) -> Tuple[Any, TokenData]:
        """Get authenticated Fulcra API client, refreshing token if needed"""
        if FulcraAPI is None:
            raise FulcraAuthError("fulcra-api is not installed. Run: pip install fulcra-api")

        token = token_store.load()
        if not token:
            raise FulcraAuthError("No token file found. Use device authorization first.")

        client = FulcraAPI(
            oidc_domain=self.oidc_domain or FULCRA_OIDC_DOMAIN,
            oidc_client_id=self.oidc_client_id or FULCRA_OIDC_CLIENT_ID,
            access_token=token.access_token,
            access_token_expiration=token.access_token_expiration,
            refresh_token=token.refresh_token,
        )

        if is_token_valid(token.access_token_expiration):
            return client, token

        if not token.refresh_token:
            raise FulcraAuthError("No refresh token available. Re-authenticate with device flow.")

        # Refresh token using the Fulcra API library
        refreshed = client.refresh_access_token()
        if not refreshed:
            raise FulcraAuthError("Failed to refresh token. Re-authenticate with device flow.")

        # Get updated token data
        updated = TokenData(
            access_token=client.get_cached_access_token(),
            refresh_token=client.get_cached_refresh_token(),
            access_token_expiration=client.get_cached_access_token_expiration(),
        )

        if not updated.access_token:
            raise FulcraAuthError("Token refresh succeeded but no access token found.")

        token_store.save(updated)
        return client, updated


def run_device_auth(oidc_domain: Optional[str] = None, oidc_client_id: Optional[str] = None) -> TokenData:
    """
    Run OAuth2 device authorization flow
    
    Returns TokenData with access_token and refresh_token.
    Note: This may not include refresh_token depending on Fulcra API library version.
    """
    if FulcraAPI is None:
        raise FulcraAuthError("fulcra-api is not installed. Run: pip install fulcra-api")
    
    client = FulcraAPI(
        oidc_domain=oidc_domain or FULCRA_OIDC_DOMAIN,
        oidc_client_id=oidc_client_id or FULCRA_OIDC_CLIENT_ID,
    )
    
    # Request device code
    device_code, uri, user_code = client._request_device_code(
        client.oidc_domain, client.oidc_client_id, client.oidc_scope, client.oidc_audience
    )
    
    print(f"Visit this URL to authorize: {uri}")
    print(f"User code: {user_code}")
    print("Waiting for authorization...")
    
    # Poll for token
    stop_at = datetime.datetime.now() + datetime.timedelta(seconds=120)
    while datetime.datetime.now() < stop_at:
        token, expiration = client.get_token(device_code)
        if token is not None:
            print("Authorization successful!")
            return TokenData(
                access_token=token,
                refresh_token=client.get_cached_refresh_token(),
                access_token_expiration=expiration,
            )
        time.sleep(2.0)
    
    raise FulcraAuthError("Authorization timed out. Please try again.")


def is_token_valid(expiration: Optional[datetime.datetime]) -> bool:
    """Check if token is still valid (not expired with 60s buffer)"""
    if not expiration:
        return False
    now = datetime.datetime.now(datetime.timezone.utc)
    if expiration.tzinfo is None:
        expiration = expiration.replace(tzinfo=datetime.timezone.utc)
    return expiration > now + datetime.timedelta(seconds=60)


def parse_iso_datetime(value: Optional[str]) -> Optional[datetime.datetime]:
    """Parse ISO 8601 datetime string, handling Z suffix"""
    match value:
        case None | "":
            return None
        case str() as text:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            try:
                dt = datetime.datetime.fromisoformat(text)
            except ValueError:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt
        case _:
            return None


def isoformat_z(dt: datetime.datetime) -> str:
    """Convert datetime to ISO 8601 string with Z suffix"""
    return dt.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")