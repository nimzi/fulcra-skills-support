#!/usr/bin/env python3
"""
Example of how the new Stay Detection skill would be implemented using the library

This shows how the existing complex stay detection skill can be simplified
to just use the library's stay detection capabilities.
"""

import os
import sys
from pathlib import Path
from fulcra_skills_support import FulcraVisualizer

def main():
    print("Stay Detection Skill")
    print("=" * 40)
    
    # Check if location data file exists
    location_file = "/tmp/fulcra_location.parquet"
    if not os.path.exists(location_file):
        print(f"Error: {location_file} not found")
        print("Please run the Fulcra skill first to fetch location data")
        sys.exit(1)
    
    print(f"Loading location data from: {location_file}")
    
    # Create visualizer (no auth needed for file-based processing)
    viz = FulcraVisualizer()
    
    try:
        # Load location data
        location_data = viz.load_location_from_file(location_file)
        print(f"Loaded {len(location_data)} location records")
        
        if location_data.empty:
            print("No location data to process")
            sys.exit(0)
        
    except Exception as e:
        print(f"Error loading location data: {e}")
        sys.exit(1)
    
    # Show default parameters and ask user
    print("\nStay Detection Parameters:")
    print("=" * 30)
    
    default_params = {
        "R_SOFT": 50,      # Spatial threshold (meters)
        "V0": 0.5,         # Velocity threshold (m/s) 
        "TAU_ENTER": 0.6,  # Score threshold to enter stay
        "TAU_EXIT": 0.35,  # Score threshold to exit stay
        "T_MIN": 120,      # Minimum stay duration (seconds)
        "R_MERGE": 75,     # Merge distance for nearby stays (meters)
        "T_MERGE": 300     # Merge time gap for consecutive stays (seconds)
    }
    
    print("Default parameters:")
    for param, value in default_params.items():
        unit = "m" if param.startswith("R_") else ("s" if param.startswith("T_") else "")
        print(f"  {param}: {value} {unit}")
    
    use_defaults = input("\nUse default parameters? [Y/n]: ").strip().lower()
    
    if use_defaults in ("", "y", "yes"):
        detector_params = {}
        print("Using default parameters")
    else:
        print("\nCustomizing parameters:")
        detector_params = {}
        for param, default_value in default_params.items():
            while True:
                try:
                    response = input(f"  {param} (default {default_value}): ").strip()
                    if not response:
                        break  # Use default
                    value = float(response)
                    detector_params[param] = value
                    break
                except ValueError:
                    print("    Please enter a valid number")
        
        if detector_params:
            print("Custom parameters:")
            for param, value in detector_params.items():
                print(f"  {param}: {value}")
    
    # Run stay detection
    print(f"\nRunning stay detection...")
    
    try:
        stays = viz.detect_stays_from_file(location_file, **detector_params)
        print(f"Detected {len(stays)} stays")
        
        if not stays:
            print("No stays detected")
            sys.exit(0)
        
    except Exception as e:
        print(f"Error during stay detection: {e}")
        sys.exit(1)
    
    # Save stays for other skills
    stays_file = "/tmp/fulcra_stays.parquet"
    try:
        viz.save_stays_data(stays, stays_file)
        print(f"✓ Saved stays to: {stays_file}")
    except Exception as e:
        print(f"Error saving stays: {e}")
    
    # Display results
    print(f"\nStay Detection Results:")
    print("=" * 50)
    
    def format_duration(seconds):
        minutes = int(seconds // 60)
        if minutes < 60:
            return f"{minutes} min"
        hours = minutes // 60
        remaining_min = minutes % 60
        return f"{hours}h {remaining_min}m" if remaining_min else f"{hours}h"
    
    def format_time(iso_string):
        from datetime import datetime
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime("%H:%M")
    
    # Sort by entry time
    stays_sorted = sorted(stays, key=lambda s: s['entry_time'])
    
    print(f"{'#':<3} {'Entry':<8} {'Exit':<8} {'Duration':<10} {'Lat':<10} {'Lon':<11} {'Points':<6}")
    print("-" * 60)
    
    for i, stay in enumerate(stays_sorted, 1):
        entry_time = format_time(stay['entry_time'])
        exit_time = format_time(stay['exit_time'])
        duration = format_duration(stay['duration_seconds'])
        lat = f"{stay['centroid_lat']:.5f}"
        lon = f"{stay['centroid_lon']:.5f}"
        points = stay['n_points']
        
        print(f"{i:<3} {entry_time:<8} {exit_time:<8} {duration:<10} {lat:<10} {lon:<11} {points:<6}")
    
    # Summary statistics
    total_duration = sum(s['duration_seconds'] for s in stays)
    avg_duration = total_duration / len(stays)
    longest_stay = max(stays, key=lambda s: s['duration_seconds'])
    
    print(f"\nSummary:")
    print(f"  Total stays: {len(stays)}")
    print(f"  Total stay time: {format_duration(total_duration)}")
    print(f"  Average stay duration: {format_duration(avg_duration)}")
    print(f"  Longest stay: {format_duration(longest_stay['duration_seconds'])}")
    
    print(f"\nData saved to {stays_file} for use by other skills")

if __name__ == "__main__":
    main()