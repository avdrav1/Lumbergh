"""
Migration script to add The New York Times to all existing servers with news configured.

Run this script once to update the database:
    python database/migrate_add_nyt.py
"""

import aiosqlite
import asyncio
import os


async def migrate_add_nyt():
    """Add NYT to all servers that have news sources configured."""

    # Get database path
    db_path = os.path.join(os.path.dirname(__file__), "database.db")

    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    print(f"📊 Connecting to database: {db_path}")

    async with aiosqlite.connect(db_path) as db:
        # Get all unique server_ids that have news sources configured
        cursor = await db.execute(
            "SELECT DISTINCT server_id FROM news_sources"
        )
        servers = await cursor.fetchall()

        if not servers:
            print("ℹ️  No servers found with news configured")
            return

        print(f"Found {len(servers)} server(s) with news configured")

        nyt_url = "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"
        nyt_name = "The New York Times"

        added_count = 0
        skipped_count = 0

        for (server_id,) in servers:
            # Check if this server already has NYT
            cursor = await db.execute(
                "SELECT COUNT(*) FROM news_sources WHERE server_id = ? AND source_name = ?",
                (server_id, nyt_name)
            )
            count = (await cursor.fetchone())[0]

            if count > 0:
                print(f"⏭️  Server {server_id}: Already has NYT, skipping")
                skipped_count += 1
                continue

            # Add NYT to this server
            await db.execute(
                "INSERT INTO news_sources (server_id, source_name, rss_url) VALUES (?, ?, ?)",
                (server_id, nyt_name, nyt_url)
            )
            print(f"✅ Server {server_id}: Added NYT")
            added_count += 1

        # Commit all changes
        await db.commit()

        print("\n" + "="*50)
        print(f"✅ Migration complete!")
        print(f"   Added NYT to {added_count} server(s)")
        print(f"   Skipped {skipped_count} server(s) (already had NYT)")
        print("="*50)


if __name__ == "__main__":
    asyncio.run(migrate_add_nyt())
