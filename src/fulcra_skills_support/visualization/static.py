"""Static visualization using Plotly"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.io import to_image

from ..utils.geo import bounds_from_locations, center_from_bounds
from .styles import ColorSchemes, MapStyles, PlotlyThemes


class StaticMapGenerator:
    """Generate static maps using Plotly"""
    
    def __init__(self, map_style: str = "street", width: int = 800, height: int = 600):
        self.map_style = MapStyles.plotly_map_style(map_style)
        self.width = width
        self.height = height
        
    def daily_path_static(self, locations_df: pd.DataFrame, **options) -> go.Figure:
        """
        Create static trajectory line map
        
        Parameters
        ----------
        locations_df : DataFrame
            Location data with columns: lat, lon, timestamp
        **options
            Additional styling options
            
        Returns
        -------
        plotly.graph_objects.Figure
        """
        if locations_df.empty:
            return self._empty_map()
        
        # Calculate map center and zoom
        bounds = bounds_from_locations(locations_df)
        center_lat, center_lon = center_from_bounds(bounds)
        
        fig = go.Figure()
        
        # Add trajectory line
        trace_style = PlotlyThemes.trajectory_trace_style().copy()
        trace_style.update(options.get("trajectory_style", {}))
        
        fig.add_trace(go.Scattermapbox(
            lat=locations_df['lat'],
            lon=locations_df['lon'],
            text=locations_df['timestamp'] if 'timestamp' in locations_df.columns else None,
            name="Daily Path",
            **trace_style
        ))
        
        # Configure layout
        layout = PlotlyThemes.default_layout().copy()
        layout.update({
            "mapbox": {
                "style": self.map_style,
                "center": {"lat": center_lat, "lon": center_lon},
                "zoom": self._calculate_zoom(bounds)
            },
            "width": self.width,
            "height": self.height,
            "title": options.get("title", "Daily Movement Path")
        })
        
        fig.update_layout(**layout)
        return fig
    
    def path_by_speed_static(self, locations_df: pd.DataFrame, **options) -> go.Figure:
        """
        Create static trajectory map color-coded by speed
        
        Parameters
        ----------
        locations_df : DataFrame
            Location data with columns: lat, lon, speed (optional)
        **options
            Additional styling options
            
        Returns
        -------
        plotly.graph_objects.Figure  
        """
        if locations_df.empty:
            return self._empty_map()
        
        # Use calculated speed if speed column missing
        if 'speed' not in locations_df.columns and 'calculated_speed_mps' in locations_df.columns:
            locations_df = locations_df.copy()
            locations_df['speed'] = locations_df['calculated_speed_mps']
        
        # Handle missing speed data
        if 'speed' not in locations_df.columns or locations_df['speed'].isna().all():
            # Fall back to regular path if no speed data
            return self.daily_path_static(locations_df, **options)
        
        bounds = bounds_from_locations(locations_df)
        center_lat, center_lon = center_from_bounds(bounds)
        
        # Create color scale based on speed
        speed_data = locations_df['speed'].fillna(0)
        max_speed = options.get('max_speed', speed_data.quantile(0.95))
        
        fig = px.scatter_mapbox(
            locations_df,
            lat='lat',
            lon='lon', 
            color='speed',
            color_continuous_scale='Viridis',
            range_color=[0, max_speed],
            mapbox_style=self.map_style,
            zoom=self._calculate_zoom(bounds),
            center={"lat": center_lat, "lon": center_lon},
            title=options.get("title", "Movement Path by Speed"),
            width=self.width,
            height=self.height
        )
        
        # Connect points with lines if requested
        if options.get('show_path', True):
            fig.add_trace(go.Scattermapbox(
                lat=locations_df['lat'],
                lon=locations_df['lon'],
                mode='lines',
                line=dict(color='rgba(0,0,0,0.3)', width=2),
                name='Path',
                showlegend=False
            ))
        
        return fig
    
    def stays_heatmap_static(self, stays_data: List[Dict], **options) -> go.Figure:
        """
        Create static heatmap of stay locations
        
        Parameters
        ----------
        stays_data : list of dicts
            Stay data with keys: centroid_lat, centroid_lon, duration_seconds
        **options
            Additional styling options
            
        Returns
        -------
        plotly.graph_objects.Figure
        """
        if not stays_data:
            return self._empty_map()
        
        # Convert to DataFrame for easier handling
        stays_df = pd.DataFrame(stays_data)
        
        # Ensure required columns exist
        lat_col = 'centroid_lat' if 'centroid_lat' in stays_df.columns else 'lat'
        lon_col = 'centroid_lon' if 'centroid_lon' in stays_df.columns else 'lon'
        dur_col = 'duration_seconds' if 'duration_seconds' in stays_df.columns else 'duration'
        
        bounds = bounds_from_locations(stays_df.rename(columns={lat_col: 'lat', lon_col: 'lon'}))
        center_lat, center_lon = center_from_bounds(bounds)
        
        # Create scatter plot sized by duration
        fig = px.scatter_mapbox(
            stays_df,
            lat=lat_col,
            lon=lon_col,
            size=dur_col,
            color=dur_col,
            color_continuous_scale='Reds',
            mapbox_style=self.map_style,
            zoom=self._calculate_zoom(bounds),
            center={"lat": center_lat, "lon": center_lon},
            title=options.get("title", "Stay Locations"),
            width=self.width,
            height=self.height,
            size_max=options.get('max_marker_size', 30)
        )
        
        return fig
    
    def _empty_map(self) -> go.Figure:
        """Create empty map figure"""
        fig = go.Figure()
        layout = PlotlyThemes.default_layout().copy()
        layout.update({
            "mapbox": {
                "style": self.map_style,
                "center": {"lat": 37.7749, "lon": -122.4194},  # Default to SF
                "zoom": 10
            },
            "width": self.width,
            "height": self.height,
            "title": "No Data Available"
        })
        fig.update_layout(**layout)
        return fig
    
    def _calculate_zoom(self, bounds) -> int:
        """Calculate appropriate zoom level for bounds"""
        from ..utils.geo import calculate_zoom_level
        return calculate_zoom_level(bounds, self.width, self.height)
    
    def save_static_map(self, fig: go.Figure, filepath: Union[str, Path], 
                       format: str = "png", **kwargs) -> None:
        """
        Save figure as static image
        
        Parameters
        ----------
        fig : plotly.graph_objects.Figure
            Figure to save
        filepath : str or Path
            Output file path
        format : str
            Image format: 'png', 'svg', 'pdf', 'jpg'
        **kwargs
            Additional options passed to plotly.io.to_image
        """
        # Default export options
        export_options = {
            "width": self.width,
            "height": self.height,
            "scale": kwargs.get('scale', 2)  # Higher DPI
        }
        export_options.update(kwargs)
        
        img_bytes = to_image(fig, format=format, **export_options)
        
        with open(filepath, 'wb') as f:
            f.write(img_bytes)
    
    def fig_to_html(self, fig: go.Figure, **kwargs) -> str:
        """
        Convert figure to HTML string
        
        Parameters
        ----------
        fig : plotly.graph_objects.Figure
            Figure to convert
        **kwargs
            Additional options passed to plotly.offline.plot
            
        Returns
        -------
        str
            HTML string
        """
        return fig.to_html(
            include_plotlyjs=kwargs.get('include_plotlyjs', 'cdn'),
            div_id=kwargs.get('div_id', None),
            config={'displayModeBar': kwargs.get('show_toolbar', True)}
        )