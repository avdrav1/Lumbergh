"""Integration tests for reminder commands."""
import pytest
from unittest.mock import AsyncMock, Mock
from cogs.reminders import Reminders
from tests.fixtures.discord_mocks import assert_embed_sent, assert_error_embed_sent


@pytest.fixture
def reminders_cog(mock_bot):
    """Create a Reminders cog instance for testing."""
    return Reminders(mock_bot)


class TestRemindCommand:
    """Integration tests for /remind command."""

    @pytest.mark.asyncio
    async def test_remind_with_valid_time(self, reminders_cog, mock_context):
        """Test /remind command with valid time creates reminder."""
        # Execute command
        await reminders_cog.remind.callback(reminders_cog, mock_context, time="5m", message="Test reminder")

        # Verify embed was sent
        assert mock_context.send.called
        embed = assert_embed_sent(mock_context)

        # Verify embed contains expected information
        assert "5 minutes" in embed.description.lower()
        assert "test reminder" in embed.description.lower()

        # Verify reminder was added to active list
        assert len(reminders_cog.active_reminders) == 1
        reminder = reminders_cog.active_reminders[0]
        assert reminder['message'] == "Test reminder"
        assert reminder['user_id'] == mock_context.author.id
        assert reminder['channel_id'] == mock_context.channel.id

    @pytest.mark.asyncio
    async def test_remind_with_invalid_time(self, reminders_cog, mock_context):
        """Test /remind command with invalid time shows error."""
        await reminders_cog.remind.callback(reminders_cog, mock_context, time="invalid", message="Test")

        # Verify error embed was sent
        error_embed = assert_error_embed_sent(mock_context)
        assert "valid time format" in error_embed.description.lower()

        # Verify no reminder was created
        assert len(reminders_cog.active_reminders) == 0

    @pytest.mark.asyncio
    async def test_remind_with_various_time_formats(self, reminders_cog, mock_context):
        """Test /remind command accepts different time formats."""
        time_formats = ["30s", "5m", "2h", "1d", "1w"]

        for time_format in time_formats:
            # Reset mock
            mock_context.send.reset_mock()

            # Execute command
            await reminders_cog.remind.callback(reminders_cog, mock_context, time=time_format, message="Test")

            # Verify success
            assert mock_context.send.called, f"Failed for time format: {time_format}"

    @pytest.mark.asyncio
    async def test_remind_at_user_limit(self, reminders_cog, mock_context):
        """Test /remind command when user reaches their limit."""
        # Create 5 reminders (the limit)
        for i in range(5):
            task = AsyncMock()
            task.done = Mock(return_value=False)
            reminder = {
                'user_id': mock_context.author.id,
                'channel_id': mock_context.channel.id,
                'message': f'Reminder {i}',
                'task': task
            }
            reminders_cog.active_reminders.append(reminder)

        # Try to create 6th reminder
        await reminders_cog.remind.callback(reminders_cog, mock_context, time="5m", message="Extra reminder")

        # Verify error was sent about limit
        error_embed = assert_error_embed_sent(mock_context)
        assert ("limit" in error_embed.description.lower() or
                "maximum" in error_embed.description.lower() or
                "can only have" in error_embed.description.lower())


class TestRemindManage:
    """Integration tests for /remind-manage command."""

    @pytest.mark.asyncio
    async def test_manage_list_no_reminders(self, reminders_cog, mock_context):
        """Test /remind-manage list with no reminders."""
        await reminders_cog.remind_manage.callback(reminders_cog, mock_context, action="list")

        # Verify response indicates no reminders
        assert mock_context.send.called
        call_args = mock_context.send.call_args
        embed = call_args[1]['embed']
        assert "don't have any" in embed.description.lower() or "no reminders" in embed.description.lower()

    @pytest.mark.asyncio
    async def test_manage_list_with_reminders(self, reminders_cog, mock_context):
        """Test /remind-manage list with active reminders."""
        # Add some reminders
        for i in range(3):
            task = AsyncMock()
            task.done = Mock(return_value=False)
            reminder = {
                'user_id': mock_context.author.id,
                'channel_id': mock_context.channel.id,
                'message': f'Reminder {i+1}',
                'task': task,
                'time': f'{i+1} minutes'
            }
            reminders_cog.active_reminders.append(reminder)

        await reminders_cog.remind_manage.callback(reminders_cog, mock_context, action="list")

        # Verify response lists reminders
        assert mock_context.send.called
        call_args = mock_context.send.call_args
        embed = call_args[1]['embed']

        # Should show all 3 reminders in fields
        assert len(embed.fields) > 0
        field_value = embed.fields[0].value.lower()
        for i in range(3):
            assert f'reminder {i+1}' in field_value

    @pytest.mark.asyncio
    async def test_manage_stats(self, reminders_cog, mock_context):
        """Test /remind-manage stats action."""
        # Add various reminder types to active_reminders
        task1 = AsyncMock()
        task1.done = Mock(return_value=False)
        reminders_cog.active_reminders.append({
            'user_id': mock_context.author.id,
            'message': 'One-time reminder',
            'task': task1,
            'recurring': False
        })

        task2 = AsyncMock()
        task2.done = Mock(return_value=False)
        reminders_cog.active_reminders.append({
            'user_id': mock_context.author.id,
            'message': 'Recurring reminder',
            'task': task2,
            'recurring': True
        })

        task3 = AsyncMock()
        task3.done = Mock(return_value=False)
        reminders_cog.active_reminders.append({
            'user_id': mock_context.author.id,
            'message': 'Scheduled reminder',
            'task': task3,
            'type': 'scheduled'
        })

        await reminders_cog.remind_manage.callback(reminders_cog, mock_context, action="stats")

        # Verify stats are shown
        assert mock_context.send.called
        call_args = mock_context.send.call_args
        embed = call_args[1]['embed']

        # Should show counts in fields
        assert len(embed.fields) > 0


