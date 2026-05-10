#!/usr/bin/env python3
"""
Example of how agents would integrate with the fulcra-skills-support library

This demonstrates various use cases for agents:
- Simple one-liner visualizations
- Batch processing multiple dates  
- Custom analysis workflows
- Error handling patterns
"""

import datetime
from pathlib import Path
from fulcra_skills_support import FulcraVisualizer

def example_simple_agent_usage():
    """Simplest possible agent integration - one map for yesterday"""
    print("=== Simple Agent Usage ===")
    
    try:
        # Agent gets user's daily path in 3 lines
        viz = FulcraVisualizer.from_token_file("~/.config/fulcra/token.json")
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Generate and save map
        fig = viz.daily_path_static(yesterday, title=f"Your path on {yesterday}")
        viz.save_static_map(fig, "user_daily_path.png")
        
        print(f"✓ Generated map: user_daily_path.png")
        
    except Exception as e:
        print(f"✗ Agent task failed: {e}")

def example_agent_batch_processing():
    """Agent processing multiple days at once"""
    print("\n=== Batch Processing Agent ===")
    
    try:
        viz = FulcraVisualizer.from_token_file("~/.config/fulcra/token.json")
        
        # Process last 7 days
        today = datetime.date.today()
        dates = [(today - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 8)]
        
        print("Processing last 7 days:")
        results = []
        
        for date in dates:
            try:
                # Get basic stats for each day
                locations = viz.fetch_daily_data(date)
                stays = viz.detect_stays(date) if not locations.empty else []
                
                stats = {
                    'date': date,
                    'locations': len(locations),
                    'stays': len(stays),
                    'total_stay_time': sum(s['duration_seconds'] for s in stays) // 60  # minutes
                }
                results.append(stats)
                print(f"  {date}: {stats['locations']} locations, {stats['stays']} stays, {stats['total_stay_time']} min")
                
            except Exception as e:
                print(f"  {date}: Error - {e}")
                results.append({'date': date, 'error': str(e)})
        
        # Summary report
        valid_results = [r for r in results if 'error' not in r]
        if valid_results:
            avg_locations = sum(r['locations'] for r in valid_results) / len(valid_results)
            avg_stays = sum(r['stays'] for r in valid_results) / len(valid_results)
            total_stay_time = sum(r['total_stay_time'] for r in valid_results)
            
            print(f"\n7-day summary:")
            print(f"  Average locations per day: {avg_locations:.0f}")
            print(f"  Average stays per day: {avg_stays:.1f}")
            print(f"  Total stay time: {total_stay_time} minutes ({total_stay_time//60}h {total_stay_time%60}m)")
        
    except Exception as e:
        print(f"✗ Batch processing failed: {e}")

def example_agent_custom_analysis():
    """Agent doing custom analysis with the library's building blocks"""
    print("\n=== Custom Analysis Agent ===")
    
    try:
        viz = FulcraVisualizer.from_token_file("~/.config/fulcra/token.json")
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        
        print(f"Analyzing movement patterns for {yesterday}:")
        
        # Get location data
        locations = viz.fetch_daily_data(yesterday)
        if locations.empty:
            print("  No data available")
            return
        
        # Custom analysis: time spent moving vs stationary
        if 'calculated_speed_mps' in locations.columns:
            speed_data = locations['calculated_speed_mps'].dropna()
            if not speed_data.empty:
                # Define movement thresholds
                stationary_threshold = 0.5  # m/s
                walking_threshold = 2.0     # m/s
                
                stationary_pct = (speed_data <= stationary_threshold).mean() * 100
                walking_pct = ((speed_data > stationary_threshold) & 
                             (speed_data <= walking_threshold)).mean() * 100
                driving_pct = (speed_data > walking_threshold).mean() * 100
                
                print(f"  Movement breakdown:")
                print(f"    Stationary: {stationary_pct:.1f}%")
                print(f"    Walking: {walking_pct:.1f}%")
                print(f"    Driving/Fast: {driving_pct:.1f}%")
        
        # Stay analysis with custom parameters
        stays = viz.detect_stays(yesterday, R_SOFT=30, T_MIN=300)  # Stricter parameters
        if stays:
            # Find home/work candidates (longest stays)
            stays_by_duration = sorted(stays, key=lambda s: s['duration_seconds'], reverse=True)
            
            print(f"  Found {len(stays)} significant stays (5+ min):")
            for i, stay in enumerate(stays_by_duration[:3]):
                duration_hours = stay['duration_seconds'] / 3600
                print(f"    {i+1}. {duration_hours:.1f}h at ({stay['centroid_lat']:.4f}, {stay['centroid_lon']:.4f})")
        
        # Generate comprehensive visualization
        print("  Generating comprehensive visualization...")
        
        # Create multi-panel figure (if we had the capability)
        # For now, create separate maps
        path_fig = viz.daily_path_static(yesterday, title="Daily Movement Path")
        viz.save_static_map(path_fig, f"analysis_{yesterday}_path.png")
        
        if 'speed' in locations.columns or 'calculated_speed_mps' in locations.columns:
            speed_fig = viz.path_by_speed_static(yesterday, title="Movement Speed Analysis")  
            viz.save_static_map(speed_fig, f"analysis_{yesterday}_speed.png")
        
        if stays:
            stays_fig = viz.stays_heatmap_static(yesterday, title="Significant Stay Locations")
            viz.save_static_map(stays_fig, f"analysis_{yesterday}_stays.png")
        
        print(f"  ✓ Analysis complete - generated visualization files")
        
    except Exception as e:
        print(f"✗ Custom analysis failed: {e}")

