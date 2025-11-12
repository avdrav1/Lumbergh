"""
Thread management utilities for Discord bot.

This module provides utilities for managing Discord threads, including
identification of bot-created threads and automatic archival of inactive threads.
"""

from datetime import datetime, timezone
from typing import Optional
import discord


# Thread name patterns for identifying bot-created threads
THREAD_NAME_PATTERNS = {
    'art': 'Analysis:',
    'news': '📰 Full Articles',
    'creative': 'Story:'
}


async def is_bot_thread(thread: discord.Thread, bot_user_id: int) -> bool:
    """
    Check if a thread was created by the bot.

    Args:
        thread: The Discord thread to check
        bot_user_id: The bot's user ID

    Returns:
        True if the thread was created by the bot, False otherwise
    """
    # Check if thread owner matches bot
    if thread.owner_id != bot_user_id:
        return False

    # Check if thread name matches any known pattern
    for pattern in THREAD_NAME_PATTERNS.values():
        if thread.name.startswith(pattern):
            return True

    return False


async def get_last_activity_time(thread: discord.Thread) -> Optional[datetime]:
    """
    Get the timestamp of the last activity in a thread.

    Args:
        thread: The Discord thread to check

    Returns:
        Datetime of last message, or thread creation time if no messages,
        or None if unable to determine
    """
    try:
        # Fetch the most recent message
        async for message in thread.history(limit=1):
            return message.created_at

        # No messages found, use thread creation time
        return thread.created_at

    except discord.Forbidden:
        # Can't read thread history due to permissions
        return None
    except Exception:
        # Other errors (thread deleted, etc.)
        return None


async def should_archive_thread(thread: discord.Thread, hours: int = 24) -> bool:
    """
    Determine if a thread should be archived based on inactivity.

    Args:
        thread: The Discord thread to check
        hours: Number of hours of inactivity before archiving (default: 24)

    Returns:
        True if thread should be archived, False otherwise
    """
    # Already archived? Skip
    if thread.archived:
        return False

    # Get last activity time
    last_activity = await get_last_activity_time(thread)
    if last_activity is None:
        # Can't determine activity, don't archive to be safe
        return False

    # Calculate inactivity duration
    now = datetime.now(timezone.utc)
    inactive_duration = now - last_activity

    # Check if inactive for specified duration
    return inactive_duration.total_seconds() >= (hours * 3600)


async def archive_thread(thread: discord.Thread) -> bool:
    """
    Archive a Discord thread.

    Args:
        thread: The Discord thread to archive

    Returns:
        True if successfully archived, False otherwise
    """
    try:
        await thread.edit(archived=True)
        return True
    except discord.Forbidden:
        # Missing permissions
        return False
    except Exception:
        # Other errors
        return False


async def get_inactive_bot_threads(
    channel: discord.TextChannel,
    bot_user_id: int,
    hours: int = 24
) -> list[discord.Thread]:
    """
    Get all inactive bot-created threads in a channel.

    Args:
        channel: The Discord channel to check
        bot_user_id: The bot's user ID
        hours: Number of hours of inactivity to check (default: 24)

    Returns:
        List of threads that should be archived
    """
    inactive_threads = []

    # Check active threads in the channel
    for thread in channel.threads:
        if await is_bot_thread(thread, bot_user_id):
            if await should_archive_thread(thread, hours):
                inactive_threads.append(thread)

    return inactive_threads
