"""Time processing utility functions"""

from __future__ import annotations

import datetime
from typing import Tuple, Union

import pytz


def parse_date_string(date_str: Union[str, datetime.date, datetime.datetime]) -> datetime.date:
    """
    Parse various date formats to datetime.date object
    
    Parameters
    ----------
    date_str : str, datetime.date, or datetime.datetime
        Date in format 'YYYY-MM-DD', date object, or datetime object
        
    Returns
    -------
    datetime.date
        Parsed date object
    """
    if isinstance(date_str, datetime.date):
        return date_str
    elif isinstance(date_str, datetime.datetime):
        return date_str.date()
    elif isinstance(date_str, str):
        return datetime.date.fromisoformat(date_str)
    else:
        raise ValueError(f"Cannot parse date from {type(date_str)}: {date_str}")


def day_time_range(date: Union[str, datetime.date, datetime.datetime], 
                  timezone: str = "UTC") -> Tuple[datetime.datetime, datetime.datetime]:
    """
    Get start and end datetime for a full day in specified timezone
    
    Parameters
    ----------
    date : str, datetime.date, or datetime.datetime
        Target date
    timezone : str
        Timezone name (e.g., 'America/Los_Angeles', 'UTC')
        
    Returns
    -------
    tuple
        (start_time, end_time) as timezone-aware datetime objects
        start_time is 00:00:00, end_time is 23:59:59
    """
    date_obj = parse_date_string(date)
    tz = pytz.timezone(timezone)
    
    start_time = tz.localize(datetime.datetime(
        date_obj.year, date_obj.month, date_obj.day, 0, 0, 0
    ))
    end_time = tz.localize(datetime.datetime(
        date_obj.year, date_obj.month, date_obj.day, 23, 59, 59
    ))
    
    return start_time, end_time


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string
    
    Parameters
    ----------
    seconds : float
        Duration in seconds
        
    Returns
    -------
    str
        Formatted duration (e.g., "2h 30m", "45 min", "30 sec")
    """
    if seconds < 60:
        return f"{int(seconds)} sec"
    
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes} min"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if remaining_minutes == 0:
        return f"{hours}h"
    else:
        return f"{hours}h {remaining_minutes}m"


def format_time(timestamp: Union[float, datetime.datetime], 
               timezone: str = "UTC", 
               format_str: str = "%I:%M %p") -> str:
    """
    Format timestamp to human-readable time string
    
    Parameters
    ----------
    timestamp : float or datetime.datetime
        Unix timestamp or datetime object
    timezone : str
        Timezone for display
    format_str : str
        strftime format string
        
    Returns
    -------
    str
        Formatted time string
    """
    if isinstance(timestamp, (int, float)):
        dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
    else:
        dt = timestamp
        
    # Convert to target timezone
    if timezone != "UTC":
        tz = pytz.timezone(timezone)
        dt = dt.astimezone(tz)
    
    return dt.strftime(format_str)


def is_same_day(dt1: datetime.datetime, dt2: datetime.datetime, 
               timezone: str = "UTC") -> bool:
    """
    Check if two datetimes are on the same calendar day in given timezone
    
    Parameters
    ----------
    dt1, dt2 : datetime.datetime
        Datetime objects to compare
    timezone : str
        Timezone for comparison
        
    Returns
    -------
    bool
        True if same calendar day
    """
    tz = pytz.timezone(timezone)
    
    # Convert to target timezone
    local_dt1 = dt1.astimezone(tz)
    local_dt2 = dt2.astimezone(tz)
    
    return local_dt1.date() == local_dt2.date()


def time_of_day_category(timestamp: Union[float, datetime.datetime], 
                        timezone: str = "UTC") -> str:
    """
    Categorize time of day (morning, afternoon, evening, night)
    
    Parameters
    ----------
    timestamp : float or datetime.datetime
        Unix timestamp or datetime object
    timezone : str
        Timezone for categorization
        
    Returns
    -------
    str
        Category: "morning", "afternoon", "evening", or "night"
    """
    if isinstance(timestamp, (int, float)):
        dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
    else:
        dt = timestamp
        
    # Convert to target timezone
    if timezone != "UTC":
        tz = pytz.timezone(timezone)
        dt = dt.astimezone(tz)
    
    hour = dt.hour
    
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon" 
    elif 18 <= hour < 22:
        return "evening"
    else:
        return "night"