def example_agent_error_handling():
    """Agent with robust error handling patterns"""
    print("\n=== Robust Agent Error Handling ===")
    
    # Try multiple authentication methods
    viz = None
    
    # Method 1: Standard token file
    try:
        viz = FulcraVisualizer.from_token_file("~/.config/fulcra/token.json")
        print("✓ Authenticated via standard token file")
    except Exception as e:
        print(f"Standard auth failed: {e}")
    
    # Method 2: Alternative token location
    if viz is None:
        try:
            viz = FulcraVisualizer.from_token_file(".fulcra_token.json")  # Local file
            print("✓ Authenticated via local token file")
        except Exception as e:
            print(f"Local auth failed: {e}")
    
    # Method 3: Environment variables (hypothetical)
    if viz is None:
        try:
            import os
            access_token = os.environ.get('FULCRA_ACCESS_TOKEN')
            if access_token:
                viz = FulcraVisualizer.from_credentials(access_token)
                print("✓ Authenticated via environment variables")
        except Exception as e:
            print(f"Environment auth failed: {e}")
    
    if viz is None:
        print("✗ All authentication methods failed")
        return
    
    # Robust data processing with fallbacks
    date = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    try:
        # Try to get data
        locations = viz.fetch_daily_data(date)
        
        if locations.empty:
            print(f"No location data for {date} - trying previous day")
            date = (datetime.date.today() - datetime.timedelta(days=2)).strftime("%Y-%m-%d")
            locations = viz.fetch_daily_data(date)
        
        if locations.empty:
            print("No recent location data available")
            return
        
        print(f"✓ Using data from {date} ({len(locations)} records)")
        
        # Try visualization with fallbacks
        try:
            # Try speed-colored map first
            fig = viz.path_by_speed_static(date)
            viz.save_static_map(fig, "robust_agent_map.png")
            print("✓ Generated speed-colored map")
        except Exception as e:
            print(f"Speed map failed: {e}, trying basic path map...")
            try:
                fig = viz.daily_path_static(date)
                viz.save_static_map(fig, "robust_agent_map.png")
                print("✓ Generated basic path map")
            except Exception as e2:
                print(f"Basic map also failed: {e2}")
        
    except Exception as e:
        print(f"✗ Robust agent ultimately failed: {e}")

def main():
    """Run all agent integration examples"""
    print("Fulcra Skills Support - Agent Integration Examples")
    print("=" * 55)
    
    # Check if we can find a token file
    token_paths = [
        Path.home() / ".config" / "fulcra" / "token.json",
        Path(".fulcra_token.json"),
        Path("python/.fulcra_token.json")  # From parent project
    ]
    
    token_found = any(p.exists() for p in token_paths)
    
    if not token_found:
        print("Note: No Fulcra token file found.")
        print("These examples assume you have authenticated with Fulcra.")
        print("Run the basic_usage.py example first to authenticate.\n")
    
    # Run examples
    example_simple_agent_usage()
    example_agent_batch_processing()  
    example_agent_custom_analysis()
    example_agent_error_handling()
    
    print("\n" + "=" * 55)
    print("Agent integration examples completed!")

if __name__ == "__main__":
    main()