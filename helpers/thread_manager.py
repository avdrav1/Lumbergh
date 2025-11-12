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


async def create_bot_thread(
    message: discord.Message,
    thread_name: str,
    initial_content: Optional[str] = None,
    auto_archive_duration: int = 1440,
    logger = None
) -> Optional[discord.Thread]:
    """
    Create a thread from a message with proper permission checks and error handling.

    This function centralizes thread creation logic used across multiple cogs,
    ensuring consistent behavior including:
    - Permission validation before creation
    - Thread creation with configurable settings
    - Optional initial content posting
    - Automatic unarchiving (fixes Discord auto-archive issue)
    - Comprehensive error handling and logging

    Args:
        message: The Discord message to create a thread from
        thread_name: Name for the thread (max 100 characters)
        initial_content: Optional content to post as first message in thread
        auto_archive_duration: Minutes of inactivity before auto-archive (default: 1440 = 24 hours)
        logger: Optional logger for diagnostic output

    Returns:
        The created Thread object if successful, None otherwise
    """
    channel = message.channel
    guild = message.guild

    # Check bot permissions first
    bot_permissions = channel.permissions_for(guild.me)
    if not bot_permissions.create_public_threads:
        if logger:
            logger.warning(
                f"Missing 'Create Public Threads' permission in {channel.guild.name} "
                f"(channel: {channel.name}). Cannot create thread."
            )
        return None

    try:
        # Create the thread
        thread = await message.create_thread(
            name=thread_name[:100],  # Thread names limited to 100 chars
            auto_archive_duration=auto_archive_duration
        )

        # Post initial content if provided
        if initial_content:
            await thread.send(initial_content)

        # Explicitly ensure thread is not archived
        # (Fixes Discord issue where threads sometimes start archived)
        if thread.archived:
            await thread.edit(archived=False)
            if logger:
                logger.info(f"Unarchived thread '{thread_name}'")

        # Log successful creation
        if logger:
            logger.info(
                f"Created thread '{thread_name}' "
                f"(ID: {thread.id}, archived: {thread.archived}, locked: {thread.locked})"
            )

        return thread

    except discord.Forbidden:
        if logger:
            logger.warning(
                f"Permission denied creating thread '{thread_name}'. "
                "Bot needs 'Create Public Threads' permission."
            )
        return None

    except Exception as e:
        if logger:
            logger.error(f"Failed to create thread '{thread_name}': {e}")
        return None
