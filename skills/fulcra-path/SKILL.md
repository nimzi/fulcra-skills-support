---
name: fulcra-path
description: Generate a static map showing the user's movement path and stay locations for a given day. Requires Fulcra authentication — direct the user to /fulcra-auth if not authenticated.
metadata.openclaw:
  emoji: "🗺️"
  requires.bins: ["python3"]
---

# Fulcra Daily Path Map

Generate a static PNG map of the user's GPS movement trajectory with stay locations
overlaid as markers for a given date.

## Step 0: Check authentication

Run:
```
python3 -m fulcra_skills_support.cli check-token
```

If it exits with an error, tell the user they need to authenticate first and ask them
to run `/fulcra-auth`. Do not proceed until authenticated.

## Step 1: Get the date

Ask the user for the date if not already provided. Format: `YYYY-MM-DD`.
Use today's date if the user says "today".

## Step 2: Generate path map

Run:
```
python3 -m fulcra_skills_support.cli daily-path <date>
```

This fetches location data, detects stays, and generates the map in one step.
Tell the user the output file path (e.g. `/tmp/fulcra_path_2026-05-09.png`) and
how many location points and stays were used.
