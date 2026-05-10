#!/usr/bin/env python3
"""Check whether a valid Fulcra token exists."""
from pathlib import Path
from fulcra_skills_support.auth import TokenStore, is_token_valid

TOKEN_PATH = Path.home() / ".config" / "fulcra" / "token.json"

token = TokenStore(TOKEN_PATH).load()
if token and is_token_valid(token.access_token_expiration):
    print("Token valid")
else:
    print("No valid token found")
    raise SystemExit(1)
