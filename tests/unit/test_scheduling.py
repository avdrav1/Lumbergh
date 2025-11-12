"""Unit tests for helpers/scheduling.py time parsing and scheduling logic."""
import pytest
from datetime import time, datetime
from freezegun import freeze_time

from helpers.scheduling import (
    parse_time_string,
    get_server_datetime,
    get_server_date,
    get_server_time,
    should_post_now,
    should_post_today
)


class TestParseTimeString:
    """Tests for parse_time_string function."""

    def test_valid_formats(self):
        """Test parsing valid time strings."""
        assert parse_time_string("09:00") == time(9, 0)
        assert parse_time_string("14:30") == time(14, 30)
        assert parse_time_string("00:00") == time(0, 0)
        assert parse_time_string("23:59") == time(23, 59)
        assert parse_time_string("0:00") == time(0, 0)
        assert parse_time_string("9:05") == time(9, 5)

    def test_with_whitespace(self):
        """Test parsing with surrounding whitespace."""
        assert parse_time_string("  09:00  ") == time(9, 0)
        assert parse_time_string("\t14:30\n") == time(14, 30)

    def test_invalid_formats(self):
        """Test that invalid formats return None."""
        assert parse_time_string("25:00") is None
        assert parse_time_string("12:60") is None
        assert parse_time_string("abc") is None
        assert parse_time_string("") is None
        assert parse_time_string("12") is None
        assert parse_time_string("12:") is None
        assert parse_time_string(":30") is None
        assert parse_time_string("9:70") is None
        assert parse_time_string("24:00") is None

    def test_edge_cases(self):
        """Test boundary values."""
        # Valid boundaries
        assert parse_time_string("23:59") == time(23, 59)
        assert parse_time_string("00:00") == time(0, 0)

        # Invalid boundaries
        assert parse_time_string("24:00") is None
        assert parse_time_string("23:60") is None


class TestTimezoneConversions:
    """Tests for timezone conversion functions."""

    @freeze_time("2025-01-15 14:00:00")  # 2pm UTC
    def test_get_server_datetime_utc(self):
        """Test getting server datetime with UTC timezone."""
        result = get_server_datetime(0)
        assert result.hour == 14
        assert result.minute == 0

    @freeze_time("2025-01-15 14:00:00")  # 2pm UTC
    def test_get_server_datetime_est(self):
        """Test getting server datetime with EST timezone (-5)."""
        result = get_server_datetime(-5)
        assert result.hour == 9
        assert result.minute == 0

    @freeze_time("2025-01-15 14:00:00")  # 2pm UTC
    def test_get_server_datetime_jst(self):
        """Test getting server datetime with JST timezone (+9)."""
        result = get_server_datetime(9)
        assert result.hour == 23
        assert result.minute == 0

    @freeze_time("2025-01-15 14:00:00")  # 2pm UTC
    def test_get_server_datetime_edge_timezones(self):
        """Test edge case timezones."""
        # Maximum positive offset
        result = get_server_datetime(14)
        assert result.hour == 4
        assert result.day == 16  # Next day

        # Maximum negative offset
        result = get_server_datetime(-12)
        assert result.hour == 2
        assert result.day == 15  # Same day

    @freeze_time("2025-01-15 14:30:00")
    def test_get_server_date(self):
        """Test getting server date string."""
        assert get_server_date(0) == "2025-01-15"
        assert get_server_date(-5) == "2025-01-15"

    @freeze_time("2025-01-15 23:30:00")  # 11:30pm UTC
    def test_get_server_date_crosses_midnight(self):
        """Test date when crossing midnight with timezone offset."""
        # UTC is 11:30pm on Jan 15
        assert get_server_date(0) == "2025-01-15"

        # JST (+9) would be 8:30am on Jan 16
        assert get_server_date(9) == "2025-01-16"

        # EST (-5) would be 6:30pm on Jan 15
        assert get_server_date(-5) == "2025-01-15"

    @freeze_time("2025-01-15 14:30:45")
    def test_get_server_time(self):
        """Test getting server time object."""
        result = get_server_time(0)
        assert result.hour == 14
        assert result.minute == 30

        result = get_server_time(-5)
        assert result.hour == 9
        assert result.minute == 30


