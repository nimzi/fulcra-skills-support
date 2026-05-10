"""Geographic utility functions"""

from __future__ import annotations

import math
from typing import List, Tuple, Union

import pandas as pd


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points using Haversine formula
    
    Parameters
    ----------
    lat1, lon1 : float
        Latitude and longitude of first point (degrees)
    lat2, lon2 : float  
        Latitude and longitude of second point (degrees)
        
    Returns
    -------
    float
        Distance in meters
    """
    R = 6_371_000.0  # Earth's radius in meters
    
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    
    a = (math.sin(dphi / 2) ** 2 + 
         math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2)
    c = 2 * math.asin(math.sqrt(max(0.0, min(1.0, a))))
    
    return R * c


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate bearing (compass heading) from point 1 to point 2
    
    Parameters
    ----------
    lat1, lon1 : float
        Latitude and longitude of first point (degrees)
    lat2, lon2 : float
        Latitude and longitude of second point (degrees)
        
    Returns
    -------
    float
        Bearing in degrees (0-360°, where 0° = North, 90° = East)
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlon_rad = math.radians(lon2 - lon1)
    
    y = math.sin(dlon_rad) * math.cos(lat2_rad)
    x = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad))
    
    bearing_rad = math.atan2(y, x)
    bearing_deg = math.degrees(bearing_rad)
    
    # Convert to 0-360° range
    return (bearing_deg + 360) % 360


def bounds_from_locations(locations: Union[pd.DataFrame, List[dict]]) -> Tuple[float, float, float, float]:
    """
    Calculate bounding box from location data
    
    Parameters
    ---------- 
    locations : DataFrame or list of dicts
        Location data with 'lat' and 'lon' columns/keys
        
    Returns
    -------
    tuple
        (min_lat, min_lon, max_lat, max_lon)
    """
    if isinstance(locations, pd.DataFrame):
        if locations.empty:
            return (0.0, 0.0, 0.0, 0.0)
        
        min_lat = locations['lat'].min()
        max_lat = locations['lat'].max() 
        min_lon = locations['lon'].min()
        max_lon = locations['lon'].max()
        
    else:  # List of dicts
        if not locations:
            return (0.0, 0.0, 0.0, 0.0)
            
        lats = [loc['lat'] for loc in locations if 'lat' in loc]
        lons = [loc['lon'] for loc in locations if 'lon' in loc]
        
        if not lats or not lons:
            return (0.0, 0.0, 0.0, 0.0)
            
        min_lat = min(lats)
        max_lat = max(lats)
        min_lon = min(lons) 
        max_lon = max(lons)
    
    # Add small padding to bounds
    lat_padding = max(0.001, (max_lat - min_lat) * 0.1)
    lon_padding = max(0.001, (max_lon - min_lon) * 0.1)
    
    return (
        min_lat - lat_padding,
        min_lon - lon_padding, 
        max_lat + lat_padding,
        max_lon + lon_padding
    )


def center_from_bounds(bounds: Tuple[float, float, float, float]) -> Tuple[float, float]:
    """
    Calculate center point from bounding box
    
    Parameters
    ----------
    bounds : tuple
        (min_lat, min_lon, max_lat, max_lon)
        
    Returns
    -------
    tuple
        (center_lat, center_lon)
    """
    min_lat, min_lon, max_lat, max_lon = bounds
    return ((min_lat + max_lat) / 2, (min_lon + max_lon) / 2)


def calculate_zoom_level(bounds: Tuple[float, float, float, float], 
                        map_width: int = 800, map_height: int = 600) -> int:
    """
    Estimate appropriate zoom level for given bounds and map size
    
    Parameters
    ----------
    bounds : tuple
        (min_lat, min_lon, max_lat, max_lon)
    map_width, map_height : int
        Map dimensions in pixels
        
    Returns  
    -------
    int
        Zoom level (typically 1-20)
    """
    min_lat, min_lon, max_lat, max_lon = bounds
    
    # Calculate span
    lat_span = max_lat - min_lat
    lon_span = max_lon - min_lon
    
    # Rough calculation based on degrees per pixel at different zoom levels
    # This is approximate and works for most mid-latitude locations
    max_span = max(lat_span, lon_span)
    
    if max_span >= 180:
        return 1
    elif max_span >= 90:
        return 2
    elif max_span >= 45:
        return 3
    elif max_span >= 22.5:
        return 4
    elif max_span >= 11.25:
        return 5
    elif max_span >= 5.625:
        return 6
    elif max_span >= 2.8125:
        return 7
    elif max_span >= 1.40625:
        return 8
    elif max_span >= 0.703125:
        return 9
    elif max_span >= 0.3515625:
        return 10
    elif max_span >= 0.17578125:
        return 11
    elif max_span >= 0.087890625:
        return 12
    elif max_span >= 0.0439453125:
        return 13
    elif max_span >= 0.02197265625:
        return 14
    elif max_span >= 0.010986328125:
        return 15
    else:
        return 16