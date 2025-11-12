"""
Scheduling utilities for Discord bot daily tasks.

This module provides utilities for managing daily scheduled tasks,
including time parsing, timezone conversions, and posting window checks.
"""

import re
from datetime import datetime, time, timedelta
from typing import Optional


def parse_time_string(time_str: str) -> Optional[time]:
    """
    Parse time string in HH:MM format (24-hour).

    Args:
        time_str: Time string in format "HH:MM" (e.g., "09:00", "14:30")

    Returns:
        time object if parsing succeeds, None otherwise

    Examples:
        >>> parse_time_string("09:00")
        datetime.time(9, 0)
        >>> parse_time_string("23:59")
        datetime.time(23, 59)
        >>> parse_time_string("invalid")
        None
    """
    time_str = time_str.strip()
    pattern = r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$'
    match = re.match(pattern, time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        return time(hour, minute)
    return None


def get_server_datetime(timezone_offset: int) -> datetime:
    """
    Get current datetime for a server's timezone.

    Args:
        timezone_offset: Hours offset from UTC (e.g., -5 for EST, 0 for UTC, +9 for JST)

    Returns:
        Current datetime adjusted for the server's timezone
    """
    utc_now = datetime.utcnow()
    server_datetime = utc_now + timedelta(hours=timezone_offset)
    return server_datetime


def get_server_date(timezone_offset: int) -> str:
    """
    Get current date string for a server's timezone.

    Args:
        timezone_offset: Hours offset from UTC

    Returns:
        Date string in format "YYYY-MM-DD"
    """
    server_datetime = get_server_datetime(timezone_offset)
    return server_datetime.strftime("%Y-%m-%d")


def get_server_time(timezone_offset: int) -> time:
    """
    Get current time for a server's timezone.

    Args:
        timezone_offset: Hours offset from UTC

    Returns:
        time object representing current time in server's timezone
    """
    server_datetime = get_server_datetime(timezone_offset)
    return server_datetime.time()


def should_post_now(
    target_time: time,
    timezone_offset: int,
    window_minutes: int = 15
) -> bool:
    """
    Check if current time is within posting window of target time.

    This function checks if the current time (in the server's timezone)
    is within ±window_minutes of the target posting time.

    Args:
        target_time: The scheduled posting time
        timezone_offset: Hours offset from UTC for the server
        window_minutes: Size of the posting window in minutes (default: 15)

    Returns:
        True if current time is within the posting window, False otherwise

    Example:
        If target_time is 09:00 and window_minutes is 15:
        - Returns True if current time is between 08:45 and 09:15
        - Returns False otherwise
    """
    current_time = get_server_time(timezone_offset)

    # Convert both times to datetime objects for comparison
    # Use a fixed date since we only care about time difference
    today = datetime.today()
    target_datetime = datetime.combine(today, target_time)
    current_datetime = datetime.combine(today, current_time)

    # Calculate difference in minutes
    time_diff_minutes = abs((current_datetime - target_datetime).total_seconds() / 60)

    return time_diff_minutes <= window_minutes


def should_post_today(
    last_post_date: Optional[str],
    timezone_offset: int
) -> bool:
    """
    Check if we should post today (haven't posted yet today).

    Args:
        last_post_date: The date of the last post (format: "YYYY-MM-DD"), or None
        timezone_offset: Hours offset from UTC for the server

    Returns:
        True if we should post (last_post_date is not today), False otherwise
    """
    if last_post_date is None:
        return True

    current_date = get_server_date(timezone_offset)
    return last_post_date != current_date