class TestShouldPostNow:
    """Tests for should_post_now function."""

    @freeze_time("2025-01-15 14:00:00")  # 2pm UTC = 9am EST
    def test_exactly_on_target_time(self):
        """Test when current time exactly matches target."""
        target = time(9, 0)
        assert should_post_now(target, -5, window_minutes=15) is True

    @freeze_time("2025-01-15 14:07:00")  # 2:07pm UTC = 9:07am EST
    def test_within_window_after_target(self):
        """Test when current time is within window after target."""
        target = time(9, 0)
        assert should_post_now(target, -5, window_minutes=15) is True

    @freeze_time("2025-01-15 13:55:00")  # 1:55pm UTC = 8:55am EST
    def test_within_window_before_target(self):
        """Test when current time is within window before target."""
        target = time(9, 0)
        assert should_post_now(target, -5, window_minutes=15) is True

    @freeze_time("2025-01-15 14:20:00")  # 2:20pm UTC = 9:20am EST
    def test_outside_window_after(self):
        """Test when current time is outside window after target."""
        target = time(9, 0)
        assert should_post_now(target, -5, window_minutes=15) is False

    @freeze_time("2025-01-15 13:40:00")  # 1:40pm UTC = 8:40am EST
    def test_outside_window_before(self):
        """Test when current time is outside window before target."""
        target = time(9, 0)
        assert should_post_now(target, -5, window_minutes=15) is False

    @freeze_time("2025-01-15 14:15:00")  # 2:15pm UTC = 9:15am EST
    def test_exactly_at_window_edge(self):
        """Test when current time is exactly at window edge."""
        target = time(9, 0)
        # At exactly 15 minutes after, should still be True
        assert should_post_now(target, -5, window_minutes=15) is True

    @freeze_time("2025-01-15 05:00:00")  # 5am UTC = midnight EST
    def test_midnight_target(self):
        """Test posting at midnight."""
        target = time(0, 0)
        assert should_post_now(target, -5, window_minutes=15) is True

    @freeze_time("2025-01-15 14:00:00")  # 2pm UTC = 9am EST
    def test_custom_window_size(self):
        """Test with different window sizes."""
        target = time(9, 0)

        # 5 minute window
        assert should_post_now(target, -5, window_minutes=5) is True

        # 30 minute window
        assert should_post_now(target, -5, window_minutes=30) is True

    @freeze_time("2025-01-15 14:10:00")  # 2:10pm UTC = 9:10am EST
    def test_small_window(self):
        """Test with smaller window."""
        target = time(9, 0)

        # 5 minute window - 10 minutes after target
        assert should_post_now(target, -5, window_minutes=5) is False

        # 15 minute window - 10 minutes after target
        assert should_post_now(target, -5, window_minutes=15) is True


class TestShouldPostToday:
    """Tests for should_post_today function."""

    @freeze_time("2025-01-15 14:00:00")
    def test_never_posted_before(self):
        """Test when never posted before (None)."""
        assert should_post_today(None, 0) is True
        assert should_post_today(None, -5) is True

    @freeze_time("2025-01-15 14:00:00")  # Jan 15, 2025
    def test_posted_yesterday(self):
        """Test when last posted was yesterday."""
        assert should_post_today("2025-01-14", 0) is True

    @freeze_time("2025-01-15 14:00:00")  # Jan 15, 2025
    def test_already_posted_today(self):
        """Test when already posted today."""
        assert should_post_today("2025-01-15", 0) is False

    @freeze_time("2025-01-15 23:30:00")  # 11:30pm UTC on Jan 15
    def test_with_timezone_same_day(self):
        """Test timezone doesn't change date."""
        # EST (-5) is still Jan 15 at 6:30pm
        assert should_post_today("2025-01-15", -5) is False
        assert should_post_today("2025-01-14", -5) is True

    @freeze_time("2025-01-15 04:00:00")  # 4am UTC on Jan 15
    def test_with_timezone_previous_day(self):
        """Test timezone puts us in previous day."""
        # EST (-5) is 11pm on Jan 14
        assert should_post_today("2025-01-14", -5) is False
        assert should_post_today("2025-01-13", -5) is True

    @freeze_time("2025-01-15 20:00:00")  # 8pm UTC on Jan 15
    def test_with_timezone_next_day(self):
        """Test timezone puts us in next day."""
        # JST (+9) is 5am on Jan 16
        assert should_post_today("2025-01-16", 9) is False
        assert should_post_today("2025-01-15", 9) is True

    @freeze_time("2025-01-15 14:00:00")
    def test_posted_long_ago(self):
        """Test when last post was weeks ago."""
        assert should_post_today("2025-01-01", 0) is True
        assert should_post_today("2024-12-25", 0) is True
