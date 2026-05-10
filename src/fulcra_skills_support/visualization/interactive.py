"""
Interactive map generation using Folium + Playwright PNG rendering.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Union

import folium
import folium.plugins
import numpy as np
import pandas as pd

from ..utils.geo import bounds_from_locations, center_from_bounds

# Path to the playwright-env site-packages bundled with this project
_PLAYWRIGHT_ENV = (
    Path(__file__).parents[3] / "playwright-env" /
    "lib" / "python3.12" / "site-packages"
)


def _time_color(t: float) -> str:
    """Interpolate from bright blue (#00BFFF) to bright orange (#FF4500) for t in [0, 1]."""
    r = int(0x00 + t * (0xFF - 0x00))
    g = int(0xBF + t * (0x45 - 0xBF))
    b = int(0xFF + t * (0x00 - 0xFF))
    return f"#{r:02x}{g:02x}{b:02x}"


class InteractiveMapGenerator:
    """Generate maps using Folium (Leaflet.js) and render to PNG via Playwright."""

    def __init__(self, width: int = 800, height: int = 1200):
        self.width = width
        self.height = height

    def daily_path_with_stays(
        self,
        locations_df: pd.DataFrame,
        stays: List[Dict],
        **options,
    ) -> folium.Map:
        """
        Build a Folium map with a time-colored path and numbered stay markers.
        """
        bounds = bounds_from_locations(locations_df)
        center_lat, center_lon = center_from_bounds(bounds)

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles=None,
            prefer_canvas=True,
            zoom_control=False,
        )

        # Dark base layer
        folium.TileLayer(
            "CartoDB dark_matter",
            name="Dark",
            attr="&copy; CartoDB",
        ).add_to(m)

        # OSM overlay at reduced opacity for context
        folium.TileLayer(
            "OpenStreetMap",
            name="Streets",
            attr="&copy; OpenStreetMap contributors",
            opacity=0.35,
        ).add_to(m)

        # Fit map to data bounds
        min_lat, min_lon, max_lat, max_lon = bounds
        m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

        # Build color gradient by time
        if "timestamp" in locations_df.columns:
            ts = pd.to_datetime(locations_df["timestamp"], format="ISO8601", utc=True)
            t0, t1 = ts.min(), ts.max()
            span = (t1 - t0).total_seconds()
            norm_vals = (
                ((ts - t0).dt.total_seconds() / span).values
                if span > 0
                else np.full(len(ts), 0.5)
            )
        else:
            norm_vals = np.linspace(0, 1, len(locations_df))

        positions = list(zip(locations_df["lat"], locations_df["lon"]))

        folium.ColorLine(
            positions=positions,
            colors=norm_vals.tolist(),   # numeric 0–1 values
            colormap=[_time_color(t) for t in np.linspace(0, 1, 10)],
            weight=4,
            opacity=0.95,
        ).add_to(m)

        # Numbered stay markers
        stays_sorted = sorted(stays, key=lambda s: s["entry_time"])
        for i, stay in enumerate(stays_sorted, 1):
            icon_html = (
                f'<div style="'
                f'background:#FF4500;color:white;border:2px solid white;'
                f'border-radius:50%;width:26px;height:26px;'
                f'display:flex;align-items:center;justify-content:center;'
                f'font-weight:bold;font-size:13px;font-family:sans-serif;'
                f'box-shadow:0 0 6px rgba(255,69,0,0.8);">'
                f'{i}</div>'
            )

            def _fmt(iso: str) -> str:
                from datetime import datetime
                return datetime.fromisoformat(iso).strftime("%H:%M")

            popup_text = (
                f"Stay {i}: {_fmt(stay['entry_time'])}–{_fmt(stay['exit_time'])}, "
                f"{int(stay['duration_seconds']) // 60} min"
            )

            folium.Marker(
                location=[stay["centroid_lat"], stay["centroid_lon"]],
                icon=folium.DivIcon(html=icon_html, icon_size=(26, 26), icon_anchor=(13, 13)),
                popup=folium.Popup(popup_text, max_width=200),
            ).add_to(m)

        return m

    def render_to_png(
        self,
        folium_map: folium.Map,
        output_path: Union[str, Path],
    ) -> Path:
        """
        Render a Folium map to PNG using a headless Playwright browser.
        """
        output_path = Path(output_path)

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            html_path = Path(f.name)

        folium_map.save(str(html_path))

        if str(_PLAYWRIGHT_ENV) not in sys.path:
            sys.path.insert(0, str(_PLAYWRIGHT_ENV))

        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(
                viewport={"width": self.width, "height": self.height}
            )
            page.goto(f"file://{html_path}")
            # Wait for tiles to load
            page.wait_for_timeout(3000)
            page.screenshot(path=str(output_path))
            browser.close()

        html_path.unlink(missing_ok=True)
        return output_path

    def save_html(
        self,
        folium_map: folium.Map,
        output_path: Union[str, Path],
    ) -> Path:
        """Save the Folium map as an interactive HTML file."""
        output_path = Path(output_path)
        folium_map.save(str(output_path))
        return output_path