class TestRemindRecurring:
    """Integration tests for /remind-recurring command."""

    @pytest.mark.asyncio
    async def test_recurring_with_valid_interval(self, reminders_cog, mock_context):
        """Test /remind-recurring with valid interval."""
        await reminders_cog.remind_recurring.callback(reminders_cog, mock_context, interval="30m", message="Recurring test")

        # Verify success response
        assert mock_context.send.called
        embed = assert_embed_sent(mock_context)
        assert "30 minutes" in embed.description.lower()

        # Verify recurring reminder was created in active_reminders
        assert len(reminders_cog.active_reminders) == 1
        reminder = reminders_cog.active_reminders[0]
        assert reminder['message'] == "Recurring test"
        assert reminder['recurring'] == True

    @pytest.mark.asyncio
    async def test_recurring_at_limit(self, reminders_cog, mock_context):
        """Test /remind-recurring when user has reached recurring limit."""
        # Add 3 recurring reminders (the limit)
        for i in range(3):
            task = AsyncMock()
            task.done = Mock(return_value=False)
            reminder = {
                'user_id': mock_context.author.id,
                'channel_id': mock_context.channel.id,
                'message': f'Recurring {i}',
                'task': task,
                'recurring': True
            }
            reminders_cog.active_reminders.append(reminder)

        # Try to create 4th recurring reminder
        await reminders_cog.remind_recurring.callback(reminders_cog, mock_context, interval="1h", message="Extra")

        # Verify error about recurring limit
        error_embed = assert_error_embed_sent(mock_context)
        assert "recurring" in error_embed.description.lower()


class TestRemindScheduled:
    """Integration tests for /remind-scheduled command."""

    @pytest.mark.asyncio
    async def test_scheduled_daily(self, reminders_cog, mock_context):
        """Test /remind-scheduled with daily pattern."""
        await reminders_cog.remind_scheduled.callback(
            reminders_cog,
            mock_context,
            pattern="daily",
            time_str="9:00am",
            message="Daily reminder"
        )

        # Verify success response
        assert mock_context.send.called
        embed = assert_embed_sent(mock_context)
        assert "daily" in embed.description.lower()
        assert "9:00" in embed.description

        # Verify scheduled reminder was created in active_reminders
        assert len(reminders_cog.active_reminders) == 1
        reminder = reminders_cog.active_reminders[0]
        assert reminder['type'] == 'scheduled'

    @pytest.mark.asyncio
    async def test_scheduled_weekdays(self, reminders_cog, mock_context):
        """Test /remind-scheduled with weekdays pattern."""
        await reminders_cog.remind_scheduled.callback(
            reminders_cog,
            mock_context,
            pattern="weekdays",
            time_str="8:00am",
            message="Weekday reminder"
        )

        # Verify success
        assert mock_context.send.called
        embed = assert_embed_sent(mock_context)
        assert "weekdays" in embed.description.lower()

    @pytest.mark.asyncio
    async def test_scheduled_specific_day(self, reminders_cog, mock_context):
        """Test /remind-scheduled with specific day."""
        await reminders_cog.remind_scheduled.callback(
            reminders_cog,
            mock_context,
            pattern="monday",
            time_str="10:00am",
            message="Monday reminder"
        )

        # Verify success
        assert mock_context.send.called
        embed = assert_embed_sent(mock_context)
        assert "monday" in embed.description.lower()

    @pytest.mark.asyncio
    async def test_scheduled_invalid_time(self, reminders_cog, mock_context):
        """Test /remind-scheduled with invalid time format."""
        await reminders_cog.remind_scheduled.callback(
            reminders_cog,
            mock_context,
            pattern="daily",
            time_str="invalid",
            message="Test"
        )

        # Verify error
        error_embed = assert_error_embed_sent(mock_context)
        assert "time" in error_embed.description.lower()

    @pytest.mark.asyncio
    async def test_scheduled_invalid_pattern(self, reminders_cog, mock_context):
        """Test /remind-scheduled with invalid pattern."""
        await reminders_cog.remind_scheduled.callback(
            reminders_cog,
            mock_context,
            pattern="invalid",
            time_str="9:00am",
            message="Test"
        )

        # Verify error
        error_embed = assert_error_embed_sent(mock_context)
        assert "pattern" in error_embed.description.lower() or "schedule" in error_embed.description.lower()


class TestFormatTime:
    """Tests for the format_time helper function."""

    def test_format_seconds(self, reminders_cog):
        """Test formatting seconds."""
        assert "30 seconds" in reminders_cog.format_time(30)
        assert "1 second" in reminders_cog.format_time(1)

    def test_format_minutes(self, reminders_cog):
        """Test formatting minutes."""
        assert "5 minutes" in reminders_cog.format_time(300)
        assert "1 minute" in reminders_cog.format_time(60)

    def test_format_hours(self, reminders_cog):
        """Test formatting hours."""
        assert "2 hours" in reminders_cog.format_time(7200)
        assert "1 hour" in reminders_cog.format_time(3600)

    def test_format_days(self, reminders_cog):
        """Test formatting days."""
        assert "1 week" in reminders_cog.format_time(604800)
        assert "1 day" in reminders_cog.format_time(86400)

    def test_format_weeks(self, reminders_cog):
        """Test formatting weeks."""
        assert "2 weeks" in reminders_cog.format_time(1209600)
        assert "1 week" in reminders_cog.format_time(604800)
