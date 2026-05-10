---
name: fulcra-stays
description: Detect where the user stopped and for how long on a given day. Fetches location data and runs stay detection. Requires Fulcra authentication — direct the user to /fulcra-auth if not authenticated.
metadata.openclaw:
  emoji: "📍"
  requires.bins: ["python3"]
---

# Fulcra Stay Detection

## Requirements

This skill requires the `fulcra-skills-support` library:
```
pip install git+https://github.com/nimzi/fulcra-skills-support.git
```

Detect stays (locations where the user paused for a significant time) for a given date.

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

## Step 2: Fetch location data

Run:
```
python3 -m fulcra_skills_support.cli fetch-data <date>
```

Report the record count to the user. If no data is found, tell the user and stop.

## Step 3: Detect stays

Run:
```
python3 -m fulcra_skills_support.cli detect-stays <date>
```

Show the full stay table to the user, including entry/exit times, duration, and coordinates.
Summarize the total number of stays and total time spent stationary.
