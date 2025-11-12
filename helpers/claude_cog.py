"""
Base cog class with automatic Claude AI initialization.

This module provides a base class for cogs that use Claude AI,
eliminating duplicate initialization code across multiple cogs.
"""

import os
from typing import Optional

from anthropic import AsyncAnthropic
from discord.ext import commands


class ClaudeAICog(commands.Cog):
    """
    Base cog class with automatic Claude AI client initialization.

    This class handles the boilerplate of initializing the Claude AI client,
    checking for API keys, and logging initialization status. Inheriting cogs
    automatically get `self.client` set to an AsyncAnthropic instance (or None
    if the API key is not configured).

    Usage:
        class MyCog(ClaudeAICog, name="mycog"):
            def __init__(self, bot):
                super().__init__(bot, cog_name="My Cog")
                # Additional initialization...

    Attributes:
        bot: The Discord bot instance
        client: AsyncAnthropic client instance (or None if API key not found)
    """

    def __init__(self, bot, cog_name: Optional[str] = None):
        """
        Initialize the cog with Claude AI client.

        Args:
            bot: The Discord bot instance
            cog_name: Human-readable name for logging (e.g., "Art cog")
                     If not provided, uses the class name
        """
        self.bot = bot
        self.client = self._init_claude_client(cog_name)

    def _init_claude_client(self, cog_name: Optional[str] = None) -> Optional[AsyncAnthropic]:
        """
        Initialize Claude AI client with error handling.

        Args:
            cog_name: Human-readable name for logging messages

        Returns:
            AsyncAnthropic client instance if API key is configured, None otherwise
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            # Determine name for logging
            name = cog_name or self.__class__.__name__

            self.bot.logger.warning(
                f"ANTHROPIC_API_KEY not found. {name} AI features will not work."
            )
            return None

        # Log successful initialization
        if cog_name:
            self.bot.logger.info(f"{cog_name} initialized with Claude AI.")

        return AsyncAnthropic(api_key=api_key)
