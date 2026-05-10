"""Tests for stay detection functionality"""

import datetime
import pytest
import pandas as pd

from fulcra_skills_support.stay_detection import StayDetector, Observation, Stay


class TestStayDetector:
    """Test cases for StayDetector class"""
    
    def test_empty_observations(self):
        """Test stay detection with empty observation list"""
        detector = StayDetector()
        stays, debug_df = detector.detect_stays([])
        
        assert len(stays) == 0
        assert debug_df.empty
    
    def test_single_observation(self):
        """Test stay detection with single observation"""
        detector = StayDetector()
        obs = [Observation(t=1000.0, lat=37.7749, lon=-122.4194)]
        
        stays, debug_df = detector.detect_stays(obs)
        
        assert len(stays) == 0  # Single point can't form a stay
        assert len(debug_df) == 1
    
    def test_stationary_points(self):
        """Test detection of clear stationary period"""
        detector = StayDetector(T_MIN=60)  # 1 minute minimum
        
        # Create 10 minutes of stationary points (1 point per minute)
        base_time = 1000.0
        observations = []
        
        for i in range(10):
            obs = Observation(
                t=base_time + i * 60,  # 1 minute intervals
                lat=37.7749 + (i * 0.0001),  # Very small movements
                lon=-122.4194 + (i * 0.0001),
                speed=0.1  # Very slow
            )
            observations.append(obs)
        
        stays, debug_df = detector.detect_stays(observations)
        
        assert len(stays) >= 1
        assert stays[0].duration >= 60  # At least 1 minute
        assert abs(stays[0].lat - 37.7749) < 0.01  # Near original location
        assert abs(stays[0].lon - (-122.4194)) < 0.01
    
    def test_moving_points(self):
        """Test that moving points don't create stays"""
        detector = StayDetector()
        
        # Create points moving in a line
        base_time = 1000.0
        observations = []
        
        for i in range(10):
            obs = Observation(
                t=base_time + i * 60,
                lat=37.7749 + i * 0.01,  # Moving significantly
                lon=-122.4194 + i * 0.01,
                speed=5.0  # Fast movement
            )
            observations.append(obs)
        
        stays, debug_df = detector.detect_stays(observations)
        
        assert len(stays) == 0  # No stays should be detected
    
    def test_custom_parameters(self):
        """Test that custom parameters affect detection"""
        # Very strict detector (large spatial threshold)
        strict_detector = StayDetector(R_SOFT=10, T_MIN=300)
        
        # Lenient detector
        lenient_detector = StayDetector(R_SOFT=100, T_MIN=30)
        
        # Create marginal case - moderate movement over time
        base_time = 1000.0
        observations = []
        
        for i in range(10):
            obs = Observation(
                t=base_time + i * 60,
                lat=37.7749 + i * 0.001,  # Small movements
                lon=-122.4194 + i * 0.001,
                speed=0.5
            )
            observations.append(obs)
        
        strict_stays, _ = strict_detector.detect_stays(observations)
        lenient_stays, _ = lenient_detector.detect_stays(observations)
        
        # Lenient detector should find more/longer stays
        assert len(lenient_stays) >= len(strict_stays)


class TestObservation:
    """Test cases for Observation dataclass"""
    
    def test_observation_creation(self):
        """Test creating observation with required fields"""
        obs = Observation(t=1000.0, lat=37.7749, lon=-122.4194)
        
        assert obs.t == 1000.0
        assert obs.lat == 37.7749
        assert obs.lon == -122.4194
        assert obs.speed is None
        assert obs.heading is None
    
    def test_observation_with_optional_fields(self):
        """Test creating observation with all fields"""
        obs = Observation(
            t=1000.0, 
            lat=37.7749, 
            lon=-122.4194,
            speed=2.5,
            heading=180.0
        )
        
        assert obs.speed == 2.5
        assert obs.heading == 180.0


class TestStay:
    """Test cases for Stay dataclass"""
    
    def test_stay_duration_calculation(self):
        """Test that Stay.duration property works correctly"""
        stay = Stay(
            lat=37.7749,
            lon=-122.4194,
            t_in=1000.0,
            t_out=1300.0,  # 5 minutes later
            n_points=10
        )
        
        assert stay.duration == 300.0  # 5 minutes in seconds
    
    def test_stay_creation(self):
        """Test creating Stay with all required fields"""
        stay = Stay(
            lat=37.7749,
            lon=-122.4194,
            t_in=1000.0,
            t_out=1300.0,
            n_points=10
        )
        
        assert stay.lat == 37.7749
        assert stay.lon == -122.4194
        assert stay.t_in == 1000.0
        assert stay.t_out == 1300.0
        assert stay.n_points == 10