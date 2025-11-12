"""Unit tests for calculate_next_scheduled_time function."""
import pytest
from datetime import datetime, time, timedelta
from freezegun import freeze_time

from cogs.reminders import Reminders


@pytest.fixture
def reminders_cog(mock_bot):
    """Create a Reminders cog instance for testing."""
    return Reminders(mock_bot)


class TestNextOccurrenceDaily:
    """Tests for daily schedule calculations."""

    @freeze_time("2025-01-15 10:00:00")  # Wednesday 10am
    def test_daily_before_target_time(self, reminders_cog):
        """Test daily schedule when current time is before target."""
        pattern = {'type': 'daily'}
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be today at 2pm
        assert result.date() == datetime(2025, 1, 15).date()
        assert result.time() == time(14, 0)

    @freeze_time("2025-01-15 15:00:00")  # Wednesday 3pm
    def test_daily_after_target_time(self, reminders_cog):
        """Test daily schedule when current time is after target."""
        pattern = {'type': 'daily'}
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be tomorrow at 2pm
        assert result.date() == datetime(2025, 1, 16).date()
        assert result.time() == time(14, 0)

    @freeze_time("2025-01-15 14:00:00")  # Wednesday exactly 2pm
    def test_daily_exactly_at_target_time(self, reminders_cog):
        """Test daily schedule when current time exactly matches target."""
        pattern = {'type': 'daily'}
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be tomorrow since we're exactly at the time
        assert result.date() == datetime(2025, 1, 16).date()
        assert result.time() == time(14, 0)


class TestNextOccurrenceWeekdays:
    """Tests for weekday schedule calculations."""

    @freeze_time("2025-01-16 10:00:00")  # Thursday 10am
    def test_weekdays_on_thursday_before_target(self, reminders_cog):
        """Test weekdays when it's Thursday before target time."""
        pattern = {'type': 'weekdays'}
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be today (Thursday) at 2pm
        assert result.date() == datetime(2025, 1, 16).date()
        assert result.time() == time(14, 0)

    @freeze_time("2025-01-18 10:00:00")  # Saturday 10am
    def test_weekdays_on_saturday(self, reminders_cog):
        """Test weekdays when it's Saturday."""
        pattern = {'type': 'weekdays'}
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be Monday Jan 20 at 2pm
        assert result.date() == datetime(2025, 1, 20).date()
        assert result.weekday() == 0  # Monday
        assert result.time() == time(14, 0)

    @freeze_time("2025-01-19 10:00:00")  # Sunday 10am
    def test_weekdays_on_sunday(self, reminders_cog):
        """Test weekdays when it's Sunday."""
        pattern = {'type': 'weekdays'}
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be Monday Jan 20 at 2pm
        assert result.date() == datetime(2025, 1, 20).date()
        assert result.weekday() == 0  # Monday

    @freeze_time("2025-01-17 15:00:00")  # Friday 3pm
    def test_weekdays_friday_after_target(self, reminders_cog):
        """Test weekdays when it's Friday after target time."""
        pattern = {'type': 'weekdays'}
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should skip weekend, Monday Jan 20 at 2pm
        assert result.date() == datetime(2025, 1, 20).date()
        assert result.weekday() == 0  # Monday


class TestNextOccurrenceWeekends:
    """Tests for weekend schedule calculations."""

    @freeze_time("2025-01-15 10:00:00")  # Thursday 10am
    def test_weekends_on_weekday(self, reminders_cog):
        """Test weekends when it's a weekday."""
        pattern = {'type': 'weekends'}
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be Saturday Jan 18 at 2pm
        assert result.date() == datetime(2025, 1, 18).date()
        assert result.weekday() == 5  # Saturday

    @freeze_time("2025-01-18 10:00:00")  # Saturday 10am
    def test_weekends_on_saturday_before_target(self, reminders_cog):
        """Test weekends when it's Saturday before target time."""
        pattern = {'type': 'weekends'}
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be today (Saturday) at 2pm
        assert result.date() == datetime(2025, 1, 18).date()
        assert result.time() == time(14, 0)

    @freeze_time("2025-01-18 15:00:00")  # Saturday 3pm
    def test_weekends_on_saturday_after_target(self, reminders_cog):
        """Test weekends when it's Saturday after target time."""
        pattern = {'type': 'weekends'}
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be tomorrow (Sunday) at 2pm
        assert result.date() == datetime(2025, 1, 19).date()
        assert result.weekday() == 6  # Sunday

    @freeze_time("2025-01-19 15:00:00")  # Sunday 3pm
    def test_weekends_on_sunday_after_target(self, reminders_cog):
        """Test weekends when it's Sunday after target time."""
        pattern = {'type': 'weekends'}
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be next Saturday Jan 25 at 2pm
        assert result.date() == datetime(2025, 1, 25).date()
        assert result.weekday() == 5  # Saturday


