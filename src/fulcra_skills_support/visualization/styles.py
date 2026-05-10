"""Color schemes and styling for visualizations"""

from __future__ import annotations

from typing import Dict, List, Union

import numpy as np


class ColorSchemes:
    """Predefined color schemes for different visualization types"""
    
    @staticmethod
    def speed_gradient() -> List[str]:
        """Color gradient for speed visualization (blue=slow, red=fast)"""
        return [
            "#313695",  # Dark blue (stationary)
            "#4575b4",  # Blue
            "#74add1",  # Light blue
            "#abd9e9",  # Very light blue
            "#e0f3f8",  # Almost white
            "#fee090",  # Light yellow
            "#fdae61",  # Orange
            "#f46d43",  # Red-orange
            "#d73027",  # Red
            "#a50026"   # Dark red (very fast)
        ]
    
    @staticmethod
    def time_of_day() -> Dict[str, str]:
        """Colors for different times of day"""
        return {
            "morning": "#FDB462",    # Orange
            "afternoon": "#80B1D3",  # Light blue
            "evening": "#FB8072",    # Light red
            "night": "#BEBADA"       # Purple
        }
    
    @staticmethod
    def stay_duration() -> List[str]:
        """Color gradient for stay duration (light=short, dark=long)"""
        return [
            "#fee5d9",  # Very light red
            "#fcbba1",  # Light red
            "#fc9272",  # Medium red
            "#fb6a4a",  # Red
            "#ef3b2c",  # Dark red
            "#cb181d",  # Very dark red
            "#99000d"   # Darkest red
        ]
    
    @staticmethod
    def trajectory_default() -> str:
        """Default color for trajectory lines"""
        return "#2E86AB"  # Nice blue
    
    @staticmethod
    def stays_default() -> str:
        """Default color for stay markers"""
        return "#F24236"  # Red
    
    @staticmethod
    def qualitative_colors() -> List[str]:
        """Qualitative colors for categorical data"""
        return [
            "#1f77b4",  # Blue
            "#ff7f0e",  # Orange
            "#2ca02c",  # Green
            "#d62728",  # Red
            "#9467bd",  # Purple
            "#8c564b",  # Brown
            "#e377c2",  # Pink
            "#7f7f7f",  # Gray
            "#bcbd22",  # Olive
            "#17becf"   # Cyan
        ]
    
    @staticmethod
    def get_speed_color(speed_mps: float, max_speed: float = 20.0) -> str:
        """
        Get color for specific speed value
        
        Parameters
        ----------
        speed_mps : float
            Speed in meters per second
        max_speed : float
            Maximum speed for color scaling
            
        Returns
        -------
        str
            Hex color code
        """
        if speed_mps <= 0:
            return ColorSchemes.speed_gradient()[0]
        
        # Normalize speed to 0-1 range
        normalized = min(speed_mps / max_speed, 1.0)
        
        # Map to color gradient
        colors = ColorSchemes.speed_gradient()
        index = min(int(normalized * (len(colors) - 1)), len(colors) - 1)
        return colors[index]
    
    @staticmethod
    def get_time_color(timestamp: float, timezone: str = "UTC") -> str:
        """
        Get color for time of day
        
        Parameters
        ----------
        timestamp : float
            Unix timestamp
        timezone : str
            Timezone for time categorization
            
        Returns
        -------
        str
            Hex color code
        """
        from ..utils.time import time_of_day_category
        category = time_of_day_category(timestamp, timezone)
        return ColorSchemes.time_of_day()[category]


class MapStyles:
    """Map styling configurations for different visualization types"""
    
    @staticmethod
    def street_map() -> Dict[str, Union[str, int]]:
        """OpenStreetMap street view style"""
        return {
            "tiles": "OpenStreetMap",
            "attr": "OpenStreetMap contributors"
        }
    
    @staticmethod
    def satellite() -> Dict[str, Union[str, int]]:
        """Satellite imagery style"""
        return {
            "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            "attr": "Esri WorldImagery"
        }
    
    @staticmethod
    def terrain() -> Dict[str, Union[str, int]]:
        """Terrain/topographic style"""
        return {
            "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
            "attr": "Esri WorldTopoMap"
        }
    
    @staticmethod
    def dark_mode() -> Dict[str, Union[str, int]]:
        """Dark theme map style"""
        return {
            "tiles": "https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png",
            "attr": "Stadia Maps"
        }
    
    @staticmethod
    def minimal() -> Dict[str, Union[str, int]]:
        """Minimal/clean map style"""
        return {
            "tiles": "https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}{r}.png", 
            "attr": "Stadia Maps"
        }
    
    @staticmethod
    def plotly_map_style(style_name: str = "open-street-map") -> str:
        """
        Get Plotly mapbox style name
        
        Parameters
        ----------
        style_name : str
            Style name: 'open-street-map', 'satellite', 'outdoors', 'light', 'dark'
            
        Returns
        -------
        str
            Plotly mapbox style identifier
        """
        valid_styles = {
            "street": "open-street-map",
            "satellite": "satellite",
            "terrain": "outdoors", 
            "light": "light",
            "dark": "dark"
        }
        return valid_styles.get(style_name, "open-street-map")


class PlotlyThemes:
    """Plotly-specific theme configurations"""
    
    @staticmethod
    def default_layout() -> Dict:
        """Default layout settings for Plotly maps"""
        return {
            "showlegend": True,
            "legend": {
                "orientation": "v",
                "yanchor": "top",
                "y": 1,
                "xanchor": "left", 
                "x": 1.01
            },
            "margin": {"r": 0, "t": 40, "l": 0, "b": 0},
            "font": {"size": 12},
        }
    
    @staticmethod
    def trajectory_trace_style() -> Dict:
        """Default style for trajectory traces"""
        return {
            "mode": "lines",
            "line": {
                "width": 3,
                "color": ColorSchemes.trajectory_default()
            },
            "showlegend": True
        }
    
    @staticmethod
    def stays_trace_style() -> Dict:
        """Default style for stay markers"""
        return {
            "mode": "markers",
            "marker": {
                "size": 12,
                "color": ColorSchemes.stays_default(),
                "symbol": "circle",
                "line": {"width": 2, "color": "white"}
            },
            "showlegend": True
        }