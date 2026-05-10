---
name: fulcra-auth
description: Authenticate with the Fulcra API using OAuth2 device authorization. Run this before any other Fulcra skill. Skips automatically if a valid token already exists.
metadata.openclaw:
  emoji: "🔑"
  requires.bins: ["python3"]
---

# Fulcra Authentication

## Requirements

This skill requires the `fulcra-skills-support` library:
```
pip install git+https://github.com/nimzi/fulcra-skills-support.git
```

Authenticate the user with the Fulcra API. The token is saved to
`~/.config/fulcra/token.json` and reused by all other Fulcra skills.

## Step 0: Check for existing token

Run:
```
python3 -m fulcra_skills_support.cli check-token
```

If it prints "Token valid", tell the user they are already authenticated and stop here.

## Step 1: Start device authorization

Run:
```
python3 -m fulcra_skills_support.cli auth-step1
```

Show the **AUTHORIZATION URL** and user code to the user verbatim. Tell them to:
1. Visit that URL in their browser
2. Enter the user code when prompted
3. Complete the authorization

**Critical**: Do not run Step 2 until the user confirms they have authorized.

## Step 2: Complete authorization

Only after the user confirms, run:
```
python3 -m fulcra_skills_support.cli auth-step2
```

This polls for the token (up to 120 seconds).

- On success: report "Authorization successful!" to the user.
- On timeout: tell the user and offer to restart from Step 1.