class TestNextOccurrenceWeekly:
    """Tests for weekly (specific day) schedule calculations."""

    @freeze_time("2025-01-16 10:00:00")  # Thursday 10am
    def test_weekly_same_day_before_target(self, reminders_cog):
        """Test weekly when today is target day before target time."""
        pattern = {'type': 'weekly', 'weekday': 3}  # Thursday
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be today at 2pm
        assert result.date() == datetime(2025, 1, 16).date()
        assert result.time() == time(14, 0)

    @freeze_time("2025-01-16 15:00:00")  # Thursday 3pm
    def test_weekly_same_day_after_target(self, reminders_cog):
        """Test weekly when today is target day after target time."""
        pattern = {'type': 'weekly', 'weekday': 3}  # Thursday
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be next Thursday Jan 23 at 2pm
        assert result.date() == datetime(2025, 1, 23).date()
        assert result.weekday() == 3  # Thursday

    @freeze_time("2025-01-16 10:00:00")  # Thursday 10am
    def test_weekly_future_day_same_week(self, reminders_cog):
        """Test weekly when target day is later this week."""
        pattern = {'type': 'weekly', 'weekday': 5}  # Saturday
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be this Saturday Jan 18 at 2pm
        assert result.date() == datetime(2025, 1, 18).date()
        assert result.weekday() == 5  # Saturday

    @freeze_time("2025-01-16 10:00:00")  # Thursday 10am
    def test_weekly_past_day_next_week(self, reminders_cog):
        """Test weekly when target day was earlier this week."""
        pattern = {'type': 'weekly', 'weekday': 1}  # Tuesday
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be next Tuesday Jan 21 at 2pm
        assert result.date() == datetime(2025, 1, 21).date()
        assert result.weekday() == 1  # Tuesday

    @freeze_time("2025-01-19 10:00:00")  # Sunday 10am
    def test_weekly_monday_from_sunday(self, reminders_cog):
        """Test weekly Monday reminder on Sunday."""
        pattern = {'type': 'weekly', 'weekday': 0}  # Monday
        target = time(9, 0)  # 9am

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be tomorrow (Monday) Jan 20 at 9am
        assert result.date() == datetime(2025, 1, 20).date()
        assert result.weekday() == 0  # Monday


class TestNextOccurrenceMonthly:
    """Tests for monthly schedule calculations."""

    @freeze_time("2025-01-15 10:00:00")  # Jan 15, 10am
    def test_monthly_before_target_day(self, reminders_cog):
        """Test monthly when current day is before target day."""
        pattern = {'type': 'monthly', 'day': 20}
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be Jan 20 at 2pm
        assert result.date() == datetime(2025, 1, 20).date()
        assert result.time() == time(14, 0)

    @freeze_time("2025-01-25 10:00:00")  # Jan 25, 10am
    def test_monthly_after_target_day(self, reminders_cog):
        """Test monthly when current day is after target day."""
        pattern = {'type': 'monthly', 'day': 20}
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be Feb 20 at 2pm
        assert result.date() == datetime(2025, 2, 20).date()
        assert result.time() == time(14, 0)

    @freeze_time("2025-01-20 15:00:00")  # Jan 20, 3pm
    def test_monthly_on_target_day_after_time(self, reminders_cog):
        """Test monthly when today is target day but after target time."""
        pattern = {'type': 'monthly', 'day': 20}
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be Feb 20 at 2pm
        assert result.date() == datetime(2025, 2, 20).date()

    @freeze_time("2025-12-15 10:00:00")  # Dec 15, 10am
    def test_monthly_crosses_year_boundary(self, reminders_cog):
        """Test monthly when next occurrence is in next year."""
        pattern = {'type': 'monthly', 'day': 10}
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be Jan 10, 2026 at 2pm
        assert result.date() == datetime(2026, 1, 10).date()
        assert result.time() == time(14, 0)

    @freeze_time("2025-01-31 15:00:00")  # Jan 31, 3pm (after target)
    def test_monthly_day_31_february(self, reminders_cog):
        """Test monthly when target day doesn't exist in next month."""
        pattern = {'type': 'monthly', 'day': 31}
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # February doesn't have day 31, should use last day (28 or 29)
        # In 2025, Feb has 28 days
        assert result.month == 2
        assert result.day == 28
        assert result.time() == time(14, 0)

    @freeze_time("2025-03-31 15:00:00")  # Mar 31, 3pm (after target)
    def test_monthly_day_31_april(self, reminders_cog):
        """Test monthly day 31 going into April (30 days)."""
        pattern = {'type': 'monthly', 'day': 31}
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # April doesn't have day 31, should use last day (30)
        assert result.month == 4
        assert result.day == 30

    @freeze_time("2024-01-31 15:00:00")  # Jan 31, 2024 3pm (after target, leap year)
    def test_monthly_day_31_february_leap_year(self, reminders_cog):
        """Test monthly day 31 going into February on leap year."""
        pattern = {'type': 'monthly', 'day': 31}
        target = time(14, 0)  # 2pm

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # 2024 is a leap year, Feb has 29 days
        assert result.month == 2
        assert result.day == 29


class TestNextOccurrenceEdgeCases:
    """Tests for edge cases and error handling."""

    @freeze_time("2025-01-15 23:59:59")  # Almost midnight
    def test_daily_near_midnight(self, reminders_cog):
        """Test daily calculation near midnight."""
        pattern = {'type': 'daily'}
        target = time(0, 0)  # Midnight

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should be tomorrow at midnight
        assert result.date() == datetime(2025, 1, 16).date()
        assert result.time() == time(0, 0)

    @freeze_time("2025-01-15 10:00:00")
    def test_invalid_pattern_type(self, reminders_cog):
        """Test with invalid pattern type."""
        pattern = {'type': 'invalid'}
        target = time(14, 0)

        result = reminders_cog.calculate_next_scheduled_time(pattern, target)

        # Should return None for invalid pattern
        assert result is None
