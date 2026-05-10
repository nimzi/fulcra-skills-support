"""
Fulcra Skills Support Library

Python library for visualizing GPS location data from the Fulcra API with both 
static and interactive maps. Designed to be the foundation for Fulcra-related 
agent skills.
"""

__version__ = "0.1.0"

from .core import FulcraVisualizer
from .auth import TokenData, FulcraAuthError
from .stay_detection import StayDetector, Stay, Observation

__all__ = [
    "FulcraVisualizer",
    "TokenData", 
    "FulcraAuthError",
    "StayDetector",
    "Stay",
    "Observation",
]