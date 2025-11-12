"""
Migration script to add creative studio tables to existing database.

Run this script once to add the new tables without affecting existing data.
"""

import asyncio
import aiosqlite


async def migrate():
    """Add creative studio tables to the database."""
    print("Starting creative studio migration...")

    async with aiosqlite.connect("database/database.db") as db:
        # Check if tables already exist
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='creative_config'"
        )
        result = await cursor.fetchone()

        if result:
            print("⚠️  Creative studio tables already exist! Skipping migration.")
            return

        print("Creating creative_config table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS `creative_config` (
              `server_id` varchar(20) NOT NULL PRIMARY KEY,
              `channel_id` varchar(20) NOT NULL,
              `post_time` varchar(5) NOT NULL,
              `timezone_offset` int DEFAULT 0,
              `daily_prompts_enabled` boolean NOT NULL DEFAULT 1,
              `weekly_challenges_enabled` boolean NOT NULL DEFAULT 1,
              `last_daily_post` varchar(10) DEFAULT NULL,
              `last_weekly_post` varchar(10) DEFAULT NULL,
              `current_month_theme` varchar(100) DEFAULT NULL,
              `prompt_rotation` varchar(20) DEFAULT 'writing'
            )
        """)

        print("Creating collaborative_works table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS `collaborative_works` (
              `id` INTEGER PRIMARY KEY AUTOINCREMENT,
              `server_id` varchar(20) NOT NULL,
              `channel_id` varchar(20) NOT NULL,
              `thread_id` varchar(20) NOT NULL,
              `work_type` varchar(20) NOT NULL,
              `title` TEXT NOT NULL,
              `prompt` TEXT NOT NULL,
              `started_by_id` varchar(20) NOT NULL,
              `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `completed` boolean NOT NULL DEFAULT 0,
              `completed_at` timestamp DEFAULT NULL,
              `contribution_count` int DEFAULT 0
            )
        """)

        print("Creating work_contributions table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS `work_contributions` (
              `id` INTEGER PRIMARY KEY AUTOINCREMENT,
              `work_id` int NOT NULL,
              `user_id` varchar(20) NOT NULL,
              `content` TEXT NOT NULL,
              `contribution_number` int NOT NULL,
              `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `word_count` int DEFAULT 0,
              FOREIGN KEY (`work_id`) REFERENCES `collaborative_works`(`id`)
            )
        """)

        print("Creating creative_challenges table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS `creative_challenges` (
              `id` INTEGER PRIMARY KEY AUTOINCREMENT,
              `server_id` varchar(20) NOT NULL,
              `challenge_type` varchar(20) NOT NULL,
              `prompt` TEXT NOT NULL,
              `description` TEXT,
              `start_date` varchar(10) NOT NULL,
              `end_date` varchar(10) NOT NULL,
              `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `voting_enabled` boolean NOT NULL DEFAULT 1,
              `winner_id` varchar(20) DEFAULT NULL
            )
        """)

        print("Creating challenge_submissions table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS `challenge_submissions` (
              `id` INTEGER PRIMARY KEY AUTOINCREMENT,
              `challenge_id` int NOT NULL,
              `user_id` varchar(20) NOT NULL,
              `submission_text` TEXT NOT NULL,
              `submission_url` TEXT,
              `submitted_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `votes` int DEFAULT 0,
              FOREIGN KEY (`challenge_id`) REFERENCES `creative_challenges`(`id`),
              UNIQUE (`challenge_id`, `user_id`)
            )
        """)

        print("Creating creative_gallery table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS `creative_gallery` (
              `id` INTEGER PRIMARY KEY AUTOINCREMENT,
              `server_id` varchar(20) NOT NULL,
              `user_id` varchar(20) NOT NULL,
              `work_type` varchar(20) NOT NULL,
              `title` TEXT NOT NULL,
              `content` TEXT NOT NULL,
              `image_url` TEXT,
              `reactions` int DEFAULT 0,
              `showcased_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `collaborative_work_id` int DEFAULT NULL,
              FOREIGN KEY (`collaborative_work_id`) REFERENCES `collaborative_works`(`id`)
            )
        """)

        await db.commit()

        print("✅ Migration completed successfully!")
        print("\nNew features available:")
        print("  • Writing Prompts - Story ideas, writing exercises, collaborative stories")
        print("  • Music Prompts - Songwriting, chord progressions, lyrics, theory help")
        print("  • Art Prompts - Drawing ideas, style challenges, color palettes, characters")
        print("  • Collaboration - Threaded projects with AI participation")
        print("  • Challenges - Weekly creative challenges with voting")
        print("  • Gallery - Showcase completed works")
        print("\nUse /story-prompt, /song-prompt, or /draw-prompt to get started!")


if __name__ == "__main__":
    asyncio.run(migrate())
