"""
Main FulcraVisualizer class - the primary interface for the library
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import matplotlib.figure
import pandas as pd

from .auth import FulcraAuthError, TokenData, TokenManager, TokenStore, run_device_auth
from .data import (
    FulcraDataClient, calculate_movement_metrics, load_location_data, 
    load_stays_data, locations_to_observations, preprocess_locations, 
    save_location_data, save_stays_data
)
from .stay_detection import StayDetector
from .utils.time import parse_date_string
from .visualization.static import StaticMapGenerator


class FulcraVisualizer:
    """
    Main interface for Fulcra location data visualization
    
    Provides authentication, data fetching, stay detection, and visualization
    capabilities in a single convenient class.
    """
    
    def __init__(self, data_client: Optional[FulcraDataClient] = None):
        self._data_client = data_client
        self._loaded_location_data = None
        self._loaded_stays_data = None
        self._stay_detector = StayDetector()
        
    @classmethod
    def from_device_auth(cls, oidc_domain: Optional[str] = None, 
                        oidc_client_id: Optional[str] = None,
                        token_path: Optional[str] = None) -> "FulcraVisualizer":
        """
        Create FulcraVisualizer using OAuth2 device authorization flow
        
        Parameters
        ----------
        oidc_domain : str, optional
            Custom OIDC domain
        oidc_client_id : str, optional  
            Custom OIDC client ID
        token_path : str, optional
            Path to save token file (default: ~/.config/fulcra/token.json)
            
        Returns
        -------
        FulcraVisualizer
        """
        if token_path is None:
            token_path = Path.home() / ".config" / "fulcra" / "token.json"
        else:
            token_path = Path(token_path)
        
        # Run device authorization
        token_data = run_device_auth(oidc_domain, oidc_client_id)
        
        # Save token
        token_store = TokenStore(token_path)
        token_store.save(token_data)
        
        # Create data client
        data_client = FulcraDataClient(token_store, oidc_domain, oidc_client_id)
        
        return cls(data_client)
    
    @classmethod
    def from_token_file(cls, token_path: Union[str, Path], 
                       oidc_domain: Optional[str] = None,
                       oidc_client_id: Optional[str] = None) -> "FulcraVisualizer":
        """
        Create FulcraVisualizer from saved token file
        
        Parameters
        ---------- 
        token_path : str or Path
            Path to token file
        oidc_domain : str, optional
            Custom OIDC domain
        oidc_client_id : str, optional
            Custom OIDC client ID
            
        Returns
        -------
        FulcraVisualizer
        """
        if isinstance(token_path, str):
            # Handle ~ expansion
            if token_path.startswith("~"):
                token_path = Path(token_path).expanduser()
            else:
                token_path = Path(token_path)
        
        token_store = TokenStore(token_path)
        data_client = FulcraDataClient(token_store, oidc_domain, oidc_client_id)
        
        return cls(data_client)
    
    @classmethod 
    def from_credentials(cls, access_token: str, refresh_token: Optional[str] = None,
                        access_token_expiration: Optional[datetime.datetime] = None,
                        oidc_domain: Optional[str] = None,
                        oidc_client_id: Optional[str] = None) -> "FulcraVisualizer":
        """
        Create FulcraVisualizer from direct credentials
        
        Parameters
        ----------
        access_token : str
            Fulcra access token
        refresh_token : str, optional
            Fulcra refresh token
        access_token_expiration : datetime.datetime, optional
            Token expiration time
        oidc_domain : str, optional
            Custom OIDC domain
        oidc_client_id : str, optional
            Custom OIDC client ID
            
        Returns
        -------
        FulcraVisualizer
        """
        # Create temporary token file
        token_path = Path("/tmp/fulcra_temp_token.json")
        token_data = TokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            access_token_expiration=access_token_expiration
        )
        
        token_store = TokenStore(token_path)
        token_store.save(token_data)
        
        data_client = FulcraDataClient(token_store, oidc_domain, oidc_client_id)
        
        return cls(data_client)
    
    def get_user_info(self) -> Dict:
        """Get user information from Fulcra API"""
        if self._data_client is None:
            raise FulcraAuthError("No authentication configured")
        return self._data_client.get_user_info()
    
    def fetch_daily_data(self, date: Union[str, datetime.date], 
                        timezone: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch location data for a single day
        
        Parameters
        ----------
        date : str or datetime.date
            Target date in 'YYYY-MM-DD' format
        timezone : str, optional
            Timezone (uses user's timezone if not specified)
            
        Returns
        -------
        DataFrame
            Location data with movement metrics
        """
        if self._data_client is None:
            raise FulcraAuthError("No authentication configured")
        
        raw_data = self._data_client.fetch_daily_locations(date, timezone)
        processed_data = preprocess_locations(raw_data)
        return calculate_movement_metrics(processed_data)
    
    def detect_stays(self, date: Union[str, datetime.date], 
                    timezone: Optional[str] = None, **detector_params) -> List[Dict]:
        """
        Detect stays for a single day
        
        Parameters
        ----------
        date : str or datetime.date
            Target date
        timezone : str, optional
            Timezone (uses user's timezone if not specified)
        **detector_params
            Parameters for StayDetector (e.g., R_SOFT=50, T_MIN=120)
            
        Returns
        -------
        list of dicts
            Stay records with keys: entry_time, exit_time, duration_seconds, 
            centroid_lat, centroid_lon, n_points
        """
        # Fetch data
        locations_df = self.fetch_daily_data(date, timezone)
        
        if locations_df.empty:
            return []
        
        # Convert to observations
        observations = locations_to_observations(locations_df)
        
        # Run stay detection
        if detector_params:
            detector = StayDetector(**detector_params)
        else:
            detector = self._stay_detector
            
        stays, debug_df = detector.detect_stays(observations)
        
        # Convert to dict format
        stay_dicts = []
        for stay in stays:
            stay_dicts.append({
                'entry_time': datetime.datetime.fromtimestamp(stay.t_in, tz=datetime.timezone.utc).isoformat(),
                'exit_time': datetime.datetime.fromtimestamp(stay.t_out, tz=datetime.timezone.utc).isoformat(),
                'duration_seconds': stay.duration,
                'centroid_lat': stay.lat,
                'centroid_lon': stay.lon,
                'n_points': stay.n_points,
            })
        
        return stay_dicts
    
    def detect_stays_from_file(self, filepath: Union[str, Path], **detector_params) -> List[Dict]:
        """
        Detect stays from saved location data file
        
        Parameters
        ----------
        filepath : str or Path
            Path to Parquet file with location data
        **detector_params
            Parameters for StayDetector
            
        Returns
        -------
        list of dicts
            Stay records
        """
        locations_df = load_location_data(filepath)
        
        if locations_df.empty:
            return []
        
        observations = locations_to_observations(locations_df)
        
        if detector_params:
            detector = StayDetector(**detector_params)
        else:
            detector = self._stay_detector
            
        stays, debug_df = detector.detect_stays(observations)
        
        # Convert to dict format
        stay_dicts = []
        for stay in stays:
            stay_dicts.append({
                'entry_time': datetime.datetime.fromtimestamp(stay.t_in, tz=datetime.timezone.utc).isoformat(),
                'exit_time': datetime.datetime.fromtimestamp(stay.t_out, tz=datetime.timezone.utc).isoformat(),
                'duration_seconds': stay.duration,
                'centroid_lat': stay.lat,
                'centroid_lon': stay.lon,
                'n_points': stay.n_points,
            })
        
        return stay_dicts
    
    def detect_stays_from_loaded_data(self, **detector_params) -> List[Dict]:
        """
        Detect stays from previously loaded location data
        
        Parameters
        ----------
        **detector_params
            Parameters for StayDetector
            
        Returns
        -------
        list of dicts
            Stay records
        """
        if self._loaded_location_data is None:
            raise ValueError("No location data loaded. Use load_location_from_file() first.")
        
        return self.detect_stays_from_file("/tmp/temp_locations.parquet", **detector_params)
    
    # Data file operations
    def save_location_data(self, locations_df: pd.DataFrame, filepath: Union[str, Path]) -> None:
        """Save location DataFrame to Parquet file"""
        save_location_data(locations_df, filepath)
    
    def load_location_from_file(self, filepath: Union[str, Path]) -> pd.DataFrame:
        """Load location data from file and store internally"""
        self._loaded_location_data = load_location_data(filepath)
        return self._loaded_location_data
    
    def save_stays_data(self, stays: List[Dict], filepath: Union[str, Path]) -> None:
        """Save stays list to Parquet file"""
        save_stays_data(stays, filepath)
    
    def load_stays_from_file(self, filepath: Union[str, Path]) -> List[Dict]:
        """Load stays data from file and store internally"""
        self._loaded_stays_data = load_stays_data(filepath)
        return self._loaded_stays_data
    
    # Static visualization methods
    def daily_path_static(self, date: Union[str, datetime.date], 
                         timezone: Optional[str] = None, **options) -> matplotlib.figure.Figure:
        """
        Generate static trajectory map for a day
        
        Parameters
        ----------
        date : str or datetime.date
            Target date
        timezone : str, optional
            Timezone
        **options
            Visualization options (width, height, title, etc.)
            
        Returns
        -------
        plotly.graph_objects.Figure
        """
        locations_df = self.fetch_daily_data(date, timezone)
        
        generator = StaticMapGenerator(
            width=options.get('width', 800),
            height=options.get('height', 600),
            map_style=options.get('map_style', 'street')
        )
        
        return generator.daily_path_static(locations_df, **options)
    
    def path_by_speed_static(self, date: Union[str, datetime.date],
                           timezone: Optional[str] = None, **options) -> matplotlib.figure.Figure:
        """
        Generate static speed-colored trajectory map
        
        Parameters
        ----------
        date : str or datetime.date
            Target date
        timezone : str, optional
            Timezone 
        **options
            Visualization options
            
        Returns
        -------
        plotly.graph_objects.Figure
        """
        locations_df = self.fetch_daily_data(date, timezone)
        
        generator = StaticMapGenerator(
            width=options.get('width', 800),
            height=options.get('height', 600),
            map_style=options.get('map_style', 'street')
        )
        
        return generator.path_by_speed_static(locations_df, **options)
    
    def stays_heatmap_static(self, date: Union[str, datetime.date],
                           timezone: Optional[str] = None, **options) -> matplotlib.figure.Figure:
        """
        Generate static stay locations heatmap
        
        Parameters
        ----------
        date : str or datetime.date
            Target date
        timezone : str, optional
            Timezone
        **options
            Visualization options
            
        Returns
        -------
        plotly.graph_objects.Figure
        """
        stays = self.detect_stays(date, timezone)
        
        generator = StaticMapGenerator(
            width=options.get('width', 800),
            height=options.get('height', 600),
            map_style=options.get('map_style', 'street')
        )
        
        return generator.stays_heatmap_static(stays, **options)
    
    def save_static_map(self, fig: matplotlib.figure.Figure, filepath: Union[str, Path], 
                       format: str = "png", **kwargs) -> None:
        """Save static map figure to file"""
        generator = StaticMapGenerator()
        generator.save_static_map(fig, filepath, format, **kwargs)
    
    # Interactive visualization methods (to be implemented)
    def daily_path_interactive(self, date: Union[str, datetime.date],
                             timezone: Optional[str] = None, **options) -> str:
        """Generate interactive trajectory map (returns HTML string)"""
        # TODO: Implement using Folium
        raise NotImplementedError("Interactive visualization not yet implemented")
    
    def path_by_speed_interactive(self, date: Union[str, datetime.date],
                                timezone: Optional[str] = None, **options) -> str:
        """Generate interactive speed-colored trajectory map"""
        # TODO: Implement using Folium
        raise NotImplementedError("Interactive visualization not yet implemented")
    
    def stays_heatmap_interactive(self, date: Union[str, datetime.date],
                                timezone: Optional[str] = None, **options) -> str:
        """Generate interactive stay locations heatmap"""
        # TODO: Implement using Folium
        raise NotImplementedError("Interactive visualization not yet implemented")
    
    def save_interactive_map(self, map_html: str, filepath: Union[str, Path]) -> None:
        """Save interactive map HTML to file"""
        with open(filepath, 'w') as f:
            f.write(map_html)