"""
Command-line entry points for Fulcra authentication and data operations.

Callable as console scripts or via:
    python3 -m fulcra_skills_support.cli <command> [date]

Commands requiring a date accept YYYY-MM-DD format.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from .auth import (
    DEFAULT_TOKEN_PATH,
    FulcraAuthError,
    TokenStore,
    complete_device_auth_flow,
    is_token_valid,
    start_device_auth_flow,
)

LOCATION_FILE = Path("/tmp/fulcra_location.parquet")
STAYS_FILE = Path("/tmp/fulcra_stays.parquet")
PATH_MAP_DIR = Path("/tmp")


def _require_date(command: str) -> str:
    if len(sys.argv) < 3:
        print(f"Usage: python3 -m fulcra_skills_support.cli {command} <YYYY-MM-DD>", file=sys.stderr)
        sys.exit(1)
    return sys.argv[2]


def _get_visualizer():
    from .core import FulcraVisualizer
    return FulcraVisualizer.from_token_file(DEFAULT_TOKEN_PATH)


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


def cmd_fetch_data() -> None:
    """Fetch location data for a date and save to /tmp/fulcra_location.parquet."""
    date = _require_date("fetch-data")
    try:
        viz = _get_visualizer()
        print(f"Fetching location data for {date}...")
        data = viz.fetch_daily_data(date)
        if data.empty:
            print("No location data found for this date.")
            sys.exit(0)
        viz.save_location_data(data, LOCATION_FILE)
        time_range = f"{data['timestamp'].min()} to {data['timestamp'].max()}"
        print(f"Fetched {len(data)} records ({time_range})")
        print(f"Saved to {LOCATION_FILE}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_detect_stays() -> None:
    """Detect stays for a date and print a summary."""
    date = _require_date("detect-stays")
    try:
        viz = _get_visualizer()
        print(f"Detecting stays for {date}...")
        stays = viz.detect_stays(date)
        if not stays:
            print("No stays detected.")
            sys.exit(0)
        viz.save_stays_data(stays, STAYS_FILE)

        def _fmt_dur(s: float) -> str:
            m = int(s) // 60
            return f"{m // 60}h {m % 60}m" if m >= 60 else f"{m}m"

        def _fmt_time(iso: str) -> str:
            from datetime import datetime
            return datetime.fromisoformat(iso).strftime("%H:%M")

        stays_sorted = sorted(stays, key=lambda s: s["entry_time"])
        print(f"\n{'#':<3} {'Entry':<7} {'Exit':<7} {'Duration':<10} {'Lat':<10} {'Lon'}")
        print("-" * 52)
        for i, s in enumerate(stays_sorted, 1):
            print(
                f"{i:<3} {_fmt_time(s['entry_time']):<7} {_fmt_time(s['exit_time']):<7} "
                f"{_fmt_dur(s['duration_seconds']):<10} "
                f"{s['centroid_lat']:.4f}   {s['centroid_lon']:.4f}"
            )
        total = sum(s["duration_seconds"] for s in stays)
        print(f"\n{len(stays)} stays, {_fmt_dur(total)} total. Saved to {STAYS_FILE}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_daily_path() -> None:
    """Generate a static daily path map with stays overlaid, saved to /tmp/fulcra_path_<date>.png."""
    date = _require_date("daily-path")
    out = PATH_MAP_DIR / f"fulcra_path_{date}.png"
    try:
        from .visualization.interactive import InteractiveMapGenerator
        from .utils.geo import reverse_geocode
        viz = _get_visualizer()
        print(f"Fetching data and detecting stays for {date}...")
        locations = viz.fetch_daily_data(date)
        if locations.empty:
            print("No location data found for this date.")
            sys.exit(0)
        stays = viz.detect_stays(date)
        stays_sorted = sorted(stays, key=lambda s: s["entry_time"])

        # Reverse geocode each stay (Nominatim: 1 req/s max)
        if stays_sorted:
            print("Reverse geocoding stay locations...")
        place_names = []
        for stay in stays_sorted:
            place_names.append(reverse_geocode(stay["centroid_lat"], stay["centroid_lon"]))
            time.sleep(1.1)

        print("Rendering map...")
        gen = InteractiveMapGenerator()
        m = gen.daily_path_with_stays(locations, stays_sorted, title=f"Daily path — {date}")
        gen.render_to_png(m, out)
        print(f"Saved to {out} ({len(locations)} points, {len(stays_sorted)} stays)\n")

        # Print stay legend
        if stays_sorted:
            def _fmt(iso: str) -> str:
                from datetime import datetime
                return datetime.fromisoformat(iso).strftime("%H:%M")

            def _dur(s: float) -> str:
                m = int(s) // 60
                return f"{m // 60}h {m % 60}m" if m >= 60 else f"{m}m"

            col_w = max(len(n) for n in place_names) + 2
            header = f"{'#':<3}  {'Location':<{col_w}}  {'Lat':>9}  {'Lon':>10}  {'Entry':>5}  {'Exit':>5}  {'Duration'}"
            print(header)
            print("-" * len(header))
            for i, (stay, name) in enumerate(zip(stays_sorted, place_names), 1):
                print(
                    f"{i:<3}  {name:<{col_w}}  "
                    f"{stay['centroid_lat']:>9.4f}  {stay['centroid_lon']:>10.4f}  "
                    f"{_fmt(stay['entry_time']):>5}  {_fmt(stay['exit_time']):>5}  "
                    f"{_dur(stay['duration_seconds'])}"
                )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


_COMMANDS: dict[str, tuple] = {
    "check-token":   (cmd_check_token,  False),
    "auth-step1":    (cmd_auth_step1,   False),
    "auth-step2":    (cmd_auth_step2,   False),
    "fetch-data":    (cmd_fetch_data,   True),
    "detect-stays":  (cmd_detect_stays, True),
    "daily-path":    (cmd_daily_path,   True),
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) >= 2 else None
    if cmd not in _COMMANDS:
        print("Usage: python3 -m fulcra_skills_support.cli <command> [date]")
        print("Commands:")
        for name, (_, needs_date) in _COMMANDS.items():
            print(f"  {name}" + (" <YYYY-MM-DD>" if needs_date else ""))
        sys.exit(1)
    _COMMANDS[cmd][0]()
