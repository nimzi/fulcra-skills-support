"""
Command-line entry points for Fulcra authentication.

Callable as console scripts (fulcra-check-token, fulcra-auth-step1,
fulcra-auth-step2) or via: python3 -m fulcra_skills_support.cli <command>
"""

from __future__ import annotations

import sys

from .auth import (
    DEFAULT_TOKEN_PATH,
    FulcraAuthError,
    TokenStore,
    complete_device_auth_flow,
    is_token_valid,
    start_device_auth_flow,
)


def cmd_check_token() -> None:
    """Exit 0 and print 'Token valid' if a valid token exists, else exit 1."""
    token = TokenStore(DEFAULT_TOKEN_PATH).load()
    if token and is_token_valid(token.access_token_expiration):
        print("Token valid")
    else:
        print("No valid token found")
        sys.exit(1)


def cmd_auth_step1() -> None:
    """Start device authorization flow. Prints URL and user code, then exits."""
    try:
        result = start_device_auth_flow()
        print(f"AUTHORIZATION URL: {result['verification_uri']}")
        print(f"User code: {result['user_code']}")
    except FulcraAuthError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_auth_step2() -> None:
    """Poll for token and save to the default token path."""
    try:
        token_data = complete_device_auth_flow()
        TokenStore(DEFAULT_TOKEN_PATH).save(token_data)
        print(f"Authorization successful! Token saved to {DEFAULT_TOKEN_PATH}")
    except FulcraAuthError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


_COMMANDS = {
    "check-token": cmd_check_token,
    "auth-step1": cmd_auth_step1,
    "auth-step2": cmd_auth_step2,
}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in _COMMANDS:
        print(f"Usage: python3 -m fulcra_skills_support.cli <command>")
        print(f"Commands: {', '.join(_COMMANDS)}")
        sys.exit(1)
    _COMMANDS[sys.argv[1]]()
