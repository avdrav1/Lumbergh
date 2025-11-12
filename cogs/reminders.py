"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.3.0
"""

import asyncio
import re
from datetime import datetime, timedelta, time
from discord.ext import commands
from discord.ext.commands import Context
from discord import app_commands
import discord


class Reminders(commands.Cog, name="reminders"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.active_reminders = []
        self.recurring_reminders = []
        self.scheduled_reminders = []

    def parse_time(self, time_str: str) -> int:
        """Parse time string into seconds. Supports formats like: 5m, 1h, 30s, 2d, 1w"""
        time_str = time_str.lower().strip()

        match = re.match(r'^(\d+)([smhdw])$', time_str)
        if not match:
            return None

        amount, unit = match.groups()
        amount = int(amount)

        multipliers = {
            's': 1,           # seconds
            'm': 60,          # minutes
            'h': 3600,        # hours
            'd': 86400,       # days
            'w': 604800,      # weeks
        }

        return amount * multipliers[unit]

    def parse_time_of_day(self, time_str: str):
        """Parse time of day string into a time object."""
        time_str = time_str.strip().lower()

        # Handle AM/PM format like 9:00 AM, 2:30 PM, 9am
        am_pm_pattern = r'^(\d{1,2}):?(\d{2})?\s*(am|pm)$'
        am_pm_match = re.match(am_pm_pattern, time_str)
        if am_pm_match:
            hour = int(am_pm_match.group(1))
            minute = int(am_pm_match.group(2) or 0)
            period = am_pm_match.group(3)

            if hour < 1 or hour > 12 or minute < 0 or minute > 59:
                return None

            # Convert to 24-hour format
            if period == 'pm' and hour != 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0

            return time(hour, minute)

        # Handle 24-hour format like 14:30
        hour_pattern = r'^(\d{1,2}):(\d{2})$'
        hour_match = re.match(hour_pattern, time_str)
        if hour_match:
            hour = int(hour_match.group(1))
            minute = int(hour_match.group(2))

            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                return None

            return time(hour, minute)

        # Handle hour only format like 9am, 14
        hour_only_pattern = r'^(\d{1,2})(am|pm)?$'
        hour_only_match = re.match(hour_only_pattern, time_str)
        if hour_only_match:
            hour = int(hour_only_match.group(1))
            period = hour_only_match.group(2)

            if period:  # AM/PM format
                if hour < 1 or hour > 12:
                    return None
                if period == 'pm' and hour != 12:
                    hour += 12
                elif period == 'am' and hour == 12:
                    hour = 0
            else:  # 24-hour format
                if hour < 0 or hour > 23:
                    return None

            return time(hour, 0)

        return None

    def parse_schedule_pattern(self, pattern: str) -> dict:
        """Parse schedule pattern into a standardized format."""
        pattern = pattern.strip().lower()

        weekdays = {
            'monday': 0, 'mon': 0,
            'tuesday': 1, 'tue': 1, 'tues': 1,
            'wednesday': 2, 'wed': 2,
            'thursday': 3, 'thu': 3, 'thurs': 3,
            'friday': 4, 'fri': 4,
            'saturday': 5, 'sat': 5,
            'sunday': 6, 'sun': 6
        }

        # Daily patterns
        if pattern in ['daily', 'every day', 'everyday']:
            return {'type': 'daily'}

        # Weekdays
        if pattern in ['weekdays', 'weekday', 'monday-friday', 'mon-fri']:
            return {'type': 'weekdays'}

        # Weekends
        if pattern in ['weekends', 'weekend', 'saturday-sunday', 'sat-sun']:
            return {'type': 'weekends'}

        # Specific weekday
        if pattern in weekdays:
            return {'type': 'weekly', 'weekday': weekdays[pattern]}

        # Handle "every X" format
        if pattern.startswith('every '):
            day_part = pattern[6:]
            if day_part in weekdays:
                return {'type': 'weekly', 'weekday': weekdays[day_part]}

        # Monthly
        if pattern in ['monthly', 'every month']:
            return {'type': 'monthly', 'day': 1}

        return None

    def calculate_next_scheduled_time(self, schedule_pattern: dict, target_time):
        """Calculate the next occurrence of a scheduled reminder."""
        now = datetime.now()

        if schedule_pattern['type'] == 'daily':
            next_time = datetime.combine(now.date(), target_time)
            if next_time <= now:
                next_time += timedelta(days=1)
            return next_time

        elif schedule_pattern['type'] == 'weekdays':
            next_time = datetime.combine(now.date(), target_time)

            while True:
                if next_time.weekday() < 5 and next_time > now:
                    return next_time
                next_time += timedelta(days=1)

        elif schedule_pattern['type'] == 'weekends':
            next_time = datetime.combine(now.date(), target_time)

            while True:
                if next_time.weekday() >= 5 and next_time > now:
                    return next_time
                next_time += timedelta(days=1)

        elif schedule_pattern['type'] == 'weekly':
            target_weekday = schedule_pattern['weekday']
            next_time = datetime.combine(now.date(), target_time)

            days_ahead = target_weekday - now.weekday()
            if days_ahead < 0 or (days_ahead == 0 and next_time <= now):
                days_ahead += 7

            return next_time + timedelta(days=days_ahead)

        elif schedule_pattern['type'] == 'monthly':
            target_day = schedule_pattern['day']

            try:
                next_time = datetime.combine(now.date().replace(day=target_day), target_time)
                if next_time > now:
                    return next_time
            except ValueError:
                pass

            # Try next month
            # Fix: Replace day to 1 first to avoid "day is out of range for month" error
            # when current day is 31 and next month has fewer days
            if now.month == 12:
                next_month = now.replace(year=now.year + 1, month=1, day=1)
            else:
                next_month = now.replace(day=1, month=now.month + 1)

            try:
                return datetime.combine(next_month.date().replace(day=target_day), target_time)
            except ValueError:
                if next_month.month == 12:
                    last_day = next_month.replace(year=next_month.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    last_day = next_month.replace(month=next_month.month + 1, day=1) - timedelta(days=1)
                return datetime.combine(last_day.date(), target_time)

        return None

    def format_time(self, seconds: int) -> str:
        """Format seconds into a human-readable string."""
        if seconds < 60:
            return f"{seconds} second{'s' if seconds != 1 else ''}"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''}"
        elif seconds < 604800:
            days = seconds // 86400
            return f"{days} day{'s' if days != 1 else ''}"
        else:
            weeks = seconds // 604800
            return f"{weeks} week{'s' if weeks != 1 else ''}"

    async def reminder_worker(self, delay: int, user_id: int, channel_id: int, message: str, formatted_time: str, recurring: bool = False, original_delay: int = None):
        """Background worker that handles a single reminder."""
        try:
            print(f"🕐 Starting reminder timer for {delay} seconds: {message} (Recurring: {recurring})")

            await asyncio.sleep(delay)

            print(f"⏰ Timer finished, sending reminder: {message}")

            channel = self.bot.get_channel(channel_id)

            user = self.bot.get_user(user_id)
            if user is None:
                try:
                    print(f"🔍 User not in cache, fetching from API...")
                    user = await self.bot.fetch_user(user_id)
                    print(f"✅ User fetched successfully: {user.display_name}")
                except Exception as e:
                    print(f"❌ Could not fetch user: {e}")

            print(f"📍 Channel found: {channel is not None}, User found: {user is not None}")

            if channel is None:
                print(f"❌ Could not find channel with ID: {channel_id}")
                return

            if user is None:
                print(f"❌ Could not find user with ID: {user_id}")
                return

            recurring_text = " (Recurring)" if recurring else ""
            embed = discord.Embed(
                title=f"⏰ Reminder{recurring_text}",
                description=f"**{user.mention}**, you asked me to remind you:\n\n*{message}*",
                color=0x3498db,
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text=f"Set to repeat every {formatted_time}" if recurring else f"Set {formatted_time} ago")

            await channel.send(embed=embed)
            print(f"✅ Reminder sent successfully: {message}")

            if recurring and original_delay:
                print(f"🔄 Scheduling next recurring reminder in {original_delay} seconds")
                next_task = asyncio.create_task(
                    self.reminder_worker(original_delay, user_id, channel_id, message, formatted_time, True, original_delay)
                )

                for reminder in self.active_reminders:
                    if reminder.get('recurring') and reminder['user_id'] == user_id and reminder['message'] == message:
                        reminder['task'] = next_task
                        break

        except asyncio.CancelledError:
            print(f"🚫 Reminder cancelled: {message}")
            raise
        except Exception as e:
            print(f"❌ Error in reminder worker: {e}")
            import traceback
            traceback.print_exc()

    async def scheduled_reminder_worker(self, schedule_pattern: dict, target_time, user_id: int, channel_id: int, message: str, schedule_description: str):
        """Background worker that handles scheduled reminders."""
        try:
            while True:
                next_occurrence = self.calculate_next_scheduled_time(schedule_pattern, target_time)
                if next_occurrence is None:
                    print(f"❌ Could not calculate next occurrence for scheduled reminder: {message}")
                    break

                seconds_until = (next_occurrence - datetime.now()).total_seconds()

                print(f"📅 Scheduled reminder: {message}")
                print(f"⏰ Next occurrence: {next_occurrence.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"⏱️ Waiting {int(seconds_until)} seconds")

                if seconds_until <= 0:
                    seconds_until = 1

                await asyncio.sleep(seconds_until)

                channel = self.bot.get_channel(channel_id)

                user = self.bot.get_user(user_id)
                if user is None:
                    try:
                        user = await self.bot.fetch_user(user_id)
                    except Exception as e:
                        print(f"❌ Could not fetch user for scheduled reminder: {e}")
                        continue

                if channel and user:
                    embed = discord.Embed(
                        title="📅 Scheduled Reminder",
                        description=f"**{user.mention}**, your {schedule_description} reminder:\n\n*{message}*",
                        color=0x9b59b6,
                        timestamp=datetime.utcnow()
                    )
                    next_time = self.calculate_next_scheduled_time(schedule_pattern, target_time)
                    if next_time:
                        embed.set_footer(text=f"Next: {next_time.strftime('%Y-%m-%d %H:%M')}")

                    await channel.send(embed=embed)
                    print(f"✅ Scheduled reminder sent: {message}")
                else:
                    print(f"❌ Could not find channel or user for scheduled reminder")

        except asyncio.CancelledError:
            print(f"🚫 Scheduled reminder cancelled: {message}")
            raise
        except Exception as e:
            print(f"❌ Error in scheduled reminder worker: {e}")
            import traceback
            traceback.print_exc()

    @commands.hybrid_command(name="remind", description="Set a one-time reminder. Usage: /remind <time> <message>")
    @app_commands.describe(
        time="Time until reminder (e.g., 5m, 2h, 1d)",
        message="The reminder message"
    )
    async def remind(self, context: Context, time: str, *, message: str) -> None:
        """Set a reminder for a specified time."""
        print(f"📝 Reminder command called: {time} - {message}")

        seconds = self.parse_time(time)
        if seconds is None:
            embed = discord.Embed(
                title="❌ Invalid Time Format",
                description="Please use a valid time format:\n• `5s` - 5 seconds\n• `10m` - 10 minutes\n• `2h` - 2 hours\n• `1d` - 1 day\n• `1w` - 1 week",
                color=0xe74c3c
            )
            await context.send(embed=embed)
            return

        print(f"⏱️ Parsed time: {seconds} seconds")

        min_time = 10
        if seconds < min_time:
            embed = discord.Embed(
                title="❌ Time Too Short",
                description=f"Please set a reminder for at least {min_time} seconds.",
                color=0xe74c3c
            )
            await context.send(embed=embed)
            return

        max_time = 31536000
        if seconds > max_time:
            embed = discord.Embed(
                title="❌ Time Too Long",
                description="Please set a reminder for less than 1 year.",
                color=0xe74c3c
            )
            await context.send(embed=embed)
            return

        if len(message) > 500:
            embed = discord.Embed(
                title="❌ Message Too Long",
                description="Please keep your reminder message under 500 characters.",
                color=0xe74c3c
            )
            await context.send(embed=embed)
            return

        user_id = context.author.id
        channel_id = context.channel.id
        formatted_time = self.format_time(seconds)

        user_total_reminders = [r for r in self.active_reminders if r['user_id'] == user_id and not r['task'].done()]
        if len(user_total_reminders) >= 5:
            embed = discord.Embed(
                title="❌ Too Many Reminders",
                description="You can only have 5 active reminders at a time (including recurring ones).",
                color=0xe74c3c
            )
            await context.send(embed=embed)
            return

        print(f"👤 User ID: {user_id}, Channel ID: {channel_id}")

        embed = discord.Embed(
            title="✅ Reminder Set",
            description=f"I'll remind you in **{formatted_time}**:\n\n*{message}*",
            color=0x2ecc71,
            timestamp=datetime.utcnow()
        )

        await context.send(embed=embed)
        print("✅ Confirmation message sent")

        task = asyncio.create_task(
            self.reminder_worker(seconds, user_id, channel_id, message, formatted_time, False, None)
        )

        reminder_data = {
            'task': task,
            'user_id': user_id,
            'message': message,
            'time': formatted_time,
            'recurring': False,
            'interval_seconds': seconds
        }
        self.active_reminders.append(reminder_data)

        print(f"🚀 Reminder task created and stored. Total active: {len(self.active_reminders)}")

    @commands.hybrid_command(name="remind-recurring", description="Set a recurring reminder. Usage: /remind-recurring <interval> <message>")
    @app_commands.describe(
        interval="Time interval for recurring reminder (e.g., 30m, 1h, 1d)",
        message="The reminder message"
    )
    async def remind_recurring(self, context: Context, interval: str, *, message: str) -> None:
        """Set a recurring reminder for a specified interval."""
        print(f"📝 Recurring reminder command called: {interval} - {message}")

        seconds = self.parse_time(interval)
        if seconds is None:
            embed = discord.Embed(
                title="❌ Invalid Time Format",
                description="Please use a valid time format:\n• `5s` - 5 seconds\n• `10m` - 10 minutes\n• `2h` - 2 hours\n• `1d` - 1 day\n• `1w` - 1 week",
                color=0xe74c3c
            )
            await context.send(embed=embed)
            return

        print(f"⏱️ Parsed time: {seconds} seconds")

        min_time = 60
        if seconds < min_time:
            embed = discord.Embed(
                title="❌ Time Too Short",
                description="Recurring reminders need at least 1 minute.",
                color=0xe74c3c
            )
            await context.send(embed=embed)
            return

        max_time = 86400
        if seconds > max_time:
            embed = discord.Embed(
                title="❌ Time Too Long",
                description="Please set a recurring reminder for less than 1 day.",
                color=0xe74c3c
            )
            await context.send(embed=embed)
            return

        if len(message) > 500:
            embed = discord.Embed(
                title="❌ Message Too Long",
                description="Please keep your reminder message under 500 characters.",
                color=0xe74c3c
            )
            await context.send(embed=embed)
            return

        user_id = context.author.id
        channel_id = context.channel.id
        formatted_time = self.format_time(seconds)

        user_total_reminders = [r for r in self.active_reminders if r['user_id'] == user_id and not r['task'].done()]
        if len(user_total_reminders) >= 5:
            embed = discord.Embed(
                title="❌ Too Many Reminders",
                description="You can only have 5 active reminders at a time (including recurring ones).",
                color=0xe74c3c
            )
            await context.send(embed=embed)
            return

        user_recurring = [r for r in user_total_reminders if r.get('recurring', False)]
        if len(user_recurring) >= 3:
            embed = discord.Embed(
                title="❌ Too Many Recurring Reminders",
                description="You can only have 3 active recurring reminders at a time.",
                color=0xe74c3c
            )
            await context.send(embed=embed)
            return

        print(f"👤 User ID: {user_id}, Channel ID: {channel_id}")

        embed = discord.Embed(
            title="✅ Reminder Set",
            description=f"I'll remind you every **{formatted_time}**:\n\n*{message}*",
            color=0x2ecc71,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="🔄 Recurring", value="This reminder will repeat until cancelled", inline=False)

        await context.send(embed=embed)
        print("✅ Confirmation message sent")

        task = asyncio.create_task(
            self.reminder_worker(seconds, user_id, channel_id, message, formatted_time, True, seconds)
        )

        reminder_data = {
            'task': task,
            'user_id': user_id,
            'message': message,
            'time': formatted_time,
            'recurring': True,
            'interval_seconds': seconds
        }
        self.active_reminders.append(reminder_data)

        print(f"🚀 Recurring reminder task created. Total active: {len(self.active_reminders)}")

    @commands.hybrid_command(name="remind-scheduled", description="Set a scheduled reminder. Usage: /remind-scheduled <pattern> <time> <message>")
    @app_commands.describe(
        pattern="Schedule pattern (daily, weekdays, weekends, monday, etc.)",
        time_str="Time of day (e.g., 9:00 AM, 2:30 PM, 14:30)",
        message="The reminder message"
    )
    async def remind_scheduled(self, context: Context, pattern: str, time_str: str, *, message: str) -> None:
        """Set a scheduled reminder for specific times and days."""
        print(f"📅 Schedule command called: {pattern} at {time_str} - {message}")

        schedule_pattern = self.parse_schedule_pattern(pattern)
        if schedule_pattern is None:
            embed = discord.Embed(
                title="❌ Invalid Schedule Pattern",
                description="Please use a valid schedule pattern:\n• `daily` - Every day\n• `weekdays` - Monday through Friday\n• `weekends` - Saturday and Sunday\n• `monday`, `tuesday`, etc. - Specific weekday\n• `monthly` - First day of each month",
                color=0xe74c3c
            )
            await context.send(embed=embed)
            return

        target_time = self.parse_time_of_day(time_str)
        if target_time is None:
            embed = discord.Embed(
                title="❌ Invalid Time Format",
                description="Please use a valid time format:\n• `9:00 AM` or `9am`\n• `2:30 PM` or `2:30pm`\n• `14:30` (24-hour format)\n• `09:00` (24-hour format)",
                color=0xe74c3c
            )
            await context.send(embed=embed)
            return

        print(f"⏰ Parsed schedule: {schedule_pattern}, time: {target_time}")

        if len(message) > 500:
            embed = discord.Embed(
                title="❌ Message Too Long",
                description="Please keep your reminder message under 500 characters.",
                color=0xe74c3c
            )
            await context.send(embed=embed)
            return

        user_id = context.author.id
        channel_id = context.channel.id

        user_total_reminders = [r for r in self.active_reminders if r['user_id'] == user_id and not r['task'].done()]
        if len(user_total_reminders) >= 5:
            embed = discord.Embed(
                title="❌ Too Many Reminders",
                description="You can only have 5 active reminders at a time (including scheduled ones).",
                color=0xe74c3c
            )
            await context.send(embed=embed)
            return

        next_occurrence = self.calculate_next_scheduled_time(schedule_pattern, target_time)
        if next_occurrence is None:
            embed = discord.Embed(
                title="❌ Error Calculating Schedule",
                description="Could not calculate the next occurrence for this schedule.",
                color=0xe74c3c
            )
            await context.send(embed=embed)
            return

        schedule_descriptions = {
            'daily': 'daily',
            'weekdays': 'weekdays',
            'weekends': 'weekends',
            'weekly': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][schedule_pattern.get('weekday', 0)] + 's',
            'monthly': 'monthly'
        }

        schedule_description = schedule_descriptions.get(schedule_pattern['type'], 'scheduled')
        time_12h = target_time.strftime('%I:%M %p').lstrip('0')

        print(f"👤 User ID: {user_id}, Channel ID: {channel_id}")
        print(f"📅 Next occurrence: {next_occurrence}")

        embed = discord.Embed(
            title="✅ Scheduled Reminder Set",
            description=f"I'll remind you **{schedule_description}** at **{time_12h}**:\n\n*{message}*",
            color=0x9b59b6,
            timestamp=datetime.utcnow()
        )
        embed.add_field(
            name="📅 Next Occurrence",
            value=next_occurrence.strftime('%A, %B %d at %I:%M %p').replace(' 0', ' '),
            inline=False
        )
        embed.add_field(name="🔄 Repeating", value="This reminder will repeat according to your schedule", inline=False)

        await context.send(embed=embed)
        print("✅ Confirmation message sent")

        task = asyncio.create_task(
            self.scheduled_reminder_worker(schedule_pattern, target_time, user_id, channel_id, message, schedule_description)
        )

        reminder_data = {
            'task': task,
            'user_id': user_id,
            'message': message,
            'schedule_pattern': schedule_pattern,
            'target_time': target_time,
            'schedule_description': schedule_description,
            'type': 'scheduled'
        }
        self.active_reminders.append(reminder_data)

        print(f"🚀 Scheduled reminder task created. Total active: {len(self.active_reminders)}")

    @commands.hybrid_command(name="remind-manage", description="Manage your reminders. Usage: /remind-manage <action>")
    @app_commands.describe(
        action="Action to perform (list, stop, stop-recurring, stop-scheduled, stats, test, help)",
        message_part="(For 'stop' action) Part of the reminder message to search for"
    )
    async def remind_manage(self, context: Context, action: str, *, message_part: str = None) -> None:
        """Manage reminders with various actions."""
        action = action.lower().strip()

        if action == "list":
            await self._manage_list(context)
        elif action == "stop":
            if message_part is None:
                embed = discord.Embed(
                    title="❌ Missing Message",
                    description="Please provide part of the reminder message to stop.\n\nUsage: `/remind-manage stop <message part>`",
                    color=0xe74c3c
                )
                await context.send(embed=embed)
                return
            await self._manage_stop(context, message_part)
        elif action == "stop-recurring":
            await self._manage_stop_recurring(context)
        elif action == "stop-scheduled":
            await self._manage_stop_scheduled(context)
        elif action == "stats":
            await self._manage_stats(context)
        elif action == "test":
            await self._manage_test(context)
        elif action == "help":
            await self._manage_help(context)
        else:
            embed = discord.Embed(
                title="❌ Invalid Action",
                description="Please use a valid action:\n• `list` - List all your reminders\n• `stop <message>` - Stop specific reminder\n• `stop-recurring` - Stop all recurring reminders\n• `stop-scheduled` - Stop all scheduled reminders\n• `stats` - Show system statistics\n• `test` - Test reminder (10 seconds)\n• `help` - Show detailed help",
                color=0xe74c3c
            )
            await context.send(embed=embed)

    async def _manage_list(self, context: Context) -> None:
        """List all active reminders for the user."""
        user_id = context.author.id
        user_reminders = [r for r in self.active_reminders if r['user_id'] == user_id and not r['task'].done()]

        if not user_reminders:
            embed = discord.Embed(
                title="📝 Your Reminders",
                description="You don't have any active reminders.",
                color=0x3498db
            )
            await context.send(embed=embed)
            return

        embed = discord.Embed(
            title="📝 Your Active Reminders",
            color=0x3498db,
            timestamp=datetime.utcnow()
        )

        one_time_reminders = [r for r in user_reminders if not r.get('recurring', False) and r.get('type') != 'scheduled']
        recurring_reminders = [r for r in user_reminders if r.get('recurring', False) and r.get('type') != 'scheduled']
        scheduled_reminders = [r for r in user_reminders if r.get('type') == 'scheduled']

        if one_time_reminders:
            reminder_list = []
            for i, reminder in enumerate(one_time_reminders, 1):
                reminder_list.append(f"**{i}.** {reminder['message'][:30]}{'...' if len(reminder['message']) > 30 else ''} *({reminder['time']})*")

            embed.add_field(
                name="⏰ One-time Reminders",
                value="\n".join(reminder_list),
                inline=False
            )

        if recurring_reminders:
            reminder_list = []
            for i, reminder in enumerate(recurring_reminders, 1):
                reminder_list.append(f"**{i}.** {reminder['message'][:30]}{'...' if len(reminder['message']) > 30 else ''} *({reminder['time']})*")

            embed.add_field(
                name="🔄 Recurring Reminders",
                value="\n".join(reminder_list),
                inline=False
            )

        if scheduled_reminders:
            reminder_list = []
            for i, reminder in enumerate(scheduled_reminders, 1):
                schedule_desc = reminder['schedule_description']
                time_str = reminder['target_time'].strftime('%I:%M %p').lstrip('0')
                next_occurrence = self.calculate_next_scheduled_time(reminder['schedule_pattern'], reminder['target_time'])
                next_str = next_occurrence.strftime('%m/%d %I:%M %p').lstrip('0') if next_occurrence else "Unknown"

                reminder_list.append(f"**{i}.** {reminder['message'][:25]}{'...' if len(reminder['message']) > 25 else ''}\n*{schedule_desc} at {time_str} (next: {next_str})*")

            embed.add_field(
                name="📅 Scheduled Reminders",
                value="\n".join(reminder_list),
                inline=False
            )

        embed.set_footer(text="Use /remind-manage to cancel reminders")
        await context.send(embed=embed)

    async def _manage_stop(self, context: Context, message_part: str) -> None:
        """Stop a specific reminder by searching for message content."""
        user_id = context.author.id
        user_reminders = [r for r in self.active_reminders if r['user_id'] == user_id and not r['task'].done()]

        matching_reminders = [r for r in user_reminders if message_part.lower() in r['message'].lower()]

        if not matching_reminders:
            embed = discord.Embed(
                title="❌ No Matching Reminders",
                description=f"No active reminders found containing: *{message_part}*",
                color=0xe74c3c
            )
            await context.send(embed=embed)
            return

        cancelled_count = 0
        for reminder in matching_reminders:
            if not reminder['task'].done():
                reminder['task'].cancel()
                cancelled_count += 1

        self.active_reminders = [r for r in self.active_reminders if r not in matching_reminders]

        embed = discord.Embed(
            title="✅ Reminders Stopped",
            description=f"Stopped {cancelled_count} reminder{'s' if cancelled_count != 1 else ''} matching: *{message_part}*",
            color=0x2ecc71
        )
        await context.send(embed=embed)

    async def _manage_stop_recurring(self, context: Context) -> None:
        """Stop all recurring reminders for the user."""
        user_id = context.author.id
        user_recurring = [r for r in self.active_reminders if r['user_id'] == user_id and r.get('recurring', False) and not r['task'].done()]

        if not user_recurring:
            embed = discord.Embed(
                title="📝 No Recurring Reminders",
                description="You don't have any active recurring reminders to stop.",
                color=0x3498db
            )
            await context.send(embed=embed)
            return

        cancelled_count = 0
        for reminder in user_recurring:
            if not reminder['task'].done():
                reminder['task'].cancel()
                cancelled_count += 1

        self.active_reminders = [r for r in self.active_reminders if not (r['user_id'] == user_id and r.get('recurring', False))]

        embed = discord.Embed(
            title="✅ Recurring Reminders Stopped",
            description=f"Stopped {cancelled_count} recurring reminder{'s' if cancelled_count != 1 else ''}.",
            color=0x2ecc71
        )
        await context.send(embed=embed)

    async def _manage_stop_scheduled(self, context: Context) -> None:
        """Stop all scheduled reminders for the user."""
        user_id = context.author.id
        user_scheduled = [r for r in self.active_reminders if r['user_id'] == user_id and r.get('type') == 'scheduled' and not r['task'].done()]

        if not user_scheduled:
            embed = discord.Embed(
                title="📅 No Scheduled Reminders",
                description="You don't have any active scheduled reminders to stop.",
                color=0x3498db
            )
            await context.send(embed=embed)
            return

        cancelled_count = 0
        for reminder in user_scheduled:
            if not reminder['task'].done():
                reminder['task'].cancel()
                cancelled_count += 1

        self.active_reminders = [r for r in self.active_reminders if not (r['user_id'] == user_id and r.get('type') == 'scheduled')]

        embed = discord.Embed(
            title="✅ Scheduled Reminders Stopped",
            description=f"Stopped {cancelled_count} scheduled reminder{'s' if cancelled_count != 1 else ''}.",
            color=0x2ecc71
        )
        await context.send(embed=embed)

    async def _manage_stats(self, context: Context) -> None:
        """Show the status of the reminder system."""
        total_reminders = len(self.active_reminders)
        completed_reminders = len([r for r in self.active_reminders if r['task'].done()])
        active_reminders = total_reminders - completed_reminders

        one_time = len([r for r in self.active_reminders if not r.get('recurring', False) and r.get('type') != 'scheduled' and not r['task'].done()])
        recurring = len([r for r in self.active_reminders if r.get('recurring', False) and not r['task'].done()])
        scheduled = len([r for r in self.active_reminders if r.get('type') == 'scheduled' and not r['task'].done()])

        embed = discord.Embed(
            title="📊 Reminder System Status",
            color=0x3498db
        )
        embed.add_field(name="Total Reminders", value=str(total_reminders), inline=True)
        embed.add_field(name="Active Reminders", value=str(active_reminders), inline=True)
        embed.add_field(name="Completed", value=str(completed_reminders), inline=True)
        embed.add_field(name="⏰ One-time", value=str(one_time), inline=True)
        embed.add_field(name="🔄 Recurring", value=str(recurring), inline=True)
        embed.add_field(name="📅 Scheduled", value=str(scheduled), inline=True)

        await context.send(embed=embed)

    async def _manage_test(self, context: Context) -> None:
        """Test reminder with a 10 second delay (owner only)."""
        if context.author.id != self.bot.owner_id:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="Only the bot owner can use the test command.",
                color=0xe74c3c
            )
            await context.send(embed=embed)
            return

        await self.remind(context, "10s", message="This is a test reminder!")

    async def _manage_help(self, context: Context) -> None:
        """Show detailed help for all reminder commands."""
        embed = discord.Embed(
            title="📚 Reminder Commands Help",
            description="Complete guide to using the reminder system",
            color=0x3498db,
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="⏰ Basic Reminders",
            value="`/remind <time> <message>` - Set a one-time reminder\n`/remind 5m Take a break` - Reminds you in 5 minutes\n`/remind 2h Meeting with team` - Reminds you in 2 hours",
            inline=False
        )

        embed.add_field(
            name="🔄 Recurring Reminders",
            value="`/remind-recurring <interval> <message>` - Set recurring reminder\n`/remind-recurring 30m Stretch break` - Every 30 minutes\n`/remind-recurring 1d Daily standup` - Every day",
            inline=False
        )

        embed.add_field(
            name="📅 Scheduled Reminders",
            value="`/remind-scheduled <pattern> <time> <message>` - Set scheduled reminder\n`/remind-scheduled daily 9:00am Morning coffee` - Every day at 9 AM\n`/remind-scheduled monday 2:30pm Weekly meeting` - Every Monday at 2:30 PM\n`/remind-scheduled weekdays 8am Wake up call` - Weekdays at 8 AM",
            inline=False
        )

        embed.add_field(
            name="📝 Managing Reminders",
            value="`/remind-manage list` - List all your active reminders\n`/remind-manage stop <text>` - Stop reminders containing text\n`/remind-manage stop-recurring` - Stop all recurring reminders\n`/remind-manage stop-scheduled` - Stop all scheduled reminders\n`/remind-manage stats` - Show system status\n`/remind-manage test` - Test reminder (owner only)\n`/remind-manage help` - Show this help",
            inline=False
        )

        embed.add_field(
            name="⏱️ Time Formats",
            value="**Intervals:** `5s`, `10m`, `2h`, `3d`, `1w`\n**Times:** `9:00 AM`, `2:30 PM`, `14:30`, `9am`",
            inline=True
        )

        embed.add_field(
            name="📊 Schedule Patterns",
            value="`daily` - Every day\n`weekdays` - Mon-Fri\n`weekends` - Sat-Sun\n`monday`, `tuesday`, etc.\n`monthly` - 1st of month",
            inline=True
        )

        embed.add_field(
            name="📊 Limits",
            value="• Max 5 total reminders per user\n• Max 3 recurring reminders per user\n• Recurring: 1 min - 1 day intervals\n• One-time: 10 sec - 1 year",
            inline=False
        )

        await context.send(embed=embed)

    @remind.error
    async def remind_error(self, context: Context, error):
        """Handle errors for the remind command."""
        print(f"❌ Command error: {error}")
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="❌ Missing Arguments",
                description="Usage: `/remind <time> <message>`\n\nExample: `/remind 5m Take a break`",
                color=0xe74c3c
            )
            await context.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(Reminders(bot))
