"""Tests for utility functions"""

import datetime
import pytest
import pandas as pd
import pytz

from fulcra_skills_support.utils.geo import (
    haversine_distance, calculate_bearing, bounds_from_locations, 
    center_from_bounds, calculate_zoom_level
)
from fulcra_skills_support.utils.time import (
    parse_date_string, day_time_range, format_duration, 
    format_time, is_same_day, time_of_day_category
)


class TestGeoUtils:
    """Test geographic utility functions"""
    
    def test_haversine_distance(self):
        """Test haversine distance calculation"""
        # Distance between SF and LA (approximately 559 km)
        sf_lat, sf_lon = 37.7749, -122.4194
        la_lat, la_lon = 34.0522, -118.2437
        
        distance = haversine_distance(sf_lat, sf_lon, la_lat, la_lon)
        
        # Should be roughly 559 km (559,000 m)
        assert 550_000 < distance < 570_000
    
    def test_haversine_distance_same_point(self):
        """Test haversine distance for same point"""
        lat, lon = 37.7749, -122.4194
        distance = haversine_distance(lat, lon, lat, lon)
        
        assert distance == 0.0
    
    def test_calculate_bearing(self):
        """Test bearing calculation"""
        # From SF to LA should be roughly southeast (around 135°)
        sf_lat, sf_lon = 37.7749, -122.4194
        la_lat, la_lon = 34.0522, -118.2437
        
        bearing = calculate_bearing(sf_lat, sf_lon, la_lat, la_lon)
        
        # Should be roughly southeast (100-160°)
        assert 100 < bearing < 160
    
    def test_calculate_bearing_north(self):
        """Test bearing calculation for due north"""
        lat1, lon1 = 0.0, 0.0
        lat2, lon2 = 1.0, 0.0  # 1 degree north
        
        bearing = calculate_bearing(lat1, lon1, lat2, lon2)
        
        # Should be close to 0° (north)
        assert abs(bearing) < 5 or abs(bearing - 360) < 5
    
    def test_bounds_from_locations_dataframe(self):
        """Test bounds calculation from DataFrame"""
        df = pd.DataFrame({
            'lat': [37.0, 38.0, 37.5],
            'lon': [-122.0, -121.0, -121.5]
        })
        
        min_lat, min_lon, max_lat, max_lon = bounds_from_locations(df)
        
        # Should include all points with some padding
        assert min_lat < 37.0
        assert max_lat > 38.0
        assert min_lon < -122.0
        assert max_lon > -121.0
    
    def test_bounds_from_locations_list(self):
        """Test bounds calculation from list of dicts"""
        locations = [
            {'lat': 37.0, 'lon': -122.0},
            {'lat': 38.0, 'lon': -121.0},
            {'lat': 37.5, 'lon': -121.5}
        ]
        
        min_lat, min_lon, max_lat, max_lon = bounds_from_locations(locations)
        
        # Should include all points with some padding
        assert min_lat < 37.0
        assert max_lat > 38.0
        assert min_lon < -122.0
        assert max_lon > -121.0
    
    def test_bounds_empty_data(self):
        """Test bounds calculation with empty data"""
        df_empty = pd.DataFrame(columns=['lat', 'lon'])
        list_empty = []
        
        bounds_df = bounds_from_locations(df_empty)
        bounds_list = bounds_from_locations(list_empty)
        
        assert bounds_df == (0.0, 0.0, 0.0, 0.0)
        assert bounds_list == (0.0, 0.0, 0.0, 0.0)
    
    def test_center_from_bounds(self):
        """Test center calculation from bounds"""
        bounds = (37.0, -122.0, 38.0, -121.0)
        center_lat, center_lon = center_from_bounds(bounds)
        
        assert center_lat == 37.5  # Midpoint of 37.0 and 38.0
        assert center_lon == -121.5  # Midpoint of -122.0 and -121.0
    
    def test_calculate_zoom_level(self):
        """Test zoom level calculation"""
        # Small area should have high zoom
        small_bounds = (37.77, -122.42, 37.78, -122.41)
        small_zoom = calculate_zoom_level(small_bounds)
        
        # Large area should have low zoom
        large_bounds = (30.0, -130.0, 40.0, -110.0)
        large_zoom = calculate_zoom_level(large_bounds)
        
        assert small_zoom > large_zoom
        assert 1 <= small_zoom <= 20
        assert 1 <= large_zoom <= 20


