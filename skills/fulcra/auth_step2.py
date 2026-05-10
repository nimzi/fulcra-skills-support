#!/usr/bin/env python3
"""Step 2: Complete Fulcra OAuth2 device authorization flow.

Polls for the token (up to 120 seconds) and saves it to the standard token path.
Only run this after the user has authorized at the URL shown by auth_step1.py.
"""
import sys
from pathlib import Path
from fulcra_skills_support import complete_device_auth_flow, FulcraAuthError
from fulcra_skills_support.auth import TokenStore

TOKEN_PATH = Path.home() / ".config" / "fulcra" / "token.json"

try:
    token_data = complete_device_auth_flow()
    TokenStore(TOKEN_PATH).save(token_data)
    print(f"Authorization successful! Token saved to {TOKEN_PATH}")
except FulcraAuthError as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
