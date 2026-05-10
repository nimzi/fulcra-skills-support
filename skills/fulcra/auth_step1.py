#!/usr/bin/env python3
"""Step 1: Start Fulcra OAuth2 device authorization flow.

Prints the authorization URL and user code, then exits immediately.
Run auth_step2.py after the user has authorized in their browser.
"""
import sys
from fulcra_skills_support import start_device_auth_flow, FulcraAuthError

try:
    result = start_device_auth_flow()
    print(f"AUTHORIZATION URL: {result['verification_uri']}")
    print(f"User code: {result['user_code']}")
except FulcraAuthError as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
