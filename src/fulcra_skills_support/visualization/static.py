"""Static visualization using matplotlib and contextily"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Union

import matplotlib.pyplot as plt
import matplotlib.figure
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection

import contextily as ctx

from ..utils.geo import bounds_from_locations


def _to_web_mercator(
    lat: Union[np.ndarray, list],
    lon: Union[np.ndarray, list],
) -> tuple[np.ndarray, np.ndarray]:
    """Convert WGS84 lat/lon to Web Mercator (EPSG:3857)."""
    R = 6_378_137.0
    x = np.radians(np.asarray(lon, dtype=float)) * R
    y = np.log(np.tan(np.pi / 4 + np.radians(np.asarray(lat, dtype=float)) / 2)) * R
    return x, y


class StaticMapGenerator:
    """Generate static maps using matplotlib and contextily."""

    def __init__(self, max_px: int = 1200, map_style: str = "street", dpi: int = 200):
        self.max_px = max_px
        self.dpi = dpi
        # width/height kept for API compatibility
        self.width = max_px
        self.height = max_px
        # map_style kept for API compatibility; currently always OSM Mapnik

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def daily_path_static(self, locations_df: pd.DataFrame,
                          **options) -> matplotlib.figure.Figure:
        """Static trajectory map colored red→blue by time of day."""
        if locations_df.empty:
            return self._empty_map(options.get("title", "Daily Movement Path"))
        x_min, y_min, x_max, y_max, aspect = self._data_bounds_and_aspect(locations_df)
        fig, ax, _, _ = self._setup_figure(aspect)
        self._set_bounds(ax, x_min, y_min, x_max, y_max)
        self._add_colored_path(ax, locations_df)
        self._add_basemap(ax)
        self._finalize(ax, options.get("title", "Daily Movement Path"))
        return fig

    def daily_path_with_stays_static(self, locations_df: pd.DataFrame,
                                     stays: List[Dict],
                                     **options) -> matplotlib.figure.Figure:
        """Static trajectory map with numbered stay markers overlaid."""
        if locations_df.empty:
            return self._empty_map(options.get("title", "Daily Movement Path"))
        stays_sorted = sorted(stays, key=lambda s: s["entry_time"]) if stays else []
        x_min, y_min, x_max, y_max, aspect = self._data_bounds_and_aspect(locations_df)
        fig, ax, _, _ = self._setup_figure(aspect)
        self._set_bounds(ax, x_min, y_min, x_max, y_max)
        self._add_colored_path(ax, locations_df)
        if stays_sorted:
            self._add_stay_markers(ax, stays_sorted)
        self._add_basemap(ax)
        self._finalize(ax, options.get("title", "Daily Movement Path"))
        return fig

    def path_by_speed_static(self, locations_df: pd.DataFrame,
                             **options) -> matplotlib.figure.Figure:
        """Static trajectory map colored by speed."""
        if locations_df.empty:
            return self._empty_map(options.get("title", "Movement Speed"))

        speed_col = next(
            (c for c in ("calculated_speed_mps", "speed") if c in locations_df.columns),
            None,
        )
        if speed_col is None:
            return self.daily_path_static(locations_df, **options)

        x_min, y_min, x_max, y_max, aspect = self._data_bounds_and_aspect(locations_df)
        fig, ax, _, _ = self._setup_figure(aspect)
        self._set_bounds(ax, x_min, y_min, x_max, y_max)
        x, y = _to_web_mercator(locations_df["lat"].values, locations_df["lon"].values)
        speed = locations_df[speed_col].fillna(0).values
        max_speed = np.quantile(speed, 0.95) or 1.0

        points = np.array([x, y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        seg_speed = (speed[:-1] + speed[1:]) / 2

        lc = LineCollection(segments, cmap="RdYlGn_r",
                            norm=plt.Normalize(0, max_speed), linewidth=2.5, zorder=3)
        lc.set_array(seg_speed)
        ax.add_collection(lc)
        cbar = plt.colorbar(lc, ax=ax, fraction=0.02, pad=0.01, aspect=30)
        cbar.set_label("Speed (m/s)", fontsize=8)
        cbar.ax.tick_params(labelsize=7)

        self._add_basemap(ax)
        self._finalize(ax, options.get("title", "Movement Speed"))
        return fig

    def stays_heatmap_static(self, stays_data: List[Dict],
                             **options) -> matplotlib.figure.Figure:
        """Static map with stay locations as circles sized by duration."""
        if not stays_data:
            return self._empty_map(options.get("title", "Stay Locations"))

        stays_df = pd.DataFrame(stays_data)
        lat_col = "centroid_lat" if "centroid_lat" in stays_df.columns else "lat"
        lon_col = "centroid_lon" if "centroid_lon" in stays_df.columns else "lon"

        loc_df = pd.DataFrame({"lat": stays_df[lat_col], "lon": stays_df[lon_col]})
        x_min, y_min, x_max, y_max, aspect = self._data_bounds_and_aspect(loc_df)
        fig, ax, _, _ = self._setup_figure(aspect)
        self._set_bounds(ax, x_min, y_min, x_max, y_max)
        x, y = _to_web_mercator(stays_df[lat_col].values, stays_df[lon_col].values)
        durations = stays_df["duration_seconds"].values
        sizes = durations / durations.max() * 300 + 50

        sc = ax.scatter(x, y, s=sizes, c=durations, cmap="Reds", alpha=0.75, zorder=3,
                        edgecolors="white", linewidths=0.5)
        cbar = plt.colorbar(sc, ax=ax, fraction=0.02, pad=0.01, aspect=30)
        cbar.set_label("Duration (s)", fontsize=8)
        cbar.ax.tick_params(labelsize=7)

        self._add_basemap(ax)
        self._finalize(ax, options.get("title", "Stay Locations"))
        return fig

    def save_static_map(self, fig: matplotlib.figure.Figure,
                        filepath: Union[str, Path],
                        format: str = "png", **kwargs) -> None:
        """Save figure to disk and close it."""
        fig.savefig(filepath, format=format, dpi=self.dpi,
                    bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _setup_figure(self, aspect: float = 1.0):
        """Create figure sized to fit data aspect ratio within max_px."""
        if aspect >= 1.0:
            w_px, h_px = self.max_px, int(self.max_px / aspect)
        else:
            w_px, h_px = int(self.max_px * aspect), self.max_px
        fig, ax = plt.subplots(
            figsize=(w_px / self.dpi, h_px / self.dpi), dpi=self.dpi
        )
        fig.patch.set_facecolor("#606060")
        ax.set_facecolor("#606060")
        ax.set_axis_off()
        return fig, ax, w_px, h_px

    def _add_colored_path(self, ax, locations_df: pd.DataFrame) -> None:
        x, y = _to_web_mercator(locations_df["lat"].values, locations_df["lon"].values)

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
            norm_vals = np.linspace(0, 1, len(x))

        # Fit a smoothing spline and resample at 10× density so
        # straight 5-minute GPS segments become smooth curves.
        try:
            from scipy.interpolate import splprep, splev
            u = np.linspace(0, 1, len(x))
            tck, u_fit = splprep([x, y], u=u, s=len(x) * 1e6, k=3)
            u_dense = np.linspace(0, 1, len(x) * 10)
            x, y = splev(u_dense, tck)
            norm_vals = np.interp(u_dense, u, norm_vals)
        except Exception:
            pass  # fall back to raw points if scipy unavailable

        points = np.array([x, y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        seg_colors = (norm_vals[:-1] + norm_vals[1:]) / 2

        cmap = LinearSegmentedColormap.from_list("glow_br", ["#00BFFF", "#FF4500"])
        norm = plt.Normalize(0, 1)

        # Glow effect: draw the path several times, wider and more transparent
        # each pass outward. The overlap creates a neon halo.
        for lw, alpha in [(16, 0.03), (10, 0.06), (6, 0.12), (3.5, 0.4)]:
            glow = LineCollection(segments, cmap=cmap, norm=norm,
                                  linewidth=lw, alpha=alpha, zorder=3)
            glow.set_array(seg_colors)
            ax.add_collection(glow)

        # Core line — bright and opaque
        core = LineCollection(segments, cmap=cmap, norm=norm,
                              linewidth=1.8, alpha=1.0, zorder=4)
        core.set_array(seg_colors)
        ax.add_collection(core)

        cbar = plt.colorbar(core, ax=ax, fraction=0.02, pad=0.01, aspect=30)
        cbar.set_ticks([0, 1])
        cbar.set_ticklabels(["Start", "End"])
        cbar.ax.tick_params(labelsize=8, colors="white")
        cbar.outline.set_edgecolor("white")

    def _add_stay_markers(self, ax, stays_sorted: List[Dict]) -> None:
        for i, stay in enumerate(stays_sorted, 1):
            mx, my = _to_web_mercator(
                [stay["centroid_lat"]], [stay["centroid_lon"]]
            )
            # Outer glow ring
            ax.plot(mx[0], my[0], "o", color="white", markersize=22,
                    alpha=0.15, zorder=5)
            # Filled circle
            ax.plot(mx[0], my[0], "o", color="#FF4500", markersize=16,
                    zorder=6, markeredgecolor="white", markeredgewidth=1.5)
            ax.text(mx[0], my[0], str(i), ha="center", va="center",
                    color="white", fontsize=9, fontweight="bold", zorder=7)

    def _data_bounds_and_aspect(self, locations_df: pd.DataFrame):
        """Return (x_min, y_min, x_max, y_max, aspect) in EPSG:3857 with 5% padding."""
        min_lat = float(locations_df['lat'].min())
        max_lat = float(locations_df['lat'].max())
        min_lon = float(locations_df['lon'].min())
        max_lon = float(locations_df['lon'].max())

        x_min, y_min = _to_web_mercator([min_lat], [min_lon])
        x_max, y_max = _to_web_mercator([max_lat], [max_lon])
        x_min, x_max = float(x_min[0]), float(x_max[0])
        y_min, y_max = float(y_min[0]), float(y_max[0])

        x_pad = (x_max - x_min) * 0.05
        y_pad = (y_max - y_min) * 0.05
        x_min -= x_pad; x_max += x_pad
        y_min -= y_pad; y_max += y_pad

        x_span = x_max - x_min
        y_span = y_max - y_min
        # Cap aspect to a reasonable portrait/landscape range
        aspect = max(0.4, min(2.5, x_span / y_span))
        return x_min, y_min, x_max, y_max, aspect

    def _set_bounds(self, ax, x_min, y_min, x_max, y_max) -> None:
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)

    def _add_basemap(self, ax) -> None:
        ctx.add_basemap(ax, crs="EPSG:3857",
                        source=ctx.providers.OpenStreetMap.Mapnik,
                        zoom="auto", alpha=0.4)

    def _finalize(self, ax, title: str) -> None:
        ax.set_title(title, fontsize=11, pad=6, color="white")

    def _empty_map(self, title: str = "No Data") -> matplotlib.figure.Figure:
        fig, ax = plt.subplots(
            figsize=(self.width / self.dpi, self.height / self.dpi), dpi=self.dpi
        )
        ax.text(0.5, 0.5, "No location data available",
                ha="center", va="center", transform=ax.transAxes, fontsize=12)
        ax.set_title(title)
        ax.set_axis_off()
        return fig
