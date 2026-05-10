#!/usr/bin/env python3
"""
Basic usage example for fulcra-skills-support library

This script demonstrates the core functionality of the library:
- Authentication 
- Data fetching
- Stay detection
- Static visualization
"""

import datetime
from fulcra_skills_support import FulcraVisualizer

def main():
    print("Fulcra Skills Support - Basic Usage Example")
    print("=" * 50)
    
    # Method 1: Load from existing token file
    try:
        viz = FulcraVisualizer.from_token_file("~/.config/fulcra/token.json")
        print("✓ Loaded credentials from token file")
    except Exception as e:
        print(f"✗ Could not load token file: {e}")
        print("Run device authorization instead...")
        
        # Method 2: Device authorization flow
        viz = FulcraVisualizer.from_device_auth()
        print("✓ Device authorization completed")
    
    # Get user information
    user_info = viz.get_user_info()
    timezone = user_info.get("preferences", {}).get("timezone", "UTC")
    print(f"✓ User timezone: {timezone}")
    
    # Use yesterday's date for demonstration
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")
    print(f"Analyzing data for: {date_str}")
    
    # Fetch daily location data
    print("\n1. Fetching location data...")
    try:
        locations = viz.fetch_daily_data(date_str, timezone)
        print(f"   Found {len(locations)} location records")
        
        if not locations.empty:
            print(f"   Time range: {locations['timestamp'].min()} to {locations['timestamp'].max()}")
            
            # Show basic statistics
            if 'speed' in locations.columns:
                speed_data = locations['speed'].dropna()
                if not speed_data.empty:
                    print(f"   Speed range: {speed_data.min():.1f} - {speed_data.max():.1f} m/s")
        
    except Exception as e:
        print(f"   ✗ Error fetching data: {e}")
        return
    
    if locations.empty:
        print("   No location data available for this date")
        return
    
    # Detect stays
    print("\n2. Detecting stays...")
    try:
        stays = viz.detect_stays(date_str, timezone)
        print(f"   Found {len(stays)} stays")
        
        if stays:
            total_duration = sum(s['duration_seconds'] for s in stays)
            print(f"   Total stay time: {total_duration // 60:.0f} minutes")
            
            # Show top 3 longest stays
            stays_by_duration = sorted(stays, key=lambda s: s['duration_seconds'], reverse=True)
            print("   Longest stays:")
            for i, stay in enumerate(stays_by_duration[:3]):
                duration_min = stay['duration_seconds'] // 60
                print(f"     {i+1}. {duration_min:.0f} min at ({stay['centroid_lat']:.4f}, {stay['centroid_lon']:.4f})")
                
    except Exception as e:
        print(f"   ✗ Error detecting stays: {e}")
        stays = []
    
    # Generate static visualizations
    print("\n3. Generating static maps...")
    
    try:
        # Basic trajectory map
        print("   Creating daily path map...")
        path_fig = viz.daily_path_static(date_str, timezone, title=f"Daily Path - {date_str}")
        viz.save_static_map(path_fig, f"daily_path_{date_str}.png")
        print(f"   ✓ Saved: daily_path_{date_str}.png")
        
        # Speed-colored map if speed data available
        if 'speed' in locations.columns and not locations['speed'].isna().all():
            print("   Creating speed-colored path map...")
            speed_fig = viz.path_by_speed_static(date_str, timezone, title=f"Path by Speed - {date_str}")
            viz.save_static_map(speed_fig, f"path_by_speed_{date_str}.png")
            print(f"   ✓ Saved: path_by_speed_{date_str}.png")
        
        # Stays heatmap if stays found
        if stays:
            print("   Creating stays heatmap...")
            stays_fig = viz.stays_heatmap_static(date_str, timezone, title=f"Stay Locations - {date_str}")
            viz.save_static_map(stays_fig, f"stays_heatmap_{date_str}.png")
            print(f"   ✓ Saved: stays_heatmap_{date_str}.png")
            
    except Exception as e:
        print(f"   ✗ Error generating maps: {e}")
    
    # Save data for use by other skills
    print("\n4. Saving data for skill interoperability...")
    try:
        viz.save_location_data(locations, "/tmp/fulcra_location.parquet")
        print("   ✓ Saved location data: /tmp/fulcra_location.parquet")
        
        if stays:
            viz.save_stays_data(stays, "/tmp/fulcra_stays.parquet")
            print("   ✓ Saved stays data: /tmp/fulcra_stays.parquet")
            
    except Exception as e:
        print(f"   ✗ Error saving data: {e}")
    
    print("\n" + "=" * 50)
    print("Basic usage example completed!")
    print("\nGenerated files:")
    print(f"  - daily_path_{date_str}.png")
    if 'speed' in locations.columns and not locations['speed'].isna().all():
        print(f"  - path_by_speed_{date_str}.png")
    if stays:
        print(f"  - stays_heatmap_{date_str}.png")
    print("  - /tmp/fulcra_location.parquet") 
    if stays:
        print("  - /tmp/fulcra_stays.parquet")

if __name__ == "__main__":
    main()