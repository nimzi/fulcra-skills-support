"""Color schemes for visualizations"""

from __future__ import annotations

from typing import Dict, List


class ColorSchemes:
    """Predefined color palettes for different visualization types."""

    @staticmethod
    def speed_gradient() -> List[str]:
        return [
            "#313695", "#4575b4", "#74add1", "#abd9e9", "#e0f3f8",
            "#fee090", "#fdae61", "#f46d43", "#d73027", "#a50026",
        ]

    @staticmethod
    def stay_duration() -> List[str]:
        return [
            "#fee5d9", "#fcbba1", "#fc9272", "#fb6a4a",
            "#ef3b2c", "#cb181d", "#99000d",
        ]

    @staticmethod
    def trajectory_default() -> str:
        return "#2E86AB"

    @staticmethod
    def stays_default() -> str:
        return "#F24236"

    @staticmethod
    def qualitative_colors() -> List[str]:
        return [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
            "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
            "#bcbd22", "#17becf",
        ]
