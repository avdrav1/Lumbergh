"""
Migration script to add 9 new high-quality news sources to all existing servers.

Run this script once to update the database:
    python database/migrate_add_9_sources.py
"""

import aiosqlite
import asyncio
import os


# The 9 new sources to add
NEW_SOURCES = [
    ("Washington Post", "https://feeds.washingtonpost.com/rss/homepage"),
    ("USA Today", "http://rssfeeds.usatoday.com/usatoday-NewsTopStories"),
    ("Los Angeles Times", "https://www.latimes.com/news/rss2.0.xml"),
    ("ABC News", "http://feeds.abcnews.com/abcnews/usheadlines"),
    ("CBS News", "https://www.cbsnews.com/latest/rss/main"),
    ("Politico", "https://rss.politico.com/politics-news.xml"),
    ("The Hill", "https://thehill.com/news/feed"),
    ("Deutsche Welle", "https://rss.dw.com/rdf/rss-en-all"),
    ("France 24", "https://www.france24.com/en/rss"),
]


async def migrate_add_9_sources():
    """Add 9 new news sources to all servers that have news sources configured."""

    # Get database path
    db_path = os.path.join(os.path.dirname(__file__), "database.db")

    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    print(f"📊 Connecting to database: {db_path}")
    print(f"📰 Adding {len(NEW_SOURCES)} new sources to all configured servers\n")

    async with aiosqlite.connect(db_path) as db:
        # Get all unique server_ids that have news sources configured
        cursor = await db.execute(
            "SELECT DISTINCT server_id FROM news_sources"
        )
        servers = await cursor.fetchall()

        if not servers:
            print("ℹ️  No servers found with news configured")
            return

        print(f"Found {len(servers)} server(s) with news configured\n")

        total_added = 0
        total_skipped = 0

        for (server_id,) in servers:
            print(f"🔧 Processing server {server_id}:")
            server_added = 0
            server_skipped = 0

            for source_name, rss_url in NEW_SOURCES:
                # Check if this server already has this source
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM news_sources WHERE server_id = ? AND source_name = ?",
                    (server_id, source_name)
                )
                count = (await cursor.fetchone())[0]

                if count > 0:
                    print(f"   ⏭️  {source_name}: Already exists, skipping")
                    server_skipped += 1
                    total_skipped += 1
                    continue

                # Add source to this server
                await db.execute(
                    "INSERT INTO news_sources (server_id, source_name, rss_url) VALUES (?, ?, ?)",
                    (server_id, source_name, rss_url)
                )
                print(f"   ✅ {source_name}: Added")
                server_added += 1
                total_added += 1

            print(f"   📊 Server summary: {server_added} added, {server_skipped} skipped\n")

        # Commit all changes
        await db.commit()

        print("=" * 60)
        print(f"✅ Migration complete!")
        print(f"   Total sources added: {total_added}")
        print(f"   Total sources skipped: {total_skipped} (already existed)")
        print(f"   Servers updated: {len(servers)}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(migrate_add_9_sources())
