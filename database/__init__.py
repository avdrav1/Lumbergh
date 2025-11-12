"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.3.0
"""

import aiosqlite


class DatabaseManager:
    def __init__(self, *, connection: aiosqlite.Connection) -> None:
        self.connection = connection

    async def add_warn(
        self, user_id: int, server_id: int, moderator_id: int, reason: str
    ) -> int:
        """
        This function will add a warn to the database.

        :param user_id: The ID of the user that should be warned.
        :param reason: The reason why the user should be warned.
        """
        rows = await self.connection.execute(
            "SELECT id FROM warns WHERE user_id=? AND server_id=? ORDER BY id DESC LIMIT 1",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            warn_id = result[0] + 1 if result is not None else 1
            await self.connection.execute(
                "INSERT INTO warns(id, user_id, server_id, moderator_id, reason) VALUES (?, ?, ?, ?, ?)",
                (
                    warn_id,
                    user_id,
                    server_id,
                    moderator_id,
                    reason,
                ),
            )
            await self.connection.commit()
            return warn_id

    async def remove_warn(self, warn_id: int, user_id: int, server_id: int) -> int:
        """
        This function will remove a warn from the database.

        :param warn_id: The ID of the warn.
        :param user_id: The ID of the user that was warned.
        :param server_id: The ID of the server where the user has been warned
        """
        await self.connection.execute(
            "DELETE FROM warns WHERE id=? AND user_id=? AND server_id=?",
            (
                warn_id,
                user_id,
                server_id,
            ),
        )
        await self.connection.commit()
        rows = await self.connection.execute(
            "SELECT COUNT(*) FROM warns WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result is not None else 0

    async def get_warnings(self, user_id: int, server_id: int) -> list:
        """
        This function will get all the warnings of a user.

        :param user_id: The ID of the user that should be checked.
        :param server_id: The ID of the server that should be checked.
        :return: A list of all the warnings of the user.
        """
        rows = await self.connection.execute(
            "SELECT user_id, server_id, moderator_id, reason, strftime('%s', created_at), id FROM warns WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            result_list = []
            for row in result:
                result_list.append(row)
            return result_list

    # ===== LEVELING SYSTEM METHODS =====

    async def get_user_level_data(self, user_id: int, server_id: int) -> dict:
        """
        Get a user's level data (XP, level, messages, last XP time).

        :param user_id: The ID of the user.
        :param server_id: The ID of the server.
        :return: Dictionary with user's level data or None if not found.
        """
        rows = await self.connection.execute(
            "SELECT xp, level, total_messages, last_xp_time FROM levels WHERE user_id=? AND server_id=?",
            (user_id, server_id),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            if result:
                return {
                    "xp": result[0],
                    "level": result[1],
                    "total_messages": result[2],
                    "last_xp_time": result[3],
                }
            return None

    async def add_xp(
        self, user_id: int, server_id: int, xp_amount: int, current_time: str
    ) -> tuple:
        """
        Add XP to a user and update their level. Creates user if they don't exist.

        :param user_id: The ID of the user.
        :param server_id: The ID of the server.
        :param xp_amount: Amount of XP to add.
        :param current_time: Current timestamp for last_xp_time.
        :return: Tuple of (new_xp, new_level, old_level, leveled_up).
        """
        # Get current data
        data = await self.get_user_level_data(user_id, server_id)

        if data is None:
            # Create new user
            new_xp = xp_amount
            new_level = self._calculate_level(new_xp)
            await self.connection.execute(
                "INSERT INTO levels (user_id, server_id, xp, level, total_messages, last_xp_time) VALUES (?, ?, ?, ?, 1, ?)",
                (user_id, server_id, new_xp, new_level, current_time),
            )
            await self.connection.commit()
            return (new_xp, new_level, 0, new_level > 0)
        else:
            # Update existing user
            old_level = data["level"]
            new_xp = max(0, data["xp"] + xp_amount)  # Ensure XP doesn't go negative
            new_level = self._calculate_level(new_xp)
            new_messages = data["total_messages"] + 1

            await self.connection.execute(
                "UPDATE levels SET xp=?, level=?, total_messages=?, last_xp_time=? WHERE user_id=? AND server_id=?",
                (new_xp, new_level, new_messages, current_time, user_id, server_id),
            )
            await self.connection.commit()
            return (new_xp, new_level, old_level, new_level > old_level)

    async def set_xp(self, user_id: int, server_id: int, xp_amount: int) -> tuple:
        """
        Set a user's XP to a specific amount.

        :param user_id: The ID of the user.
        :param server_id: The ID of the server.
        :param xp_amount: XP amount to set.
        :return: Tuple of (new_xp, new_level).
        """
        xp_amount = max(0, xp_amount)  # Ensure XP is non-negative
        new_level = self._calculate_level(xp_amount)

        # Check if user exists
        data = await self.get_user_level_data(user_id, server_id)
        if data is None:
            # Create new user
            await self.connection.execute(
                "INSERT INTO levels (user_id, server_id, xp, level, total_messages) VALUES (?, ?, ?, ?, 0)",
                (user_id, server_id, xp_amount, new_level),
            )
        else:
            # Update existing user
            await self.connection.execute(
                "UPDATE levels SET xp=?, level=? WHERE user_id=? AND server_id=?",
                (xp_amount, new_level, user_id, server_id),
            )

        await self.connection.commit()
        return (xp_amount, new_level)

    async def reset_xp(self, user_id: int, server_id: int) -> bool:
        """
        Reset a user's XP and level to 0.

        :param user_id: The ID of the user.
        :param server_id: The ID of the server.
        :return: True if reset successful, False if user not found.
        """
        data = await self.get_user_level_data(user_id, server_id)
        if data is None:
            return False

        await self.connection.execute(
            "UPDATE levels SET xp=0, level=0 WHERE user_id=? AND server_id=?",
            (user_id, server_id),
        )
        await self.connection.commit()
        return True

    async def get_leaderboard(self, server_id: int, limit: int = 10, offset: int = 0) -> list:
        """
        Get the top users by XP for a server.

        :param server_id: The ID of the server.
        :param limit: Number of users to return.
        :param offset: Offset for pagination.
        :return: List of tuples (user_id, xp, level, total_messages).
        """
        rows = await self.connection.execute(
            "SELECT user_id, xp, level, total_messages FROM levels WHERE server_id=? ORDER BY xp DESC LIMIT ? OFFSET ?",
            (server_id, limit, offset),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            return result

    async def get_user_rank(self, user_id: int, server_id: int) -> int:
        """
        Get a user's rank position in the server (1-indexed).

        :param user_id: The ID of the user.
        :param server_id: The ID of the server.
        :return: User's rank position or 0 if not found.
        """
        rows = await self.connection.execute(
            "SELECT COUNT(*) + 1 FROM levels WHERE server_id=? AND xp > (SELECT xp FROM levels WHERE user_id=? AND server_id=?)",
            (server_id, user_id, server_id),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

    async def add_level_role(self, server_id: int, level: int, role_id: int) -> bool:
        """
        Add or update a role reward for a specific level.

        :param server_id: The ID of the server.
        :param level: The level to assign the role at.
        :param role_id: The ID of the role to assign.
        :return: True if successful.
        """
        await self.connection.execute(
            "INSERT OR REPLACE INTO level_roles (server_id, level, role_id) VALUES (?, ?, ?)",
            (server_id, level, role_id),
        )
        await self.connection.commit()
        return True

    async def remove_level_role(self, server_id: int, level: int) -> bool:
        """
        Remove a role reward for a specific level.

        :param server_id: The ID of the server.
        :param level: The level to remove the role from.
        :return: True if a role was removed, False if none existed.
        """
        cursor = await self.connection.execute(
            "DELETE FROM level_roles WHERE server_id=? AND level=?",
            (server_id, level),
        )
        await self.connection.commit()
        return cursor.rowcount > 0

    async def get_level_roles(self, server_id: int) -> list:
        """
        Get all level role rewards for a server, sorted by level.

        :param server_id: The ID of the server.
        :return: List of tuples (level, role_id).
        """
        rows = await self.connection.execute(
            "SELECT level, role_id FROM level_roles WHERE server_id=? ORDER BY level ASC",
            (server_id,),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            return result

    async def get_role_for_level(self, server_id: int, level: int) -> int:
        """
        Get the role ID for a specific level.

        :param server_id: The ID of the server.
        :param level: The level to check.
        :return: Role ID or None if no role is set for this level.
        """
        rows = await self.connection.execute(
            "SELECT role_id FROM level_roles WHERE server_id=? AND level=?",
            (server_id, level),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

    def _calculate_level(self, xp: int) -> int:
        """
        Calculate level from XP using exponential curve.
        Formula: Level = floor(0.1 * sqrt(XP))

        :param xp: The amount of XP.
        :return: The calculated level.
        """
        return int(0.1 * (xp**0.5))

    # ===== CLAUDE CONVERSATION METHODS =====

    async def add_claude_message(
        self, channel_id: int, user_id: int, role: str, content: str
    ) -> None:
        """
        Add a message to the Claude conversation history.
        Conversation history is shared across all users in a channel.

        :param channel_id: The ID of the channel.
        :param user_id: The ID of the user who sent the message.
        :param role: The role ('user' or 'assistant').
        :param content: The message content.
        """
        await self.connection.execute(
            "INSERT INTO claude_conversations (channel_id, user_id, role, content) VALUES (?, ?, ?, ?)",
            (channel_id, user_id, role, content),
        )
        await self.connection.commit()

    async def get_conversation_history(self, channel_id: int, limit: int = 20, user_id: int = None) -> list:
        """
        Get the conversation history for a channel.
        Returns messages in chronological order (oldest first).

        :param channel_id: The ID of the channel.
        :param limit: Maximum number of messages to retrieve.
        :param user_id: Optional user ID for personal conversation history. If None, returns shared channel history.
        :return: List of tuples (role, content).
        """
        if user_id is not None:
            # Personal conversation: filter by both channel_id and user_id
            rows = await self.connection.execute(
                "SELECT role, content FROM claude_conversations WHERE channel_id=? AND user_id=? ORDER BY id DESC LIMIT ?",
                (channel_id, user_id, limit),
            )
        else:
            # Shared conversation: filter by channel_id only
            rows = await self.connection.execute(
                "SELECT role, content FROM claude_conversations WHERE channel_id=? ORDER BY id DESC LIMIT ?",
                (channel_id, limit),
            )
        async with rows as cursor:
            result = await cursor.fetchall()
            # Reverse to get chronological order (oldest first)
            return list(reversed(result))

    async def clear_conversation(self, channel_id: int, user_id: int = None) -> int:
        """
        Clear conversation history for a channel.

        :param channel_id: The ID of the channel.
        :param user_id: Optional user ID for personal conversation history. If None, clears shared channel history.
        :return: Number of messages deleted.
        """
        if user_id is not None:
            # Personal conversation: delete by both channel_id and user_id
            cursor = await self.connection.execute(
                "DELETE FROM claude_conversations WHERE channel_id=? AND user_id=?",
                (channel_id, user_id),
            )
        else:
            # Shared conversation: delete by channel_id only
            cursor = await self.connection.execute(
                "DELETE FROM claude_conversations WHERE channel_id=?",
                (channel_id,),
            )
        await self.connection.commit()
        return cursor.rowcount

    async def get_total_messages(self, channel_id: int, user_id: int = None) -> int:
        """
        Get the total number of user messages (questions) in a conversation.
        Each user message represents one exchange/interaction.

        :param channel_id: The ID of the channel.
        :param user_id: Optional user ID for personal conversation. If None, returns shared channel count.
        :return: Total user message count (number of questions asked).
        """
        if user_id is not None:
            # Personal conversation: count user messages by both channel_id and user_id
            rows = await self.connection.execute(
                "SELECT COUNT(*) FROM claude_conversations WHERE channel_id=? AND user_id=? AND role='user'",
                (channel_id, user_id),
            )
        else:
            # Shared conversation: count user messages by channel_id only
            rows = await self.connection.execute(
                "SELECT COUNT(*) FROM claude_conversations WHERE channel_id=? AND role='user'",
                (channel_id,),
            )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

    # ===== AFFIRMATION METHODS =====

    async def get_affirmation_config(self, server_id: int) -> dict:
        """
        Get affirmation configuration for a server.

        :param server_id: The ID of the server.
        :return: Dictionary with configuration or None if not found.
        """
        rows = await self.connection.execute(
            "SELECT channel_id, post_time, timezone_offset, enabled, theme, last_post_date FROM affirmation_config WHERE server_id=?",
            (server_id,),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            if result:
                return {
                    "channel_id": int(result[0]),
                    "post_time": result[1],
                    "timezone_offset": result[2],
                    "enabled": bool(result[3]),
                    "theme": result[4],
                    "last_post_date": result[5],
                }
            return None

    async def set_affirmation_config(
        self, server_id: int, channel_id: int, post_time: str, timezone_offset: int, theme: str = "motivation"
    ) -> None:
        """
        Set affirmation configuration for a server.

        :param server_id: The ID of the server.
        :param channel_id: The ID of the channel to post to.
        :param post_time: Time to post (HH:MM format).
        :param timezone_offset: Timezone offset from UTC.
        :param theme: Theme for affirmations.
        """
        await self.connection.execute(
            "INSERT OR REPLACE INTO affirmation_config (server_id, channel_id, post_time, timezone_offset, enabled, theme) VALUES (?, ?, ?, ?, 1, ?)",
            (server_id, channel_id, post_time, timezone_offset, theme),
        )
        await self.connection.commit()

    async def toggle_affirmations(self, server_id: int, enabled: bool) -> bool:
        """
        Enable or disable daily affirmations for a server.

        :param server_id: The ID of the server.
        :param enabled: True to enable, False to disable.
        :return: True if successful, False if config not found.
        """
        cursor = await self.connection.execute(
            "UPDATE affirmation_config SET enabled=? WHERE server_id=?",
            (enabled, server_id),
        )
        await self.connection.commit()
        return cursor.rowcount > 0

    async def update_last_post_date(self, server_id: int, date_str: str) -> None:
        """
        Update the last post date for a server.

        :param server_id: The ID of the server.
        :param date_str: Date string (YYYY-MM-DD format).
        """
        await self.connection.execute(
            "UPDATE affirmation_config SET last_post_date=? WHERE server_id=?",
            (date_str, server_id),
        )
        await self.connection.commit()

    async def get_servers_needing_affirmations(self) -> list:
        """
        Get list of servers that have affirmations enabled.

        :return: List of tuples (server_id, channel_id, post_time, timezone_offset, theme, last_post_date).
        """
        rows = await self.connection.execute(
            "SELECT server_id, channel_id, post_time, timezone_offset, theme, last_post_date FROM affirmation_config WHERE enabled=1"
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            return result

    async def get_news_config(self, server_id: int) -> list:
        """
        Get all news configurations for a server (supports multiple times).

        :param server_id: The server ID.
        :return: List of dictionaries with news configuration, or empty list if not configured.
        """
        rows = await self.connection.execute(
            "SELECT channel_id, post_time, timezone_offset, enabled, last_post_date FROM news_config WHERE server_id=?",
            (server_id,),
        )
        async with rows as cursor:
            results = await cursor.fetchall()
            configs = []
            for result in results:
                configs.append({
                    "channel_id": result[0],
                    "post_time": result[1],
                    "timezone_offset": result[2],
                    "enabled": bool(result[3]),
                    "last_post_date": result[4],
                })
            return configs

    async def set_news_config(
        self, server_id: int, channel_id: int, post_time: str, timezone_offset: int = 0
    ) -> None:
        """
        Set or update news configuration for a server.

        :param server_id: The server ID.
        :param channel_id: The channel ID where news will be posted.
        :param post_time: Time to post news in HH:MM format (24-hour).
        :param timezone_offset: Timezone offset in hours from UTC.
        """
        await self.connection.execute(
            "INSERT OR REPLACE INTO news_config (server_id, channel_id, post_time, timezone_offset, enabled) VALUES (?, ?, ?, ?, 1)",
            (server_id, channel_id, post_time, timezone_offset),
        )
        await self.connection.commit()

    async def toggle_news(self, server_id: int, enabled: bool) -> bool:
        """
        Toggle news updates on or off for a server.

        :param server_id: The server ID.
        :param enabled: Whether to enable (True) or disable (False) news updates.
        :return: True if successful, False if server not configured.
        """
        result = await self.connection.execute(
            "UPDATE news_config SET enabled=? WHERE server_id=?",
            (1 if enabled else 0, server_id),
        )
        await self.connection.commit()
        return result.rowcount > 0

    async def update_last_news_post(self, server_id: int, post_time: str, date_str: str) -> None:
        """
        Update the last post date for a specific news update time.

        :param server_id: The server ID.
        :param post_time: The specific post time being updated (HH:MM format).
        :param date_str: Date string in YYYY-MM-DD format.
        """
        await self.connection.execute(
            "UPDATE news_config SET last_post_date=? WHERE server_id=? AND post_time=?",
            (date_str, server_id, post_time),
        )
        await self.connection.commit()

    async def count_news_times(self, server_id: int) -> int:
        """
        Count how many post times are configured for a server.

        :param server_id: The server ID.
        :return: Number of configured post times.
        """
        rows = await self.connection.execute(
            "SELECT COUNT(*) FROM news_config WHERE server_id=?",
            (server_id,),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

    async def remove_news_time(self, server_id: int, post_time: str) -> bool:
        """
        Remove a specific post time for a server.

        :param server_id: The server ID.
        :param post_time: The post time to remove (HH:MM format).
        :return: True if removed, False if not found.
        """
        result = await self.connection.execute(
            "DELETE FROM news_config WHERE server_id=? AND post_time=?",
            (server_id, post_time),
        )
        await self.connection.commit()
        return result.rowcount > 0

    async def get_servers_needing_news(self) -> list:
        """
        Get list of servers that have news updates enabled.

        :return: List of tuples (server_id, channel_id, post_time, timezone_offset, last_post_date).
        """
        rows = await self.connection.execute(
            "SELECT server_id, channel_id, post_time, timezone_offset, last_post_date FROM news_config WHERE enabled=1"
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            return result

    async def add_news_source(self, server_id: int, source_name: str, rss_url: str) -> None:
        """
        Add a news source for a server.

        :param server_id: The server ID.
        :param source_name: The name of the news source.
        :param rss_url: The RSS feed URL.
        """
        await self.connection.execute(
            "INSERT INTO news_sources (server_id, source_name, rss_url) VALUES (?, ?, ?)",
            (server_id, source_name, rss_url),
        )
        await self.connection.commit()

    async def remove_news_source(self, server_id: int, source_name: str) -> bool:
        """
        Remove a news source for a server.

        :param server_id: The server ID.
        :param source_name: The name of the news source to remove.
        :return: True if source was removed, False if not found.
        """
        result = await self.connection.execute(
            "DELETE FROM news_sources WHERE server_id=? AND source_name=?",
            (server_id, source_name),
        )
        await self.connection.commit()
        return result.rowcount > 0

    async def get_news_sources(self, server_id: int) -> list:
        """
        Get all news sources for a server.

        :param server_id: The server ID.
        :return: List of tuples (source_name, rss_url).
        """
        rows = await self.connection.execute(
            "SELECT source_name, rss_url FROM news_sources WHERE server_id=?",
            (server_id,),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            return result

    async def is_article_posted(self, server_id: int, article_id: str) -> bool:
        """
        Check if an article has already been posted to a server.

        :param server_id: The server ID.
        :param article_id: The article identifier (usually GUID or link).
        :return: True if article has been posted, False otherwise.
        """
        rows = await self.connection.execute(
            "SELECT 1 FROM posted_articles WHERE server_id=? AND article_id=?",
            (server_id, article_id),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result is not None

    async def mark_article_posted(self, server_id: int, article_id: str) -> None:
        """
        Mark an article as posted for a server.

        :param server_id: The server ID.
        :param article_id: The article identifier (usually GUID or link).
        """
        await self.connection.execute(
            "INSERT OR IGNORE INTO posted_articles (server_id, article_id) VALUES (?, ?)",
            (server_id, article_id),
        )
        await self.connection.commit()

    async def cleanup_old_articles(self, days: int = 30) -> None:
        """
        Remove article tracking records older than specified days.

        :param days: Number of days to keep article records (default 30).
        """
        await self.connection.execute(
            "DELETE FROM posted_articles WHERE posted_at < datetime('now', '-' || ? || ' days')",
            (days,),
        )
        await self.connection.commit()

    # ===== VIBES (MEMORIES + QOTD) METHODS =====

    async def get_vibes_config(self, server_id: int) -> dict:
        """
        Get vibes configuration for a server.

        :param server_id: The server ID.
        :return: Configuration dict or None if not configured.
        """
        rows = await self.connection.execute(
            "SELECT memory_emoji, qotd_enabled, throwback_enabled, auto_suggest_memories FROM vibes_config WHERE server_id=?",
            (server_id,),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            if result:
                return {
                    "memory_emoji": result[0],
                    "qotd_enabled": bool(result[1]),
                    "throwback_enabled": bool(result[2]),
                    "auto_suggest_memories": bool(result[3]),
                }
            return None

    async def set_memory_emoji(self, server_id: int, emoji: str) -> None:
        """
        Set or update the memory emoji for a server.

        :param server_id: The server ID.
        :param emoji: The emoji string (can be unicode or custom emoji format).
        """
        await self.connection.execute(
            "INSERT INTO vibes_config (server_id, memory_emoji) VALUES (?, ?) "
            "ON CONFLICT(server_id) DO UPDATE SET memory_emoji=?",
            (server_id, emoji, emoji),
        )
        await self.connection.commit()

    async def toggle_vibes_feature(
        self, server_id: int, feature: str, enabled: bool
    ) -> bool:
        """
        Toggle a vibes feature on or off.

        :param server_id: The server ID.
        :param feature: Feature name ('qotd', 'throwback', 'auto_suggest').
        :param enabled: True to enable, False to disable.
        :return: True if successful, False otherwise.
        """
        column_map = {
            "qotd": "qotd_enabled",
            "throwback": "throwback_enabled",
            "auto_suggest": "auto_suggest_memories",
        }
        column = column_map.get(feature)
        if not column:
            return False

        await self.connection.execute(
            f"INSERT INTO vibes_config (server_id, {column}) VALUES (?, ?) "
            f"ON CONFLICT(server_id) DO UPDATE SET {column}=?",
            (server_id, int(enabled), int(enabled)),
        )
        await self.connection.commit()
        return True

    async def save_memory(
        self,
        server_id: int,
        message_id: int,
        channel_id: int,
        author_id: int,
        saved_by_id: int,
        content: str,
        context_before: str = None,
        context_after: str = None,
        save_reason: str = "manual",
        category: str = None,
        reactions_count: int = 0,
    ) -> bool:
        """
        Save a message as a memory.

        :param server_id: The server ID.
        :param message_id: The message ID.
        :param channel_id: The channel ID where the message was posted.
        :param author_id: The author of the message.
        :param saved_by_id: The user who saved the memory.
        :param content: The message content.
        :param context_before: Previous messages for context.
        :param context_after: Following messages for context.
        :param save_reason: Why it was saved ('manual', 'reaction', 'qotd', 'ai_suggested').
        :param category: Optional category tag.
        :param reactions_count: Number of reactions the message had.
        :return: True if saved successfully, False if already exists.
        """
        try:
            await self.connection.execute(
                """INSERT INTO memories (
                    server_id, message_id, channel_id, author_id, saved_by_id,
                    content, context_before, context_after, save_reason, category, reactions_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    server_id,
                    message_id,
                    channel_id,
                    author_id,
                    saved_by_id,
                    content,
                    context_before,
                    context_after,
                    save_reason,
                    category,
                    reactions_count,
                ),
            )
            await self.connection.commit()
            return True
        except aiosqlite.IntegrityError:
            # Memory already exists
            return False

    async def get_memories(
        self,
        server_id: int,
        limit: int = 50,
        category: str = None,
        author_id: int = None,
        search_query: str = None,
    ) -> list:
        """
        Get memories for a server with optional filtering.

        :param server_id: The server ID.
        :param limit: Maximum number of memories to return.
        :param category: Optional category filter.
        :param author_id: Optional filter by message author.
        :param search_query: Optional text search in content.
        :return: List of memory dicts.
        """
        query = "SELECT id, message_id, channel_id, author_id, saved_by_id, content, save_reason, category, reactions_count, created_at, saved_at FROM memories WHERE server_id=?"
        params = [server_id]

        if category:
            query += " AND category=?"
            params.append(category)

        if author_id:
            query += " AND author_id=?"
            params.append(author_id)

        if search_query:
            query += " AND content LIKE ?"
            params.append(f"%{search_query}%")

        query += " ORDER BY saved_at DESC LIMIT ?"
        params.append(limit)

        rows = await self.connection.execute(query, tuple(params))
        async with rows as cursor:
            result = await cursor.fetchall()
            memories = []
            for row in result:
                memories.append(
                    {
                        "id": row[0],
                        "message_id": row[1],
                        "channel_id": row[2],
                        "author_id": row[3],
                        "saved_by_id": row[4],
                        "content": row[5],
                        "save_reason": row[6],
                        "category": row[7],
                        "reactions_count": row[8],
                        "created_at": row[9],
                        "saved_at": row[10],
                    }
                )
            return memories

    async def get_random_memory(self, server_id: int) -> dict:
        """
        Get a random memory from the server.

        :param server_id: The server ID.
        :return: Memory dict or None if no memories exist.
        """
        rows = await self.connection.execute(
            """SELECT id, message_id, channel_id, author_id, saved_by_id, content,
               save_reason, category, reactions_count, created_at, saved_at
               FROM memories WHERE server_id=? ORDER BY RANDOM() LIMIT 1""",
            (server_id,),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            if result:
                return {
                    "id": result[0],
                    "message_id": result[1],
                    "channel_id": result[2],
                    "author_id": result[3],
                    "saved_by_id": result[4],
                    "content": result[5],
                    "save_reason": result[6],
                    "category": result[7],
                    "reactions_count": result[8],
                    "created_at": result[9],
                    "saved_at": result[10],
                }
            return None

    async def get_memory_stats(self, server_id: int) -> dict:
        """
        Get statistics about memories for a server.

        :param server_id: The server ID.
        :return: Stats dict with counts and top contributors.
        """
        # Total memories
        rows = await self.connection.execute(
            "SELECT COUNT(*) FROM memories WHERE server_id=?", (server_id,)
        )
        async with rows as cursor:
            total = (await cursor.fetchone())[0]

        # Top saver
        rows = await self.connection.execute(
            "SELECT saved_by_id, COUNT(*) as count FROM memories WHERE server_id=? GROUP BY saved_by_id ORDER BY count DESC LIMIT 1",
            (server_id,),
        )
        async with rows as cursor:
            top_saver_result = await cursor.fetchone()
            top_saver = (
                {"user_id": top_saver_result[0], "count": top_saver_result[1]}
                if top_saver_result
                else None
            )

        # Most quoted person
        rows = await self.connection.execute(
            "SELECT author_id, COUNT(*) as count FROM memories WHERE server_id=? GROUP BY author_id ORDER BY count DESC LIMIT 1",
            (server_id,),
        )
        async with rows as cursor:
            most_quoted_result = await cursor.fetchone()
            most_quoted = (
                {"user_id": most_quoted_result[0], "count": most_quoted_result[1]}
                if most_quoted_result
                else None
            )

        # Categories breakdown
        rows = await self.connection.execute(
            "SELECT category, COUNT(*) as count FROM memories WHERE server_id=? AND category IS NOT NULL GROUP BY category ORDER BY count DESC",
            (server_id,),
        )
        async with rows as cursor:
            categories = await cursor.fetchall()

        return {
            "total_memories": total,
            "top_saver": top_saver,
            "most_quoted": most_quoted,
            "categories": [{"category": cat[0], "count": cat[1]} for cat in categories],
        }

    async def delete_memory(self, server_id: int, memory_id: int) -> bool:
        """
        Delete a memory.

        :param server_id: The server ID.
        :param memory_id: The memory ID.
        :return: True if deleted, False if not found.
        """
        cursor = await self.connection.execute(
            "DELETE FROM memories WHERE server_id=? AND id=?", (server_id, memory_id)
        )
        await self.connection.commit()
        return cursor.rowcount > 0

    # QOTD Methods

    async def set_qotd_schedule(
        self, server_id: int, channel_id: int, post_time: str, timezone_offset: int
    ) -> None:
        """
        Set or update QOTD schedule for a server.

        :param server_id: The server ID.
        :param channel_id: The channel to post questions in.
        :param post_time: Time in HH:MM format.
        :param timezone_offset: Timezone offset from UTC.
        """
        await self.connection.execute(
            "INSERT INTO qotd_schedule (server_id, channel_id, post_time, timezone_offset) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(server_id) DO UPDATE SET channel_id=?, post_time=?, timezone_offset=?",
            (
                server_id,
                channel_id,
                post_time,
                timezone_offset,
                channel_id,
                post_time,
                timezone_offset,
            ),
        )
        await self.connection.commit()

        # Also enable QOTD in vibes config
        await self.toggle_vibes_feature(server_id, "qotd", True)

    async def get_qotd_schedule(self, server_id: int) -> dict:
        """
        Get QOTD schedule for a server.

        :param server_id: The server ID.
        :return: Schedule dict or None if not configured.
        """
        rows = await self.connection.execute(
            "SELECT channel_id, post_time, timezone_offset, last_post_date FROM qotd_schedule WHERE server_id=?",
            (server_id,),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            if result:
                return {
                    "channel_id": result[0],
                    "post_time": result[1],
                    "timezone_offset": result[2],
                    "last_post_date": result[3],
                }
            return None

    async def get_servers_needing_qotd(self) -> list:
        """
        Get all servers that need QOTD posts (enabled and within time window).

        :return: List of (server_id, channel_id, post_time, timezone_offset, last_post_date) tuples.
        """
        rows = await self.connection.execute(
            """SELECT q.server_id, q.channel_id, q.post_time, q.timezone_offset, q.last_post_date
               FROM qotd_schedule q
               JOIN vibes_config v ON q.server_id = v.server_id
               WHERE v.qotd_enabled = 1"""
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            return result

    async def update_qotd_last_post(self, server_id: int, date_str: str) -> None:
        """
        Update the last post date for QOTD.

        :param server_id: The server ID.
        :param date_str: Date string in YYYY-MM-DD format.
        """
        await self.connection.execute(
            "UPDATE qotd_schedule SET last_post_date=? WHERE server_id=?",
            (date_str, server_id),
        )
        await self.connection.commit()

    async def add_qotd_question(
        self,
        question: str,
        category: str = "random",
        is_custom: bool = False,
        submitted_by_id: int = None,
        server_id: int = None,
    ) -> int:
        """
        Add a question to the pool.

        :param question: The question text.
        :param category: Question category.
        :param is_custom: Whether this is a user-submitted question.
        :param submitted_by_id: User ID who submitted (if custom).
        :param server_id: Server ID (for custom questions, None for global).
        :return: The question ID.
        """
        cursor = await self.connection.execute(
            "INSERT INTO qotd_questions (server_id, question, category, is_custom, submitted_by_id) VALUES (?, ?, ?, ?, ?)",
            (server_id, question, category, int(is_custom), submitted_by_id),
        )
        await self.connection.commit()
        return cursor.lastrowid

    async def get_next_qotd_question(self, server_id: int, category: str = None) -> dict:
        """
        Get the next question to ask (least recently asked or never asked).

        :param server_id: The server ID.
        :param category: Optional category filter.
        :return: Question dict or None if no questions available.
        """
        query = "SELECT id, question, category FROM qotd_questions WHERE (server_id=? OR server_id IS NULL)"
        params = [server_id]

        if category:
            query += " AND category=?"
            params.append(category)

        query += " ORDER BY times_asked ASC, last_asked_date ASC NULLS FIRST LIMIT 1"

        rows = await self.connection.execute(query, tuple(params))
        async with rows as cursor:
            result = await cursor.fetchone()
            if result:
                return {"id": result[0], "question": result[1], "category": result[2]}
            return None

    async def mark_question_asked(
        self, question_id: int, date_str: str, reactions_count: int = 0
    ) -> None:
        """
        Mark a question as asked and update its statistics.

        :param question_id: The question ID.
        :param date_str: Date string in YYYY-MM-DD format.
        :param reactions_count: Number of reactions received.
        """
        await self.connection.execute(
            "UPDATE qotd_questions SET times_asked = times_asked + 1, last_asked_date=?, total_reactions = total_reactions + ? WHERE id=?",
            (date_str, reactions_count, question_id),
        )
        await self.connection.commit()

    # ===== RECIPE METHODS =====

    async def save_recipe(
        self,
        user_id: int,
        recipe_name: str,
        recipe_data: str,
        cuisine: str = None,
        dietary: str = None,
        difficulty: str = None,
    ) -> int:
        """
        Save a recipe to the user's personal collection.

        :param user_id: The ID of the user saving the recipe.
        :param recipe_name: The name of the recipe.
        :param recipe_data: Full recipe data as JSON string.
        :param cuisine: Optional cuisine type.
        :param dietary: Optional dietary restriction.
        :param difficulty: Optional difficulty level.
        :return: The recipe ID.
        """
        cursor = await self.connection.execute(
            "INSERT INTO saved_recipes (user_id, recipe_name, recipe_data, cuisine, dietary, difficulty) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, recipe_name, recipe_data, cuisine, dietary, difficulty),
        )
        await self.connection.commit()
        return cursor.lastrowid

    async def get_user_recipes(
        self, user_id: int, limit: int = 5, offset: int = 0
    ) -> list:
        """
        Get recipes saved by a user with pagination.

        :param user_id: The ID of the user.
        :param limit: Maximum number of recipes to return (default 5 for pagination).
        :param offset: Offset for pagination (default 0).
        :return: List of recipe dicts.
        """
        rows = await self.connection.execute(
            "SELECT id, recipe_name, recipe_data, cuisine, dietary, difficulty, created_at FROM saved_recipes WHERE user_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (user_id, limit, offset),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            recipes = []
            for row in result:
                recipes.append(
                    {
                        "id": row[0],
                        "recipe_name": row[1],
                        "recipe_data": row[2],
                        "cuisine": row[3],
                        "dietary": row[4],
                        "difficulty": row[5],
                        "created_at": row[6],
                    }
                )
            return recipes

    async def count_user_recipes(self, user_id: int) -> int:
        """
        Count total recipes saved by a user.

        :param user_id: The ID of the user.
        :return: Total number of saved recipes.
        """
        rows = await self.connection.execute(
            "SELECT COUNT(*) FROM saved_recipes WHERE user_id=?", (user_id,)
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

    async def delete_recipe(self, user_id: int, recipe_id: int) -> bool:
        """
        Delete a recipe from user's collection.

        :param user_id: The ID of the user (for security check).
        :param recipe_id: The recipe ID to delete.
        :return: True if deleted, False if not found or not owned by user.
        """
        cursor = await self.connection.execute(
            "DELETE FROM saved_recipes WHERE id=? AND user_id=?",
            (recipe_id, user_id),
        )
        await self.connection.commit()
        return cursor.rowcount > 0

    async def get_recipe_daily_config(self, server_id: int) -> dict:
        """
        Get daily recipe configuration for a server.

        :param server_id: The ID of the server.
        :return: Dictionary with configuration or None if not found.
        """
        rows = await self.connection.execute(
            "SELECT channel_id, post_time, timezone_offset, enabled, cuisine_preference, dietary_preference, last_post_date FROM recipe_daily_config WHERE server_id=?",
            (server_id,),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            if result:
                return {
                    "channel_id": int(result[0]),
                    "post_time": result[1],
                    "timezone_offset": result[2],
                    "enabled": bool(result[3]),
                    "cuisine_preference": result[4],
                    "dietary_preference": result[5],
                    "last_post_date": result[6],
                }
            return None

    async def set_recipe_daily_config(
        self,
        server_id: int,
        channel_id: int,
        post_time: str,
        timezone_offset: int = 0,
        cuisine_preference: str = "random",
        dietary_preference: str = "none",
    ) -> None:
        """
        Set daily recipe configuration for a server.

        :param server_id: The ID of the server.
        :param channel_id: The ID of the channel to post to.
        :param post_time: Time to post (HH:MM format).
        :param timezone_offset: Timezone offset from UTC.
        :param cuisine_preference: Preferred cuisine type.
        :param dietary_preference: Preferred dietary restriction.
        """
        await self.connection.execute(
            "INSERT OR REPLACE INTO recipe_daily_config (server_id, channel_id, post_time, timezone_offset, enabled, cuisine_preference, dietary_preference) VALUES (?, ?, ?, ?, 1, ?, ?)",
            (
                server_id,
                channel_id,
                post_time,
                timezone_offset,
                cuisine_preference,
                dietary_preference,
            ),
        )
        await self.connection.commit()

    async def toggle_recipe_daily(self, server_id: int, enabled: bool) -> bool:
        """
        Enable or disable daily recipe posts for a server.

        :param server_id: The ID of the server.
        :param enabled: True to enable, False to disable.
        :return: True if successful, False if config not found.
        """
        cursor = await self.connection.execute(
            "UPDATE recipe_daily_config SET enabled=? WHERE server_id=?",
            (enabled, server_id),
        )
        await self.connection.commit()
        return cursor.rowcount > 0

    async def update_recipe_last_post(self, server_id: int, date_str: str) -> None:
        """
        Update the last post date for daily recipes.

        :param server_id: The ID of the server.
        :param date_str: Date string in YYYY-MM-DD format.
        """
        await self.connection.execute(
            "UPDATE recipe_daily_config SET last_post_date=? WHERE server_id=?",
            (date_str, server_id),
        )
        await self.connection.commit()

    async def get_servers_needing_recipe_post(self) -> list:
        """
        Get list of servers that have daily recipe posts enabled.

        :return: List of tuples (server_id, channel_id, post_time, timezone_offset, cuisine_preference, dietary_preference, last_post_date).
        """
        rows = await self.connection.execute(
            "SELECT server_id, channel_id, post_time, timezone_offset, cuisine_preference, dietary_preference, last_post_date FROM recipe_daily_config WHERE enabled=1"
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            return result

    # ===== ART DISCOVERY METHODS =====

    async def get_art_config(self, server_id: int) -> tuple:
        """
        Get art configuration for a server.

        :param server_id: The ID of the server.
        :return: Tuple with configuration or None if not found.
        """
        rows = await self.connection.execute(
            "SELECT server_id, channel_id, post_time, timezone_offset, enabled, last_post_date, focus_areas, include_contemporary FROM art_config WHERE server_id=?",
            (server_id,),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result

    async def setup_art_config(
        self,
        server_id: int,
        channel_id: int,
        post_time: str,
        timezone_offset: int = 0,
        focus_areas: str = "all",
        include_contemporary: bool = True,
    ) -> None:
        """
        Setup or update art configuration for a server.

        :param server_id: The ID of the server.
        :param channel_id: The ID of the channel to post to.
        :param post_time: Time to post (HH:MM format).
        :param timezone_offset: Timezone offset from UTC.
        :param focus_areas: Focus areas for art selection.
        :param include_contemporary: Whether to include contemporary art.
        """
        await self.connection.execute(
            "INSERT OR REPLACE INTO art_config (server_id, channel_id, post_time, timezone_offset, enabled, focus_areas, include_contemporary) VALUES (?, ?, ?, ?, 1, ?, ?)",
            (
                server_id,
                channel_id,
                post_time,
                timezone_offset,
                focus_areas,
                int(include_contemporary),
            ),
        )
        await self.connection.commit()

    async def toggle_art_enabled(self, server_id: int, enabled: bool) -> bool:
        """
        Enable or disable daily art posts for a server.

        :param server_id: The ID of the server.
        :param enabled: True to enable, False to disable.
        :return: True if successful, False if config not found.
        """
        cursor = await self.connection.execute(
            "UPDATE art_config SET enabled=? WHERE server_id=?", (enabled, server_id)
        )
        await self.connection.commit()
        return cursor.rowcount > 0

    async def update_art_last_post_date(self, server_id: int, date_str: str) -> None:
        """
        Update the last post date for art posts.

        :param server_id: The ID of the server.
        :param date_str: Date string in YYYY-MM-DD format.
        """
        await self.connection.execute(
            "UPDATE art_config SET last_post_date=? WHERE server_id=?",
            (date_str, server_id),
        )
        await self.connection.commit()

    async def get_servers_needing_art(self) -> list:
        """
        Get list of servers that have daily art posts enabled.

        :return: List of tuples (server_id, channel_id, post_time, timezone_offset, last_post_date).
        """
        rows = await self.connection.execute(
            "SELECT server_id, channel_id, post_time, timezone_offset, last_post_date FROM art_config WHERE enabled=1"
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            return result

    async def save_art_favorite(
        self,
        user_id: int,
        server_id: int,
        artwork_title: str,
        artist: str,
        museum: str,
        image_url: str = None,
        artwork_url: str = None,
    ) -> int:
        """
        Save an artwork to a user's favorites.

        :param user_id: The ID of the user.
        :param server_id: The ID of the server.
        :param artwork_title: Title of the artwork.
        :param artist: Artist name.
        :param museum: Museum name.
        :param image_url: URL of the artwork image.
        :param artwork_url: URL to the artwork page.
        :return: The favorite ID.
        """
        cursor = await self.connection.execute(
            "INSERT INTO art_favorites (user_id, server_id, artwork_title, artist, museum, image_url, artwork_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, server_id, artwork_title, artist, museum, image_url, artwork_url),
        )
        await self.connection.commit()
        return cursor.lastrowid

    async def get_user_art_favorites(
        self, user_id: int, server_id: int, limit: int = 10
    ) -> list:
        """
        Get a user's favorite artworks.

        :param user_id: The ID of the user.
        :param server_id: The ID of the server.
        :param limit: Maximum number of favorites to return.
        :return: List of favorite dicts.
        """
        rows = await self.connection.execute(
            "SELECT id, artwork_title, artist, museum, image_url, artwork_url, saved_at FROM art_favorites WHERE user_id=? AND server_id=? ORDER BY saved_at DESC LIMIT ?",
            (user_id, server_id, limit),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            favorites = []
            for row in result:
                favorites.append(
                    {
                        "id": row[0],
                        "artwork_title": row[1],
                        "artist": row[2],
                        "museum": row[3],
                        "image_url": row[4],
                        "artwork_url": row[5],
                        "saved_at": row[6],
                    }
                )
            return favorites

    async def get_cached_art_analysis(self, artwork_url: str) -> dict:
        """
        Get cached art analysis for an artwork.

        :param artwork_url: The museum URL for the artwork.
        :return: Dictionary with cached data or None if not found.
        """
        rows = await self.connection.execute(
            "SELECT id, image_url, artwork_title, artist, museum, vision_story, analysis_model, created_at, last_used_at FROM art_analysis_cache WHERE artwork_url=?",
            (artwork_url,),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            if result:
                return {
                    "id": result[0],
                    "image_url": result[1],
                    "artwork_title": result[2],
                    "artist": result[3],
                    "museum": result[4],
                    "vision_story": result[5],
                    "analysis_model": result[6],
                    "created_at": result[7],
                    "last_used_at": result[8],
                }
            return None

    async def save_art_analysis(
        self,
        artwork_url: str,
        image_url: str,
        artwork_title: str,
        artist: str,
        museum: str,
        vision_story: str,
    ) -> int:
        """
        Save artwork analysis to cache.

        :param artwork_url: Museum URL for the artwork (unique key).
        :param image_url: URL of the artwork image.
        :param artwork_title: Title of the artwork.
        :param artist: Artist name.
        :param museum: Museum name.
        :param vision_story: Generated vision story.
        :return: The cache entry ID.
        """
        cursor = await self.connection.execute(
            "INSERT OR REPLACE INTO art_analysis_cache (artwork_url, image_url, artwork_title, artist, museum, vision_story) VALUES (?, ?, ?, ?, ?, ?)",
            (artwork_url, image_url, artwork_title, artist, museum, vision_story),
        )
        await self.connection.commit()
        return cursor.lastrowid

    async def update_art_analysis_last_used(self, artwork_url: str) -> None:
        """
        Update the last_used_at timestamp for a cached analysis.

        :param artwork_url: Museum URL for the artwork.
        """
        await self.connection.execute(
            "UPDATE art_analysis_cache SET last_used_at=CURRENT_TIMESTAMP WHERE artwork_url=?",
            (artwork_url,),
        )
        await self.connection.commit()
