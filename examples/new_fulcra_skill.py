#!/usr/bin/env python3
"""
Example of how the new Fulcra skill would be implemented using the library

This shows how the existing complex Fulcra skill can be simplified to just
a thin wrapper around the fulcra-skills-support library.
"""

import sys
from pathlib import Path
from fulcra_skills_support import FulcraVisualizer

def main():
    print("Fulcra Data Fetcher")
    print("=" * 40)
    
    # Get date from user
    if len(sys.argv) > 1:
        date = sys.argv[1]
    else:
        date = input("Enter date (YYYY-MM-DD): ").strip()
    
    if not date:
        print("Error: Date is required")
        sys.exit(1)
    
    print(f"Fetching data for: {date}")
    
    # Try to use existing token, fall back to device auth
    token_path = Path.home() / ".config" / "fulcra" / "token.json"
    
    try:
        if token_path.exists():
            viz = FulcraVisualizer.from_token_file(token_path)
            print("✓ Using existing token")
        else:
            print("No existing token found. Starting device authorization...")
            viz = FulcraVisualizer.from_device_auth(token_path=token_path)
    except Exception as e:
        print(f"Authentication failed: {e}")
        sys.exit(1)
    
    # Get user timezone
    try:
        user_info = viz.get_user_info()
        timezone = user_info.get("preferences", {}).get("timezone", "UTC")
        print(f"User timezone: {timezone}")
    except Exception as e:
        print(f"Could not get user info: {e}")
        timezone = "UTC"
    
    # Fetch location data
    try:
        print("Fetching location data...")
        daily_data = viz.fetch_daily_data(date, timezone)
        
        if daily_data.empty:
            print("No location data found for this date.")
            sys.exit(0)
        
        print(f"Found {len(daily_data)} location records")
        
        # Save to standard location for other skills
        output_path = "/tmp/fulcra_location.parquet"
        viz.save_location_data(daily_data, output_path)
        
        print(f"✓ Saved to: {output_path}")
        print(f"  Columns: {list(daily_data.columns)}")
        print(f"  Time range: {daily_data['timestamp'].min()} to {daily_data['timestamp'].max()}")
        
        # Show basic statistics
        if 'speed' in daily_data.columns:
            speed_data = daily_data['speed'].dropna()
            if not speed_data.empty:
                print(f"  Speed range: {speed_data.min():.1f} - {speed_data.max():.1f} m/s")
        
        print("\nData is ready for use by other skills (stay detection, visualization, etc.)")
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()