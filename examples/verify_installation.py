#!/usr/bin/env python3
"""
Installation verification script for fulcra-skills-support

This script verifies that the library is correctly installed and can be imported.
It checks all major components without requiring authentication.
"""

import sys
import traceback
from pathlib import Path

def check_import(module_name, description):
    """Check if a module can be imported"""
    try:
        exec(f"import {module_name}")
        print(f"✓ {description}")
        return True
    except ImportError as e:
        print(f"✗ {description}: {e}")
        return False
    except Exception as e:
        print(f"✗ {description}: Unexpected error - {e}")
        return False

def check_basic_functionality():
    """Check basic library functionality without authentication"""
    print("\nTesting basic functionality...")
    
    try:
        # Test core imports
        from fulcra_skills_support import FulcraVisualizer, StayDetector, Observation, Stay
        print("✓ Core classes import successfully")
        
        # Test stay detection with synthetic data
        print("Testing stay detection with synthetic data...")
        detector = StayDetector()
        
        # Create simple test observations
        observations = [
            Observation(t=1000.0, lat=37.7749, lon=-122.4194, speed=0.1),
            Observation(t=1060.0, lat=37.7750, lon=-122.4195, speed=0.1),
            Observation(t=1120.0, lat=37.7749, lon=-122.4194, speed=0.1),
        ]
        
        stays, debug_df = detector.detect_stays(observations)
        print(f"✓ Stay detection works ({len(stays)} stays detected)")
        print(f"✓ Debug DataFrame has {len(debug_df)} rows")
        
        # Test utilities
        from fulcra_skills_support.utils.geo import haversine_distance, calculate_bearing
        from fulcra_skills_support.utils.time import format_duration, parse_date_string
        
        # Test geo utilities
        dist = haversine_distance(37.7749, -122.4194, 37.7750, -122.4195)
        bearing = calculate_bearing(37.7749, -122.4194, 37.7750, -122.4195)
        print(f"✓ Geo utilities work (distance: {dist:.1f}m, bearing: {bearing:.1f}°)")
        
        # Test time utilities
        duration_str = format_duration(3665)  # 1h 1m 5s
        date_obj = parse_date_string("2023-05-15")
        print(f"✓ Time utilities work (duration: {duration_str}, date: {date_obj})")
        
        # Test visualization classes (without generating actual plots)
        from fulcra_skills_support.visualization.styles import ColorSchemes, MapStyles
        colors = ColorSchemes.speed_gradient()
        map_style = MapStyles.street_map()
        print(f"✓ Visualization styles work ({len(colors)} speed colors)")
        
        return True
        
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        traceback.print_exc()
        return False

def check_dependencies():
    """Check that all required dependencies are available"""
    print("\nChecking dependencies...")
    
    required_deps = [
        ("pandas", "Data processing"),
        ("numpy", "Numerical operations"),
        ("plotly", "Static visualizations"),
        ("folium", "Interactive maps"),
        ("pyarrow", "Parquet file support"),
        ("pytz", "Timezone handling")
    ]
    
    optional_deps = [
        ("fulcra_api", "Fulcra API client (optional for testing)")
    ]
    
    all_good = True
    
    for module, description in required_deps:
        if not check_import(module, f"Required: {description}"):
            all_good = False
    
    print("\nOptional dependencies:")
    for module, description in optional_deps:
        check_import(module, f"Optional: {description}")
    
    return all_good

def check_file_structure():
    """Check that all expected files are present"""
    print("\nChecking file structure...")
    
    # Get the library installation path
    try:
        import fulcra_skills_support
        lib_path = Path(fulcra_skills_support.__file__).parent
        print(f"Library installed at: {lib_path}")
        
        expected_files = [
            "core.py",
            "auth.py", 
            "data.py",
            "stay_detection.py",
            "utils/__init__.py",
            "utils/geo.py",
            "utils/time.py",
            "visualization/__init__.py",
            "visualization/styles.py",
            "visualization/static.py"
        ]
        
        all_present = True
        for file_path in expected_files:
            full_path = lib_path / file_path
            if full_path.exists():
                print(f"✓ {file_path}")
            else:
                print(f"✗ {file_path} (missing)")
                all_present = False
        
        return all_present
        
    except Exception as e:
        print(f"✗ Could not check file structure: {e}")
        return False

def main():
    """Run all verification checks"""
    print("Fulcra Skills Support - Installation Verification")
    print("=" * 55)
    
    print(f"Python version: {sys.version}")
    print(f"Python path: {sys.executable}")
    
    # Run all checks
    checks = [
        ("Library Import", lambda: check_import("fulcra_skills_support", "Main library")),
        ("Dependencies", check_dependencies),
        ("File Structure", check_file_structure), 
        ("Basic Functionality", check_basic_functionality)
    ]
    
    results = []
    
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        print("-" * len(check_name))
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"✗ {check_name} failed with exception: {e}")
            results.append((check_name, False))
    
    # Summary
    print("\n" + "=" * 55)
    print("VERIFICATION SUMMARY")
    print("=" * 55)
    
    passed = 0
    total = len(results)
    
    for check_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{check_name:<20} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All checks passed! The library is correctly installed.")
        print("\nYou can now:")
        print("- Run examples/basic_usage.py to test with real data")
        print("- Import fulcra_skills_support in your own scripts")
        print("- Use the library to build new Fulcra skills")
        return 0
    else:
        print("❌ Some checks failed. Please check the installation.")
        print("\nTroubleshooting:")
        print("- Make sure you installed with: pip install fulcra-skills-support") 
        print("- Try reinstalling: pip uninstall fulcra-skills-support && pip install fulcra-skills-support")
        print("- Check that all dependencies are installed")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)