class TestTimeUtils:
    """Test time utility functions"""
    
    def test_parse_date_string(self):
        """Test date string parsing"""
        # String format
        date_str = "2023-05-15"
        parsed = parse_date_string(date_str)
        assert parsed == datetime.date(2023, 5, 15)
        
        # Date object
        date_obj = datetime.date(2023, 5, 15)
        parsed = parse_date_string(date_obj)
        assert parsed == date_obj
        
        # DateTime object
        datetime_obj = datetime.datetime(2023, 5, 15, 10, 30)
        parsed = parse_date_string(datetime_obj)
        assert parsed == datetime.date(2023, 5, 15)
    
    def test_day_time_range(self):
        """Test day time range calculation"""
        date = "2023-05-15"
        timezone = "America/Los_Angeles"
        
        start_time, end_time = day_time_range(date, timezone)
        
        # Should be timezone-aware
        assert start_time.tzinfo is not None
        assert end_time.tzinfo is not None
        
        # Should span the full day
        assert start_time.hour == 0
        assert start_time.minute == 0
        assert start_time.second == 0
        assert end_time.hour == 23
        assert end_time.minute == 59
        assert end_time.second == 59
    
    def test_format_duration(self):
        """Test duration formatting"""
        assert format_duration(30) == "30 sec"
        assert format_duration(90) == "1 min"
        assert format_duration(3600) == "1h"
        assert format_duration(3900) == "1h 5m"
        assert format_duration(7200) == "2h"
    
    def test_format_time(self):
        """Test time formatting"""
        # Unix timestamp
        timestamp = 1684152600  # 2023-05-15 10:30:00 UTC
        formatted = format_time(timestamp, timezone="UTC")
        assert "10:30" in formatted
        
        # DateTime object
        dt = datetime.datetime(2023, 5, 15, 10, 30, tzinfo=datetime.timezone.utc)
        formatted = format_time(dt, timezone="UTC")
        assert "10:30" in formatted
    
    def test_is_same_day(self):
        """Test same day checking"""
        tz = pytz.timezone("America/Los_Angeles")
        
        # Same day, different times
        dt1 = tz.localize(datetime.datetime(2023, 5, 15, 10, 0))
        dt2 = tz.localize(datetime.datetime(2023, 5, 15, 22, 0))
        assert is_same_day(dt1, dt2, "America/Los_Angeles")
        
        # Different days
        dt3 = tz.localize(datetime.datetime(2023, 5, 16, 2, 0))
        assert not is_same_day(dt1, dt3, "America/Los_Angeles")
    
    def test_time_of_day_category(self):
        """Test time of day categorization"""
        # Morning (6-12)
        morning_ts = datetime.datetime(2023, 5, 15, 9, 0, tzinfo=datetime.timezone.utc).timestamp()
        assert time_of_day_category(morning_ts, "UTC") == "morning"
        
        # Afternoon (12-18)
        afternoon_ts = datetime.datetime(2023, 5, 15, 15, 0, tzinfo=datetime.timezone.utc).timestamp()
        assert time_of_day_category(afternoon_ts, "UTC") == "afternoon"
        
        # Evening (18-22)
        evening_ts = datetime.datetime(2023, 5, 15, 20, 0, tzinfo=datetime.timezone.utc).timestamp()
        assert time_of_day_category(evening_ts, "UTC") == "evening"
        
        # Night (22-6)
        night_ts = datetime.datetime(2023, 5, 15, 2, 0, tzinfo=datetime.timezone.utc).timestamp()
        assert time_of_day_category(night_ts, "UTC") == "night"