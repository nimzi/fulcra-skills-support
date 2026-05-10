"""
GPS stay-detection algorithm.

Implements the 7-stage pipeline from stay_detection.tex:
  1. Preprocessing (gap detection)
  2. Availability router (α_vel, α_hdg)
  3. Channel scores (spatial, velocity, heading)
  4. Adaptive fusion
  5. Gaussian temporal smoothing
  6. Three-state FSM (MOVING / CANDIDATE / STAY)
  7. Centroid maintenance + post-processing (merge, filter)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from math import asin, cos, radians, sin, sqrt
from typing import Optional, List, Tuple

import numpy as np
import pandas as pd


# Default parameters from research paper
DEFAULT_PARAMS = {
    "R_SOFT": 50.0,        # spatial Gaussian σ (metres)
    "V0": 0.5,             # velocity Gaussian σ (m/s) 
    "W_P": 1.0,            # fusion weight: position
    "W_V": 0.8,            # fusion weight: velocity
    "W_H": 0.6,            # fusion weight: heading
    "TAU_ENTER": 0.6,      # FSM: enter CANDIDATE / stay in STAY threshold
    "TAU_EXIT": 0.35,      # FSM: exit CANDIDATE / STAY threshold (hysteresis)
    "T_MIN": 120.0,        # minimum stay duration (seconds)
    "N_EXIT": 3,           # consecutive sub-threshold readings to leave STAY
    "T_GAP": 600.0,        # data gap that forces a state reset (seconds)
    "TAU_SMOOTH": 15.0,    # Gaussian smoothing kernel σ (seconds)
    "DT_W": 30.0,          # heading window half-width (seconds) 
    "K_MIN": 3,            # minimum heading window occupancy for heading channel
    "R_MAX": 100.0,        # maximum candidate cluster radius (metres)
    "R_MERGE": 75.0,       # post-processing: merge centroid distance (metres)
    "T_MERGE": 300.0,      # post-processing: merge time-gap threshold (seconds)
}


@dataclass
class Observation:
    """One location sample."""
    t: float                          # POSIX timestamp (seconds)
    lat: float                        # latitude (degrees)  
    lon: float                        # longitude (degrees)
    speed: Optional[float] = None     # m/s; None = unavailable
    heading: Optional[float] = None   # compass degrees 0–360; None = unavailable


@dataclass 
class Stay:
    """A detected stay (dwell period)."""
    lat: float       # weighted centroid latitude
    lon: float       # weighted centroid longitude
    t_in: float      # entry timestamp (POSIX seconds)
    t_out: float     # exit timestamp (POSIX seconds) 
    n_points: int    # number of constituent observations

    @property
    def duration(self) -> float:
        """Stay duration in seconds"""
        return self.t_out - self.t_in


class _State(Enum):
    MOVING = auto()
    CANDIDATE = auto()  
    STAY = auto()


class StayDetector:
    """GPS stay detection using multi-channel scoring and finite state machine"""
    
    def __init__(self, **params):
        """Initialize with custom parameters (uses defaults for unspecified params)"""
        self.params = DEFAULT_PARAMS.copy()
        self.params.update(params)
    
    def detect_stays(self, observations: List[Observation]) -> Tuple[List[Stay], pd.DataFrame]:
        """
        Run the full stay-detection pipeline on a time-sorted observation list.

        Parameters
        ----------
        observations:
            Time-sorted list of Observation objects. Must be sorted ascending by t.

        Returns
        -------
        stays:
            Post-processed Stay records (merged nearby consecutive stays, short
            stays removed).
        debug:
            DataFrame with per-observation diagnostics:
            t, lat, lon, sigma_raw, sigma_smooth, state
        """
        if not observations:
            return [], pd.DataFrame(
                columns=["t", "lat", "lon", "sigma_raw", "sigma_smooth", "state"]
            )

        n = len(observations)
        times = np.array([o.t for o in observations], dtype=float)
        lats = np.array([o.lat for o in observations], dtype=float)
        lons = np.array([o.lon for o in observations], dtype=float)

        # Build heading windows using two-pointer sliding window
        heading_windows = self._build_heading_windows(observations, times)
        
        # Pass 1: raw fused scores with rolling centroid
        sigma_raw = self._compute_raw_scores(observations, times, lats, lons, heading_windows)
        
        # Pass 2: Gaussian temporal smoothing
        sigma_smooth = self._gaussian_smooth(times, sigma_raw)
        
        # Pass 3: three-state FSM
        raw_stays, state_labels = self._run_fsm(times, lats, lons, sigma_smooth)
        
        # Post-processing
        stays = self._merge_stays(raw_stays)
        stays = self._filter_short(stays)

        debug = pd.DataFrame({
            "t": times,
            "lat": lats,
            "lon": lons,
            "sigma_raw": sigma_raw,
            "sigma_smooth": sigma_smooth,
            "state": state_labels,
        })

        return stays, debug
    
    def _build_heading_windows(self, observations: List[Observation], times: np.ndarray) -> List[List[float]]:
        """Build heading windows using two-pointer sliding window"""
        n = len(observations)
        heading_windows: List[List[float]] = []
        lo_h = 0
        hi_h = 0
        
        for i in range(n):
            # Drop left side of window
            while lo_h < i and (times[i] - times[lo_h]) > self.params["DT_W"]:
                lo_h += 1
            # Extend right side of window  
            while hi_h + 1 < n and (times[hi_h + 1] - times[i]) <= self.params["DT_W"]:
                hi_h += 1
            win = [
                observations[j].heading
                for j in range(lo_h, hi_h + 1)
                if observations[j].heading is not None
            ]
            heading_windows.append(win)
            
        return heading_windows
    
    def _compute_raw_scores(self, observations: List[Observation], times: np.ndarray, 
                          lats: np.ndarray, lons: np.ndarray, 
                          heading_windows: List[List[float]]) -> np.ndarray:
        """Compute raw fused scores with rolling centroid"""
        n = len(observations)
        centroid_lat, centroid_lon = lats[0], lons[0]
        sigma_raw = np.empty(n)

        for i in range(n):
            # Gap reset: new segment starts with centroid at current position
            if i > 0 and (times[i] - times[i - 1]) > self.params["T_GAP"]:
                centroid_lat, centroid_lon = lats[i], lons[i]

            d = haversine(lats[i], lons[i], centroid_lat, centroid_lon)
            sigma_raw[i] = self._fused_score(d, observations[i].speed, heading_windows[i])

            # Update centroid: pull toward current point proportional to score
            w = sigma_raw[i]
            centroid_lat = (1.0 - w) * centroid_lat + w * lats[i]
            centroid_lon = (1.0 - w) * centroid_lon + w * lons[i]
            
        return sigma_raw
    
    def _fused_score(self, d: float, speed: Optional[float], heading_window: List[float]) -> float:
        """Adaptive weighted fusion of spatial, velocity, and heading scores."""
        s_pos = float(np.exp(-0.5 * (d / self.params["R_SOFT"]) ** 2))

        alpha_vel = speed is not None
        alpha_hdg = len(heading_window) >= self.params["K_MIN"]

        s_vel = float(np.exp(-0.5 * (speed / self.params["V0"]) ** 2)) if alpha_vel else 0.0
        s_hdg = 1.0 - self._mean_resultant_length(heading_window) if alpha_hdg else 0.0

        num = (self.params["W_P"] * s_pos + 
               self.params["W_V"] * int(alpha_vel) * s_vel + 
               self.params["W_H"] * int(alpha_hdg) * s_hdg)
        den = (self.params["W_P"] + 
               self.params["W_V"] * int(alpha_vel) + 
               self.params["W_H"] * int(alpha_hdg))
        return num / den
    
    def _mean_resultant_length(self, headings: List[float]) -> float:
        """Circular concentration of heading angles (0 = scattered, 1 = aligned)."""
        if not headings:
            return 0.0
        zs = [complex(cos(radians(h)), sin(radians(h))) for h in headings]
        return abs(sum(zs) / len(zs))
    
    def _gaussian_smooth(self, times: np.ndarray, scores: np.ndarray) -> np.ndarray:
        """Apply symmetric Gaussian kernel to scores, truncated at 3τ."""
        cutoff = 3.0 * self.params["TAU_SMOOTH"]
        n = len(times)
        result = np.empty_like(scores)
        lo = 0
        hi = 0
        
        for i in range(n):
            # Advance lo: drop points that have fallen behind the left edge
            while lo < i and (times[i] - times[lo]) > cutoff:
                lo += 1
            # Advance hi: include points that have entered the right edge
            while hi + 1 < n and (times[hi + 1] - times[i]) <= cutoff:
                hi += 1
            window_t = times[lo : hi + 1]
            window_s = scores[lo : hi + 1]
            w = np.exp(-0.5 * ((window_t - times[i]) / self.params["TAU_SMOOTH"]) ** 2)
            result[i] = (w * window_s).sum() / w.sum()
            
        return result
    
    def _run_fsm(self, times: np.ndarray, lats: np.ndarray, lons: np.ndarray, 
                sigma_smooth: np.ndarray) -> Tuple[List[Stay], List[str]]:
        """Run three-state finite state machine"""
        n = len(times)
        state = _State.MOVING
        state_labels: List[str] = ["MOVING"] * n

        # Cluster accumulators (weighted centroid)
        w_sum = lat_sum = lon_sum = 0.0
        t_start = 0.0
        consec_low = 0
        cluster_n = 0
        raw_stays: List[Stay] = []

        def cluster_centroid() -> Tuple[float, float]:
            return lat_sum / w_sum, lon_sum / w_sum

        def finalize(t_out: float) -> None:
            nonlocal state, w_sum, lat_sum, lon_sum, consec_low, cluster_n
            if w_sum > 0:
                clat, clon = cluster_centroid()
                raw_stays.append(Stay(
                    lat=clat, lon=clon,
                    t_in=t_start, t_out=t_out,
                    n_points=cluster_n,
                ))
            state = _State.MOVING
            w_sum = lat_sum = lon_sum = 0.0
            consec_low = 0
            cluster_n = 0

        for i in range(n):
            # Gap reset
            if i > 0 and (times[i] - times[i - 1]) > self.params["T_GAP"]:
                if state in (_State.CANDIDATE, _State.STAY):
                    finalize(times[i - 1])

            sigma = sigma_smooth[i]

            if state == _State.MOVING:
                if sigma >= self.params["TAU_ENTER"]:
                    state = _State.CANDIDATE
                    t_start = times[i]
                    w_sum = sigma
                    lat_sum = sigma * lats[i]
                    lon_sum = sigma * lons[i]
                    cluster_n = 1
                    state_labels[i] = "CANDIDATE"
                else:
                    state_labels[i] = "MOVING"

            elif state == _State.CANDIDATE:
                clat, clon = cluster_centroid()
                d = haversine(lats[i], lons[i], clat, clon)
                if sigma < self.params["TAU_EXIT"] or d > self.params["R_MAX"]:
                    # Discard: not a stay
                    state = _State.MOVING
                    w_sum = lat_sum = lon_sum = 0.0
                    cluster_n = 0
                    state_labels[i] = "MOVING"
                else:
                    w_sum += sigma
                    lat_sum += sigma * lats[i]
                    lon_sum += sigma * lons[i]
                    cluster_n += 1
                    elapsed = times[i] - t_start
                    if elapsed >= self.params["T_MIN"]:
                        state = _State.STAY
                        state_labels[i] = "STAY"
                    else:
                        state_labels[i] = "CANDIDATE"

            elif state == _State.STAY:
                if sigma < self.params["TAU_EXIT"]:
                    consec_low += 1
                    state_labels[i] = "STAY"  # still labelled STAY until confirmed exit
                    if consec_low >= self.params["N_EXIT"]:
                        finalize(times[i])
                else:
                    consec_low = 0
                    w_sum += sigma
                    lat_sum += sigma * lats[i]
                    lon_sum += sigma * lons[i]
                    cluster_n += 1
                    state_labels[i] = "STAY"

        # Finalize any open stay at end of sequence
        if state in (_State.CANDIDATE, _State.STAY) and cluster_n > 0:
            finalize(times[-1])
            
        return raw_stays, state_labels
    
    def _merge_stays(self, stays: List[Stay]) -> List[Stay]:
        """Merge consecutive stays that are spatially and temporally close."""
        if not stays:
            return stays
        merged = [stays[0]]
        for s in stays[1:]:
            prev = merged[-1]
            d = haversine(prev.lat, prev.lon, s.lat, s.lon)
            gap = s.t_in - prev.t_out
            if d < self.params["R_MERGE"] and gap < self.params["T_MERGE"]:
                total = prev.n_points + s.n_points
                merged[-1] = Stay(
                    lat=(prev.lat * prev.n_points + s.lat * s.n_points) / total,
                    lon=(prev.lon * prev.n_points + s.lon * s.n_points) / total,
                    t_in=prev.t_in,
                    t_out=s.t_out,
                    n_points=total,
                )
            else:
                merged.append(s)
        return merged

    def _filter_short(self, stays: List[Stay], min_dur: Optional[float] = None) -> List[Stay]:
        """Remove stays shorter than min_dur seconds."""
        if min_dur is None:
            min_dur = self.params["T_MIN"]
        return [s for s in stays if s.duration >= min_dur]


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two (lat, lon) points."""
    R = 6_371_000.0
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlam = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlam / 2) ** 2
    return R * 2 * asin(sqrt(max(0.0, min(1.0, a))))


# Convenience function for backward compatibility
def detect_stays(observations: List[Observation]) -> Tuple[List[Stay], pd.DataFrame]:
    """Convenience function using default parameters"""
    detector = StayDetector()
    return detector.detect_stays(observations)