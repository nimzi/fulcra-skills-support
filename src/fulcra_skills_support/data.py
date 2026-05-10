"""
Data fetching and processing for Fulcra API
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, List, Optional, Union

import pandas as pd
import pytz

from .auth import FulcraAuthError, TokenManager, TokenStore
from .stay_detection import Observation

try:
    from fulcra_api.core import FulcraAPI
except ImportError:
    FulcraAPI = None


class FulcraDataClient:
    """High-level client for fetching and processing Fulcra location data"""
    
    def __init__(self, token_store: TokenStore, oidc_domain: Optional[str] = None, 
                 oidc_client_id: Optional[str] = None):
        self.token_manager = TokenManager(oidc_domain, oidc_client_id)
        self.token_store = token_store
        self._client = None
        self._token = None
    
    @property
    def client(self) -> Any:
        """Get authenticated Fulcra API client, refreshing if needed"""
        if self._client is None or not self._is_token_valid():
            self._client, self._token = self.token_manager.get_authenticated_client(self.token_store)
        return self._client
    
    def _is_token_valid(self) -> bool:
        """Check if current token is still valid"""
        if not self._token or not self._token.access_token_expiration:
            return False
        now = datetime.datetime.now(datetime.timezone.utc)
        expiry = self._token.access_token_expiration
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=datetime.timezone.utc)
        return expiry > now + datetime.timedelta(seconds=60)
    
    def get_user_info(self) -> dict:
        """Get user information including timezone preferences"""
        return self.client.get_user_info()
    
    def fetch_daily_locations(self, date: Union[str, datetime.date], 
                            timezone: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch raw location data for a single day
        
        Parameters
        ----------
        date : str or datetime.date
            Date in format 'YYYY-MM-DD' or date object
        timezone : str, optional
            Timezone name (e.g., 'America/Los_Angeles'). If None, uses user's timezone.
            
        Returns
        -------
        DataFrame with columns: timestamp, lat, lon, speed, course_heading_degrees
        """
        if isinstance(date, str):
            date = datetime.date.fromisoformat(date)
        
        if timezone is None:
            user_info = self.get_user_info()
            timezone = user_info.get("preferences", {}).get("timezone", "UTC")
        
        tz = pytz.timezone(timezone)
        start_time = tz.localize(datetime.datetime(date.year, date.month, date.day, 0, 0, 0))
        end_time = tz.localize(datetime.datetime(date.year, date.month, date.day, 23, 59, 59))
        
        # Fetch Apple location updates (primary source)
        updates = self.client.apple_location_updates(start_time, end_time)
        
        records = []
        for r in updates:
            records.append({
                'timestamp': r['timestamp'],
                'lat': r['latitude_degrees'],
                'lon': r['longitude_degrees'],
                'speed': r.get('speed') if r.get('speed', -1) >= 0 else None,
                'course_heading_degrees': r.get('course_heading_degrees') if r.get('course_heading_degrees', -1) >= 0 else None,
            })
        
        return pd.DataFrame(records)
    
    def fetch_location_visits(self, date: Union[str, datetime.date], 
                            timezone: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch Apple location visits for a single day
        
        Returns DataFrame with visit-level location data
        """
        if isinstance(date, str):
            date = datetime.date.fromisoformat(date)
        
        if timezone is None:
            user_info = self.get_user_info()
            timezone = user_info.get("preferences", {}).get("timezone", "UTC")
        
        tz = pytz.timezone(timezone)
        start_time = tz.localize(datetime.datetime(date.year, date.month, date.day, 0, 0, 0))
        end_time = tz.localize(datetime.datetime(date.year, date.month, date.day, 23, 59, 59))
        
        visits = self.client.apple_location_visits(start_time, end_time)
        
        records = []
        for v in visits:
            records.append({
                'arrival_date': v.get('arrival_date'),
                'departure_date': v.get('departure_date'),
                'lat': v['latitude_degrees'],
                'lon': v['longitude_degrees'],
                'horizontal_accuracy_meters': v.get('horizontal_accuracy_meters'),
            })
        
        return pd.DataFrame(records)


def preprocess_locations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and validate location data
    
    Parameters
    ---------- 
    df : DataFrame
        Raw location data with columns: timestamp, lat, lon, speed, course_heading_degrees
        
    Returns
    -------
    DataFrame with cleaned data, sorted by timestamp
    """
    if df.empty:
        return df
    
    # Remove invalid coordinates
    df = df.dropna(subset=['lat', 'lon'])
    df = df[(df['lat'].between(-90, 90)) & (df['lon'].between(-180, 180))]
    
    # Convert timestamp to datetime for sorting
    df['timestamp_dt'] = pd.to_datetime(df['timestamp'], format='ISO8601', utc=True)
    df = df.sort_values('timestamp_dt')
    
    # Remove duplicates (same timestamp and location)
    df = df.drop_duplicates(subset=['timestamp', 'lat', 'lon'])
    
    # Clean speed and heading (remove negative sentinel values)
    df.loc[df['speed'] < 0, 'speed'] = None
    df.loc[df['course_heading_degrees'] < 0, 'course_heading_degrees'] = None
    
    return df.drop('timestamp_dt', axis=1).reset_index(drop=True)


def calculate_movement_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add calculated movement metrics to location data
    
    Parameters
    ----------
    df : DataFrame
        Location data with columns: timestamp, lat, lon
        
    Returns
    -------
    DataFrame with additional columns: distance_m, calculated_speed_mps, time_diff_s
    """
    if len(df) < 2:
        return df
    
    # Convert timestamps to datetime
    timestamps = pd.to_datetime(df['timestamp'], format='ISO8601', utc=True)
    
    # Calculate distances between consecutive points
    distances = []
    time_diffs = []
    calculated_speeds = []
    
    for i in range(len(df)):
        if i == 0:
            distances.append(0.0)
            time_diffs.append(0.0)
            calculated_speeds.append(0.0)
        else:
            # Calculate haversine distance
            from .utils.geo import haversine_distance
            dist = haversine_distance(
                df.iloc[i-1]['lat'], df.iloc[i-1]['lon'],
                df.iloc[i]['lat'], df.iloc[i]['lon']
            )
            distances.append(dist)
            
            # Calculate time difference
            time_diff = (timestamps.iloc[i] - timestamps.iloc[i-1]).total_seconds()
            time_diffs.append(time_diff)
            
            # Calculate speed (m/s)
            if time_diff > 0:
                speed = dist / time_diff
            else:
                speed = 0.0
            calculated_speeds.append(speed)
    
    df = df.copy()
    df['distance_m'] = distances
    df['time_diff_s'] = time_diffs  
    df['calculated_speed_mps'] = calculated_speeds
    
    return df


def locations_to_observations(df: pd.DataFrame) -> List[Observation]:
    """
    Convert DataFrame of locations to list of Observation objects for stay detection
    
    Parameters
    ----------
    df : DataFrame
        Location data with columns: timestamp, lat, lon, speed, course_heading_degrees
        
    Returns
    -------
    List of Observation objects, sorted by timestamp
    """
    observations = []
    
    for _, row in df.iterrows():
        timestamp_dt = pd.to_datetime(row['timestamp'])
        
        obs = Observation(
            t=timestamp_dt.timestamp(),
            lat=float(row['lat']),
            lon=float(row['lon']),
            speed=float(row['speed']) if pd.notna(row.get('speed')) else None,
            heading=float(row['course_heading_degrees']) if pd.notna(row.get('course_heading_degrees')) else None,
        )
        observations.append(obs)
    
    # Sort by timestamp
    observations.sort(key=lambda o: o.t)
    
    return observations


def save_location_data(df: pd.DataFrame, filepath: Union[str, Path]) -> None:
    """Save location DataFrame to Parquet file"""
    df.to_parquet(filepath, index=False)


def load_location_data(filepath: Union[str, Path]) -> pd.DataFrame:
    """Load location DataFrame from Parquet file"""
    return pd.read_parquet(filepath)


def save_stays_data(stays: List, filepath: Union[str, Path]) -> None:
    """Save stays list to Parquet file"""
    from .stay_detection import Stay
    
    if not stays:
        # Create empty DataFrame with correct schema
        df = pd.DataFrame(columns=[
            'entry_time', 'exit_time', 'duration_seconds', 
            'centroid_lat', 'centroid_lon', 'n_points'
        ])
    else:
        records = []
        for stay in stays:
            if isinstance(stay, Stay):
                records.append({
                    'entry_time': datetime.datetime.fromtimestamp(stay.t_in, tz=datetime.timezone.utc).isoformat(),
                    'exit_time': datetime.datetime.fromtimestamp(stay.t_out, tz=datetime.timezone.utc).isoformat(),
                    'duration_seconds': stay.duration,
                    'centroid_lat': stay.lat,
                    'centroid_lon': stay.lon,
                    'n_points': stay.n_points,
                })
            else:
                # Handle dict format
                records.append(stay)
        df = pd.DataFrame(records)
    
    df.to_parquet(filepath, index=False)


def load_stays_data(filepath: Union[str, Path]) -> List:
    """Load stays list from Parquet file"""
    df = pd.read_parquet(filepath)
    stays = []
    
    for _, row in df.iterrows():
        # Convert back to Stay objects or keep as dicts
        stay_data = {
            'entry_time': row['entry_time'],
            'exit_time': row['exit_time'],
            'duration_seconds': row['duration_seconds'],
            'centroid_lat': row['centroid_lat'],
            'centroid_lon': row['centroid_lon'],
            'n_points': row['n_points'],
        }
        stays.append(stay_data)
    
    return stays