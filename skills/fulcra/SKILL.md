---
name: fulcra
description: Authenticate with the Fulcra API and prepare it for use by other Fulcra skills. Handles OAuth2 device authorization in two separate steps.
metadata.openclaw:
  emoji: "📍"
  requires.bins: ["python3"]
---

# Fulcra Skill

Use this skill to authenticate with the Fulcra API. The token is saved to
`~/.config/fulcra/token.json` and used by all other Fulcra skills.

## Step 0: Check for existing token

Run:
```
python3 -m fulcra_skills_support.cli check-token
```

If it prints "Token valid", authentication is already complete — skip to Step 3.

## Step 1: Start device authorization

Run:
```
python3 -m fulcra_skills_support.cli auth-step1
```

Read the output carefully. Find the **AUTHORIZATION URL** line and show it to the
user verbatim. Also show the user code. Tell the user to:
1. Visit that URL in their browser
2. Enter the user code when prompted
3. Complete the authorization

**Critical**: Do not run Step 2 yet. Ask the user to confirm they have authorized
before continuing.

## Step 2: Complete authorization

Only after the user confirms they have authorized in their browser, run:
```
python3 -m fulcra_skills_support.cli auth-step2
```

This polls the authorization server for the token (up to 120 seconds).

- If it prints "Authorization successful!", report this to the user and proceed to Step 3.
- If it fails with a timeout error, tell the user and offer to restart from Step 1.

## Step 3: Done

Authentication is complete. The token is saved and ready for other Fulcra skills
(location data, stay detection, visualization, etc.).
