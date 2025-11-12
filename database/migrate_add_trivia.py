"""
Migration script to add trivia system tables to existing database.

Run this script once to add the new tables without affecting existing data.
"""

import asyncio
import aiosqlite


async def migrate():
    """Add trivia tables to the database."""
    print("Starting trivia migration...")

    async with aiosqlite.connect("database/database.db") as db:
        # Check if tables already exist
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='trivia_config'"
        )
        result = await cursor.fetchone()

        if result:
            print("⚠️  Trivia tables already exist! Skipping migration.")
            return

        print("Creating trivia_config table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS `trivia_config` (
              `server_id` varchar(20) NOT NULL PRIMARY KEY,
              `channel_id` varchar(20) NOT NULL,
              `post_time` varchar(5) NOT NULL,
              `timezone_offset` int DEFAULT 0,
              `enabled` boolean NOT NULL DEFAULT 1,
              `last_post_date` varchar(10) DEFAULT NULL,
              `questions_per_game` int DEFAULT 5,
              `difficulty` varchar(20) DEFAULT 'medium'
            )
        """)

        print("Creating trivia_scores table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS `trivia_scores` (
              `server_id` varchar(20) NOT NULL,
              `user_id` varchar(20) NOT NULL,
              `total_correct` int DEFAULT 0,
              `total_answered` int DEFAULT 0,
              `current_streak` int DEFAULT 0,
              `best_streak` int DEFAULT 0,
              `total_points` int DEFAULT 0,
              `last_played` timestamp DEFAULT NULL,
              PRIMARY KEY (`server_id`, `user_id`)
            )
        """)

        print("Creating trivia_history table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS `trivia_history` (
              `id` INTEGER PRIMARY KEY AUTOINCREMENT,
              `server_id` varchar(20) NOT NULL,
              `user_id` varchar(20) NOT NULL,
              `question` TEXT NOT NULL,
              `correct_answer` varchar(10) NOT NULL,
              `user_answer` varchar(10),
              `correct` boolean NOT NULL,
              `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `category` varchar(50) NOT NULL,
              `difficulty` varchar(20) NOT NULL,
              `points_earned` int DEFAULT 0
            )
        """)

        await db.commit()

        print("✅ Migration completed successfully!")
        print("\nNew features available:")
        print("  • Interactive Trivia Questions - Single or multi-question games")
        print("  • Server Leaderboards - Compete with other members")
        print("  • Personal Stats Tracking - Track your progress and streaks")
        print("  • Scheduled Daily Trivia - Automatic trivia games")
        print("\nUse /trivia to play or /trivia-schedule to configure daily games!")


if __name__ == "__main__":
    asyncio.run(migrate())
