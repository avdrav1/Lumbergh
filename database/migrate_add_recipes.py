"""
Migration script to add recipe tables to existing database.
Run this once to add recipe functionality.
"""

import aiosqlite
import asyncio


async def migrate():
    """Add recipe tables to the database."""
    async with aiosqlite.connect("database/database.db") as db:
        print("Adding saved_recipes table...")
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id varchar(20) NOT NULL,
                recipe_name TEXT NOT NULL,
                recipe_data TEXT NOT NULL,
                cuisine varchar(50),
                dietary varchar(50),
                difficulty varchar(20),
                created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        print("Adding recipe_daily_config table...")
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS recipe_daily_config (
                server_id varchar(20) NOT NULL PRIMARY KEY,
                channel_id varchar(20) NOT NULL,
                post_time varchar(5) NOT NULL,
                timezone_offset int DEFAULT 0,
                enabled boolean NOT NULL DEFAULT 1,
                cuisine_preference varchar(50) DEFAULT 'random',
                dietary_preference varchar(50) DEFAULT 'none',
                last_post_date varchar(10) DEFAULT NULL
            )
            """
        )

        await db.commit()
        print("✅ Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate())
