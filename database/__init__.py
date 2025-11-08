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
