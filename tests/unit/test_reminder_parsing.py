"""Unit tests for reminders.py time parsing functions."""
import pytest
from datetime import time
from cogs.reminders import Reminders


@pytest.fixture
def reminders_cog(mock_bot):
    """Create a Reminders cog instance for testing."""
    return Reminders(mock_bot)


class TestParseTime:
    """Tests for parse_time function (interval parsing like 5m, 2h, 3d)."""

    def test_seconds(self, reminders_cog):
        """Test parsing seconds."""
        assert reminders_cog.parse_time("30s") == 30
        assert reminders_cog.parse_time("1s") == 1
        assert reminders_cog.parse_time("59s") == 59

    def test_minutes(self, reminders_cog):
        """Test parsing minutes."""
        assert reminders_cog.parse_time("5m") == 300  # 5 * 60
        assert reminders_cog.parse_time("1m") == 60
        assert reminders_cog.parse_time("30m") == 1800

    def test_hours(self, reminders_cog):
        """Test parsing hours."""
        assert reminders_cog.parse_time("1h") == 3600  # 60 * 60
        assert reminders_cog.parse_time("2h") == 7200
        assert reminders_cog.parse_time("24h") == 86400

    def test_days(self, reminders_cog):
        """Test parsing days."""
        assert reminders_cog.parse_time("1d") == 86400  # 24 * 60 * 60
        assert reminders_cog.parse_time("7d") == 604800

    def test_weeks(self, reminders_cog):
        """Test parsing weeks."""
        assert reminders_cog.parse_time("1w") == 604800  # 7 * 24 * 60 * 60
        assert reminders_cog.parse_time("2w") == 1209600

    def test_case_insensitive(self, reminders_cog):
        """Test that parsing is case insensitive."""
        assert reminders_cog.parse_time("5M") == 300
        assert reminders_cog.parse_time("2H") == 7200
        assert reminders_cog.parse_time("3D") == 259200

    def test_with_whitespace(self, reminders_cog):
        """Test parsing with surrounding whitespace."""
        assert reminders_cog.parse_time("  5m  ") == 300
        assert reminders_cog.parse_time("\t2h\n") == 7200

    def test_invalid_formats(self, reminders_cog):
        """Test that invalid formats return None."""
        assert reminders_cog.parse_time("5") is None
        assert reminders_cog.parse_time("m") is None
        assert reminders_cog.parse_time("5x") is None
        assert reminders_cog.parse_time("abc") is None
        assert reminders_cog.parse_time("") is None
        assert reminders_cog.parse_time("5 m") is None  # Space not allowed

    def test_zero_values(self, reminders_cog):
        """Test zero values."""
        assert reminders_cog.parse_time("0s") == 0
        assert reminders_cog.parse_time("0m") == 0

    def test_large_values(self, reminders_cog):
        """Test large values."""
        assert reminders_cog.parse_time("100d") == 8640000
        assert reminders_cog.parse_time("52w") == 31449600


class TestParseTimeOfDay:
    """Tests for parse_time_of_day function (clock times like 9:00am, 14:30)."""

    def test_am_pm_with_minutes(self, reminders_cog):
        """Test AM/PM format with minutes."""
        assert reminders_cog.parse_time_of_day("9:00 AM") == time(9, 0)
        assert reminders_cog.parse_time_of_day("2:30 PM") == time(14, 30)
        assert reminders_cog.parse_time_of_day("11:45 am") == time(11, 45)
        assert reminders_cog.parse_time_of_day("5:15 pm") == time(17, 15)

    def test_am_pm_without_space(self, reminders_cog):
        """Test AM/PM format without space."""
        assert reminders_cog.parse_time_of_day("9:00am") == time(9, 0)
        assert reminders_cog.parse_time_of_day("2:30pm") == time(14, 30)

    def test_am_pm_hour_only(self, reminders_cog):
        """Test AM/PM format with hour only (no minutes)."""
        assert reminders_cog.parse_time_of_day("9am") == time(9, 0)
        assert reminders_cog.parse_time_of_day("2pm") == time(14, 0)
        assert reminders_cog.parse_time_of_day("11AM") == time(11, 0)

    def test_midnight_and_noon(self, reminders_cog):
        """Test special cases: midnight (12am) and noon (12pm)."""
        assert reminders_cog.parse_time_of_day("12:00 AM") == time(0, 0)
        assert reminders_cog.parse_time_of_day("12:00 PM") == time(12, 0)
        assert reminders_cog.parse_time_of_day("12am") == time(0, 0)
        assert reminders_cog.parse_time_of_day("12pm") == time(12, 0)

    def test_24_hour_format(self, reminders_cog):
        """Test 24-hour format."""
        assert reminders_cog.parse_time_of_day("14:30") == time(14, 30)
        assert reminders_cog.parse_time_of_day("00:00") == time(0, 0)
        assert reminders_cog.parse_time_of_day("23:59") == time(23, 59)
        assert reminders_cog.parse_time_of_day("9:05") == time(9, 5)

    def test_24_hour_hour_only(self, reminders_cog):
        """Test 24-hour format with hour only."""
        assert reminders_cog.parse_time_of_day("14") == time(14, 0)
        assert reminders_cog.parse_time_of_day("0") == time(0, 0)
        assert reminders_cog.parse_time_of_day("23") == time(23, 0)

    def test_with_whitespace(self, reminders_cog):
        """Test parsing with whitespace."""
        assert reminders_cog.parse_time_of_day("  9:00 AM  ") == time(9, 0)
        assert reminders_cog.parse_time_of_day("  14:30  ") == time(14, 30)

    def test_invalid_hours(self, reminders_cog):
        """Test invalid hour values."""
        assert reminders_cog.parse_time_of_day("25:00") is None
        assert reminders_cog.parse_time_of_day("24:00") is None
        assert reminders_cog.parse_time_of_day("13:00 AM") is None
        assert reminders_cog.parse_time_of_day("0:00 PM") is None

    def test_invalid_minutes(self, reminders_cog):
        """Test invalid minute values."""
        assert reminders_cog.parse_time_of_day("9:60 AM") is None
        assert reminders_cog.parse_time_of_day("14:70") is None

    def test_invalid_formats(self, reminders_cog):
        """Test completely invalid formats."""
        assert reminders_cog.parse_time_of_day("abc") is None
        assert reminders_cog.parse_time_of_day("") is None
        assert reminders_cog.parse_time_of_day("9:") is None
        assert reminders_cog.parse_time_of_day(":30") is None


