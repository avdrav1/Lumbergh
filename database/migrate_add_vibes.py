"""
Migration script to add vibes (Memory Bank + QOTD) tables to existing database.

Run this script once to add the new tables without affecting existing data.
"""

import asyncio
import aiosqlite


async def migrate():
    """Add vibes tables to the database."""
    print("Starting vibes migration...")

    async with aiosqlite.connect("database/database.db") as db:
        # Check if tables already exist
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='vibes_config'"
        )
        result = await cursor.fetchone()

        if result:
            print("⚠️  Vibes tables already exist! Skipping migration.")
            return

        print("Creating vibes_config table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS `vibes_config` (
              `server_id` varchar(20) NOT NULL PRIMARY KEY,
              `memory_emoji` varchar(100) DEFAULT '💾',
              `qotd_enabled` boolean NOT NULL DEFAULT 0,
              `throwback_enabled` boolean NOT NULL DEFAULT 1,
              `auto_suggest_memories` boolean NOT NULL DEFAULT 1
            )
        """)

        print("Creating memories table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS `memories` (
              `id` INTEGER PRIMARY KEY AUTOINCREMENT,
              `server_id` varchar(20) NOT NULL,
              `message_id` varchar(20) NOT NULL,
              `channel_id` varchar(20) NOT NULL,
              `author_id` varchar(20) NOT NULL,
              `saved_by_id` varchar(20) NOT NULL,
              `content` TEXT NOT NULL,
              `context_before` TEXT,
              `context_after` TEXT,
              `save_reason` varchar(20) DEFAULT 'manual',
              `category` varchar(50),
              `reactions_count` int DEFAULT 0,
              `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `saved_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
              UNIQUE (`server_id`, `message_id`)
            )
        """)

        print("Creating qotd_schedule table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS `qotd_schedule` (
              `server_id` varchar(20) NOT NULL PRIMARY KEY,
              `channel_id` varchar(20) NOT NULL,
              `post_time` varchar(5) NOT NULL,
              `timezone_offset` int DEFAULT 0,
              `last_post_date` varchar(10) DEFAULT NULL
            )
        """)

        print("Creating qotd_questions table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS `qotd_questions` (
              `id` INTEGER PRIMARY KEY AUTOINCREMENT,
              `server_id` varchar(20),
              `question` TEXT NOT NULL,
              `category` varchar(50) DEFAULT 'random',
              `is_custom` boolean NOT NULL DEFAULT 0,
              `submitted_by_id` varchar(20),
              `times_asked` int DEFAULT 0,
              `total_reactions` int DEFAULT 0,
              `last_asked_date` varchar(10) DEFAULT NULL,
              `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.commit()

        print("✅ Migration completed successfully!")
        print("\nNew features available:")
        print("  • Memory Bank - Save and browse memorable messages")
        print("  • Question of the Day - Scheduled daily questions")
        print("  • Throwback Posts - Random memory resurfacing")
        print("\nUse /vibes-setup to configure!")


if __name__ == "__main__":
    asyncio.run(migrate())