class TestParseSchedulePattern:
    """Tests for parse_schedule_pattern function."""

    def test_daily_patterns(self, reminders_cog):
        """Test daily schedule patterns."""
        assert reminders_cog.parse_schedule_pattern("daily") == {'type': 'daily'}
        assert reminders_cog.parse_schedule_pattern("every day") == {'type': 'daily'}
        assert reminders_cog.parse_schedule_pattern("everyday") == {'type': 'daily'}
        assert reminders_cog.parse_schedule_pattern("DAILY") == {'type': 'daily'}

    def test_weekday_patterns(self, reminders_cog):
        """Test weekday schedule patterns."""
        result = reminders_cog.parse_schedule_pattern("weekdays")
        assert result == {'type': 'weekdays'}

        result = reminders_cog.parse_schedule_pattern("monday-friday")
        assert result == {'type': 'weekdays'}

        result = reminders_cog.parse_schedule_pattern("mon-fri")
        assert result == {'type': 'weekdays'}

    def test_weekend_patterns(self, reminders_cog):
        """Test weekend schedule patterns."""
        result = reminders_cog.parse_schedule_pattern("weekends")
        assert result == {'type': 'weekends'}

        result = reminders_cog.parse_schedule_pattern("saturday-sunday")
        assert result == {'type': 'weekends'}

    def test_specific_weekdays(self, reminders_cog):
        """Test specific weekday patterns."""
        assert reminders_cog.parse_schedule_pattern("monday") == {'type': 'weekly', 'weekday': 0}
        assert reminders_cog.parse_schedule_pattern("tuesday") == {'type': 'weekly', 'weekday': 1}
        assert reminders_cog.parse_schedule_pattern("wednesday") == {'type': 'weekly', 'weekday': 2}
        assert reminders_cog.parse_schedule_pattern("thursday") == {'type': 'weekly', 'weekday': 3}
        assert reminders_cog.parse_schedule_pattern("friday") == {'type': 'weekly', 'weekday': 4}
        assert reminders_cog.parse_schedule_pattern("saturday") == {'type': 'weekly', 'weekday': 5}
        assert reminders_cog.parse_schedule_pattern("sunday") == {'type': 'weekly', 'weekday': 6}

    def test_weekday_abbreviations(self, reminders_cog):
        """Test weekday abbreviations."""
        assert reminders_cog.parse_schedule_pattern("mon") == {'type': 'weekly', 'weekday': 0}
        assert reminders_cog.parse_schedule_pattern("tue") == {'type': 'weekly', 'weekday': 1}
        assert reminders_cog.parse_schedule_pattern("wed") == {'type': 'weekly', 'weekday': 2}
        assert reminders_cog.parse_schedule_pattern("thu") == {'type': 'weekly', 'weekday': 3}
        assert reminders_cog.parse_schedule_pattern("fri") == {'type': 'weekly', 'weekday': 4}
        assert reminders_cog.parse_schedule_pattern("sat") == {'type': 'weekly', 'weekday': 5}
        assert reminders_cog.parse_schedule_pattern("sun") == {'type': 'weekly', 'weekday': 6}

    def test_every_prefix(self, reminders_cog):
        """Test 'every X' format."""
        assert reminders_cog.parse_schedule_pattern("every monday") == {'type': 'weekly', 'weekday': 0}
        assert reminders_cog.parse_schedule_pattern("every friday") == {'type': 'weekly', 'weekday': 4}

    def test_monthly_patterns(self, reminders_cog):
        """Test monthly schedule patterns."""
        assert reminders_cog.parse_schedule_pattern("monthly") == {'type': 'monthly', 'day': 1}
        assert reminders_cog.parse_schedule_pattern("every month") == {'type': 'monthly', 'day': 1}

    def test_case_insensitive(self, reminders_cog):
        """Test that parsing is case insensitive."""
        assert reminders_cog.parse_schedule_pattern("MONDAY") == {'type': 'weekly', 'weekday': 0}
        assert reminders_cog.parse_schedule_pattern("Daily") == {'type': 'daily'}
        assert reminders_cog.parse_schedule_pattern("WeekDays") == {'type': 'weekdays'}

    def test_with_whitespace(self, reminders_cog):
        """Test parsing with whitespace."""
        assert reminders_cog.parse_schedule_pattern("  daily  ") == {'type': 'daily'}
        assert reminders_cog.parse_schedule_pattern("  monday  ") == {'type': 'weekly', 'weekday': 0}

    def test_invalid_patterns(self, reminders_cog):
        """Test invalid schedule patterns."""
        assert reminders_cog.parse_schedule_pattern("invalid") is None
        assert reminders_cog.parse_schedule_pattern("") is None
        assert reminders_cog.parse_schedule_pattern("abc123") is None
