"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized discord bot in Python programming language.

Version: 6.3.0
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ext.commands import Context
import feedparser
from datetime import datetime, timedelta
import re
import os
from anthropic import AsyncAnthropic
from typing import Literal


# Default news sources with RSS feeds
DEFAULT_SOURCES = {
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "CNN Top Stories": "http://rss.cnn.com/rss/cnn_topstories.rss",
    "ABC News": "http://feeds.abcnews.com/abcnews/usheadlines",
    "CBS News": "https://www.cbsnews.com/latest/rss/main",
    "Associated Press": "https://feeds.apnews.com/rss/apf-topnews",
    "Reuters World": "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best",
    "NPR News": "https://feeds.npr.org/1001/rss.xml",
    "The Guardian": "https://www.theguardian.com/world/rss",
    "The New York Times": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "Washington Post": "https://feeds.washingtonpost.com/rss/homepage",
    "USA Today": "http://rssfeeds.usatoday.com/usatoday-NewsTopStories",
    "Los Angeles Times": "https://www.latimes.com/news/rss2.0.xml",
    "Politico": "https://rss.politico.com/politics-news.xml",
    "The Hill": "https://thehill.com/news/feed",
    "Al Jazeera English": "https://www.aljazeera.com/xml/rss/all.xml",
    "Deutsche Welle": "https://rss.dw.com/rdf/rss-en-all",
    "France 24": "https://www.france24.com/en/rss",
    "TechCrunch": "https://techcrunch.com/feed/",
    "CNBC": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "Hacker News": "https://news.ycombinator.com/rss",
}


class News(commands.Cog, name="news"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.daily_news_task.start()

    def cog_unload(self) -> None:
        self.daily_news_task.cancel()

    @tasks.loop(minutes=15)
    async def daily_news_task(self) -> None:
        """
        Background task that checks every 15 minutes for servers needing news updates.
        """
        try:
            servers = await self.bot.database.get_servers_needing_news()

            for server_data in servers:
                server_id, channel_id, post_time, timezone_offset, last_post_date = (
                    server_data
                )

                # Get current UTC time and adjust for timezone
                now_utc = datetime.utcnow()
                server_time = now_utc + timedelta(hours=timezone_offset)

                # Parse the configured post time (HH:MM format)
                try:
                    post_hour, post_minute = map(int, post_time.split(":"))
                except ValueError:
                    self.bot.logger.error(
                        f"Invalid post_time format for server {server_id}: {post_time}"
                    )
                    continue

                # Calculate time difference in minutes
                current_minutes = server_time.hour * 60 + server_time.minute
                target_minutes = post_hour * 60 + post_minute
                time_diff = abs(current_minutes - target_minutes)

                # Log time check for debugging
                self.bot.logger.debug(
                    f"News check for server {server_id}: "
                    f"current={server_time.strftime('%H:%M')} (UTC{timezone_offset:+d}), "
                    f"target={post_time}, diff={time_diff}min, "
                    f"window={'✓ IN' if time_diff <= 60 else '✗ OUT'}"
                )

                # Check if we're within the posting window (within 60 minutes)
                if time_diff <= 60:
                    # Check if we already posted today
                    today_str = server_time.strftime("%Y-%m-%d")
                    if last_post_date == today_str:
                        self.bot.logger.debug(
                            f"News already posted today for server {server_id} at {post_time}"
                        )
                        continue  # Already posted today

                    # Post news update
                    self.bot.logger.info(
                        f"Posting news to server {server_id} at {post_time} (scheduled time reached)"
                    )
                    await self.post_news_to_server(server_id, channel_id)

                    # Update last post date for this specific time slot
                    await self.bot.database.update_last_news_post(
                        server_id, post_time, today_str
                    )

        except Exception as e:
            self.bot.logger.error(f"Error in daily news task: {e}")

    @daily_news_task.before_loop
    async def before_daily_news_task(self) -> None:
        """Wait until bot is ready before starting the task."""
        await self.bot.wait_until_ready()

    async def fetch_news_from_rss(self, rss_url: str, limit: int = 5, max_age_days: int = 1) -> list:
        """
        Fetch news articles from an RSS feed.

        :param rss_url: The RSS feed URL.
        :param limit: Maximum number of articles to fetch.
        :param max_age_days: Maximum age of articles in days (default 1).
        :return: List of article dictionaries.
        """
        try:
            feed = feedparser.parse(rss_url)

            articles = []
            now = datetime.utcnow()

            # Process more entries to account for filtering
            for entry in feed.entries[:limit * 3]:
                # Skip if we already have enough articles
                if len(articles) >= limit:
                    break

                # Extract article data
                article = {
                    "title": entry.get("title", "No title"),
                    "link": entry.get("link", ""),
                    "description": entry.get("summary", entry.get("description", "")),
                    "published": entry.get(
                        "published", entry.get("updated", "Unknown date")
                    ),
                    "source": feed.feed.get("title", "Unknown source"),
                    "id": entry.get("id", entry.get("link", "")),
                    "image": self.extract_image_from_entry(entry),
                }

                # Check article age - skip if we can't parse date or if too old
                article_date = self.parse_article_date(article["published"])
                if not article_date:
                    # Can't parse date, skip to be safe
                    self.bot.logger.debug(
                        f"Skipping article with unparseable date: {article['title'][:50]}"
                    )
                    continue

                # Make datetime timezone-aware if needed
                if article_date.tzinfo is None:
                    article_date = article_date.replace(tzinfo=None)
                    age = now - article_date
                else:
                    from datetime import timezone
                    now_aware = now.replace(tzinfo=timezone.utc)
                    age = now_aware - article_date

                # Skip articles older than max_age_days
                if age.days > max_age_days:
                    self.bot.logger.debug(
                        f"Skipping old article ({age.days} days old): {article['title'][:50]}"
                    )
                    continue

                # Clean HTML tags from description
                article["description"] = self.clean_html(article["description"])

                # Truncate description if too long
                if len(article["description"]) > 300:
                    article["description"] = article["description"][:297] + "..."

                articles.append(article)

            return articles

        except Exception as e:
            self.bot.logger.error(f"Error fetching RSS feed {rss_url}: {e}")
            return []

    def parse_article_date(self, published_str: str) -> datetime:
        """
        Parse article date string to datetime object.

        :param published_str: Published date string.
        :return: datetime object or None if parsing fails.
        """
        if not published_str or published_str == "Unknown date":
            return None

        try:
            # Try using email.utils for RFC 2822 dates (most common in RSS)
            from email.utils import parsedate_to_datetime
            try:
                return parsedate_to_datetime(published_str)
            except (TypeError, ValueError):
                pass

            # Fallback to manual parsing with common formats
            for fmt in [
                "%a, %d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S %Z",
                "%a, %d %b %Y %H:%M:%S GMT",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            ]:
                try:
                    return datetime.strptime(published_str, fmt)
                except ValueError:
                    continue

            # If all formats fail, log and return None
            self.bot.logger.debug(f"Could not parse date: {published_str}")
            return None

        except Exception as e:
            self.bot.logger.debug(f"Error parsing date '{published_str}': {e}")
            return None

    def clean_html(self, text: str) -> str:
        """
        Remove HTML tags from text.

        :param text: Text with HTML tags.
        :return: Clean text.
        """
        # Remove HTML tags
        clean = re.compile("<.*?>")
        text = re.sub(clean, "", text)
        # Remove extra whitespace
        text = " ".join(text.split())
        return text

    def extract_image_from_entry(self, entry) -> str:
        """
        Extract image URL from RSS feed entry with comprehensive fallback.

        :param entry: Feedparser entry object.
        :return: Image URL string or empty string if no image found.
        """
        image_url = ""

        # 1. Try media_thumbnail first (most common for news feeds)
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            try:
                image_url = entry.media_thumbnail[0].get('url', '')
                if image_url:
                    return image_url
            except (IndexError, KeyError, AttributeError):
                pass

        # 2. Try media_content (often higher quality)
        if hasattr(entry, 'media_content') and entry.media_content:
            try:
                for media in entry.media_content:
                    # Prefer images over other media types
                    if media.get('medium') == 'image' or 'image' in media.get('type', ''):
                        image_url = media.get('url', '')
                        if image_url:
                            return image_url
            except (IndexError, KeyError, AttributeError):
                pass

        # 3. Try enclosures (standard RSS)
        if hasattr(entry, 'enclosures') and entry.enclosures:
            try:
                for enclosure in entry.enclosures:
                    # Check if it's an image type
                    if enclosure.get('type', '').startswith('image/'):
                        image_url = enclosure.get('href', '')
                        if image_url:
                            return image_url
            except (IndexError, KeyError, AttributeError):
                pass

        # 4. Parse HTML description/summary for <img> tags
        html_content = entry.get('description', entry.get('summary', ''))
        if html_content:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                img = soup.find('img')

                if img:
                    # Try src first, then data-src (lazy loading), then srcset
                    image_url = img.get('src') or img.get('data-src', '')

                    # Handle srcset if src not found
                    if not image_url and img.get('srcset'):
                        # srcset format: "url1 1x, url2 2x" - take first URL
                        srcset = img.get('srcset', '').split(',')[0].strip().split()[0]
                        image_url = srcset

                    # Handle relative URLs
                    if image_url and image_url.startswith('/'):
                        from urllib.parse import urlparse
                        parsed = urlparse(entry.get('link', ''))
                        if parsed.scheme and parsed.netloc:
                            image_url = f"{parsed.scheme}://{parsed.netloc}{image_url}"

                    if image_url:
                        return image_url
            except Exception as e:
                self.bot.logger.debug(f"Error parsing HTML for image: {e}")

        return image_url

    def parse_relative_time(self, published_str: str) -> str:
        """
        Convert published date string to relative time.

        :param published_str: Published date string.
        :return: Relative time string (e.g., "2 hours ago").
        """
        try:
            # Try to parse common date formats
            for fmt in [
                "%a, %d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S %Z",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S",
            ]:
                try:
                    parsed = datetime.strptime(published_str, fmt)
                    # Calculate time difference
                    now = datetime.utcnow()
                    if parsed.tzinfo:
                        # Make now timezone-aware
                        from datetime import timezone

                        now = now.replace(tzinfo=timezone.utc)

                    diff = now - parsed

                    # Format relative time
                    if diff.days > 0:
                        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
                    elif diff.seconds >= 3600:
                        hours = diff.seconds // 3600
                        return f"{hours} hour{'s' if hours > 1 else ''} ago"
                    elif diff.seconds >= 60:
                        minutes = diff.seconds // 60
                        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
                    else:
                        return "Just now"
                except ValueError:
                    continue

            # If parsing fails, return original string
            return published_str

        except Exception:
            return published_str

    async def _summarize_and_categorize_articles(self, articles: list) -> list:
        """
        Use Claude API to generate concise summaries and categorize articles.

        :param articles: List of article dictionaries.
        :return: Articles with added 'summary' and 'category' fields.
        """
        if not articles:
            return articles

        try:
            # Build article list for Claude
            articles_text = []
            for idx, article in enumerate(articles):
                articles_text.append(
                    f"Article {idx + 1}:\n"
                    f"Title: {article['title']}\n"
                    f"Source: {article['source']}\n"
                    f"Description: {article['description']}\n"
                )

            prompt = (
                "Analyze these news articles and provide:\n"
                "1. A concise 1-2 sentence summary for each article\n"
                "2. A category for each article from: Politics, Business, Technology, Science, World News, US News, Entertainment, Sports, Health, Other\n\n"
                + "\n".join(articles_text) + "\n\n"
                "Respond in this exact format for each article:\n"
                "Article X | Category: [category] | Summary: [1-2 sentence summary]"
            )

            # Call Claude API with prompt caching
            response = await self.anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=2000,
                system=[
                    {
                        "type": "text",
                        "text": "You are a news summarization assistant. Provide concise, accurate summaries and categorize articles appropriately.",
                        "cache_control": {"type": "ephemeral"}
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Parse Claude's response
            response_text = response.content[0].text
            lines = response_text.strip().split('\n')

            for line in lines:
                if not line.strip() or '|' not in line:
                    continue

                try:
                    # Parse format: "Article X | Category: [category] | Summary: [summary]"
                    parts = line.split('|')
                    if len(parts) >= 3:
                        article_num = int(parts[0].strip().split()[1]) - 1
                        category = parts[1].split(':')[1].strip()
                        summary = parts[2].split(':', 1)[1].strip()

                        if 0 <= article_num < len(articles):
                            articles[article_num]['summary'] = summary
                            articles[article_num]['category'] = category
                except (ValueError, IndexError) as e:
                    self.bot.logger.debug(f"Error parsing Claude response line: {line} - {e}")
                    continue

            # Add default summary/category for any that failed
            for article in articles:
                if 'summary' not in article:
                    article['summary'] = article['description'][:150]
                if 'category' not in article:
                    article['category'] = 'Other'

            return articles

        except Exception as e:
            self.bot.logger.error(f"Error summarizing with Claude: {e}")
            # Fallback: use original descriptions
            for article in articles:
                article['summary'] = article['description'][:150]
                article['category'] = 'Other'
            return articles

    def _create_digest_embeds(self, articles: list) -> list:
        """
        Create digest embeds grouped by category.

        :param articles: List of articles with 'category' and 'summary' fields.
        :return: List of Discord embeds.
        """
        # Group articles by category
        categories = {}
        for article in articles:
            category = article.get('category', 'Other')
            if category not in categories:
                categories[category] = []
            categories[category].append(article)

        # Category emojis
        category_emojis = {
            'Politics': '🏛️',
            'Business': '💼',
            'Technology': '💻',
            'Science': '🔬',
            'World News': '🌍',
            'US News': '🇺🇸',
            'Entertainment': '🎬',
            'Sports': '⚽',
            'Health': '🏥',
            'Other': '📰'
        }

        # Create embeds (one per category, max 25 fields per embed)
        embeds = []

        for category, cat_articles in sorted(categories.items()):
            emoji = category_emojis.get(category, '📰')
            embed = discord.Embed(
                title=f"{emoji} {category}",
                description=f"{len(cat_articles)} article{'s' if len(cat_articles) != 1 else ''}",
                color=0x3498DB,
            )

            # Add up to 25 articles (Discord limit)
            for article in cat_articles[:25]:
                field_value = f"**{article['source']}** • {article.get('summary', article['description'][:100])}"
                embed.add_field(
                    name=f"{article.get('article_type', '📰')} {article['title'][:80]}",
                    value=field_value[:1024],  # Discord field value limit
                    inline=False
                )

            if len(cat_articles) > 25:
                embed.set_footer(text=f"+ {len(cat_articles) - 25} more articles in this category")

            embeds.append(embed)

        return embeds

    async def post_news_to_server(
        self, server_id: int, channel_id: int
    ) -> None:
        """
        Post top 2 news articles from each source to a server's configured channel.

        :param server_id: The server ID.
        :param channel_id: The channel ID.
        """
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                self.bot.logger.error(f"Channel {channel_id} not found")
                return

            # Get news sources for this server
            sources = await self.bot.database.get_news_sources(server_id)

            # If no custom sources, use default sources
            if not sources:
                sources = [(name, url) for name, url in DEFAULT_SOURCES.items()]

            all_articles = []

            # Fetch top 2 stories from each source
            for source_name, rss_url in sources:
                articles = await self.fetch_news_from_rss(rss_url, limit=2)
                for idx, article in enumerate(articles):
                    # Check if article already posted
                    if not await self.bot.database.is_article_posted(
                        server_id, article["id"]
                    ):
                        article["source"] = source_name  # Override with custom name
                        article["article_type"] = "📰 Recent" if idx == 0 else "⭐ Popular"
                        all_articles.append(article)

            if not all_articles:
                self.bot.logger.info(
                    f"No new articles to post for server {server_id}"
                )
                return

            # Summarize and categorize articles with Claude
            all_articles = await self._summarize_and_categorize_articles(all_articles)

            # Create digest embeds
            digest_embeds = self._create_digest_embeds(all_articles)

            # Count categories
            categories = set(article.get('category', 'Other') for article in all_articles)

            # Send header embed
            header_embed = discord.Embed(
                title="📰 Daily News Digest",
                description=f"{len(categories)} categories • {len(all_articles)} articles from {len(sources)} sources",
                color=0x3498DB,
            )
            header_embed.set_footer(text=f"News Update • {datetime.now().strftime('%B %d, %Y')}")
            header_embed_message = await channel.send(embed=header_embed)

            # Send digest embeds (categorized overview)
            for digest_embed in digest_embeds:
                await channel.send(embed=digest_embed)

            # Create thread for full articles
            try:
                # Check if bot has permission to create threads
                bot_permissions = channel.permissions_for(channel.guild.me)
                if not bot_permissions.create_public_threads:
                    self.bot.logger.warning(
                        f"Missing 'Create Public Threads' permission in server {server_id}, channel {channel_id}. "
                        "Posting digest only."
                    )
                    return

                thread_name = f"📰 Full Articles - {datetime.now().strftime('%B %d, %Y')}"

                # Create thread from the channel directly using the message
                if isinstance(channel, discord.TextChannel):
                    thread = await channel.create_thread(
                        name=thread_name,
                        message=header_embed_message,
                        auto_archive_duration=1440  # 24 hours
                    )
                else:
                    # Fallback to message.create_thread for other channel types
                    thread = await header_embed_message.create_thread(
                        name=thread_name,
                        auto_archive_duration=1440  # 24 hours
                    )
            except discord.Forbidden:
                self.bot.logger.warning(
                    f"Permission denied creating thread in server {server_id}, channel {channel_id}. "
                    "Bot needs 'Create Public Threads' permission."
                )
                return
            except Exception as thread_error:
                self.bot.logger.error(f"Failed to create thread for server {server_id}: {thread_error}")
                # Skip posting full articles if thread creation fails
                self.bot.logger.info(f"Posted {len(all_articles)} news articles to server {server_id} (digest only)")
                return

            # Post each individual article with AI summary to the thread
            for article in all_articles:
                embed = discord.Embed(
                    title=article["title"][:256],  # Discord limit
                    description=article.get("summary", article["description"]),
                    color=0x3498DB,
                    url=article["link"],
                )

                # Add fields
                embed.add_field(
                    name="Source", value=article["source"], inline=True
                )
                embed.add_field(
                    name="Category", value=article.get("category", "Other"), inline=True
                )
                embed.add_field(
                    name="Type", value=article["article_type"], inline=True
                )
                embed.add_field(
                    name="Published",
                    value=self.parse_relative_time(article["published"]),
                    inline=True,
                )

                # Add image if available
                if article.get("image"):
                    embed.set_image(url=article["image"])

                embed.set_footer(text="Click the title to read the full article")

                await thread.send(embed=embed)

                # Mark article as posted
                await self.bot.database.mark_article_posted(server_id, article["id"])

            self.bot.logger.info(
                f"Posted {len(all_articles)} news articles to server {server_id}"
            )

        except Exception as e:
            self.bot.logger.error(f"Error posting news to server {server_id}: {e}")

    # ========== CONSOLIDATED COMMAND 1: /news ==========

    async def _news_view(self, ctx: Context) -> None:
        """View current news."""
        await ctx.defer()

        try:
            # Get configured sources or use defaults
            server_id = ctx.guild.id
            sources = await self.bot.database.get_news_sources(server_id)

            if not sources:
                sources = [(name, url) for name, url in DEFAULT_SOURCES.items()]

            all_articles = []

            # Fetch top 2 stories from each source
            for source_name, rss_url in sources:
                articles = await self.fetch_news_from_rss(rss_url, limit=2)
                for idx, article in enumerate(articles):
                    # Check if article already posted
                    if not await self.bot.database.is_article_posted(
                        server_id, article["id"]
                    ):
                        article["source"] = source_name
                        article["article_type"] = "📰 Recent" if idx == 0 else "⭐ Popular"
                        all_articles.append(article)

            if not all_articles:
                embed = discord.Embed(
                    description="❌ Could not fetch news at this time. Please try again later.",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed)
                return

            # Summarize and categorize articles with Claude
            all_articles = await self._summarize_and_categorize_articles(all_articles)

            # Create digest embeds
            digest_embeds = self._create_digest_embeds(all_articles)

            # Count categories
            categories = set(article.get('category', 'Other') for article in all_articles)

            # Send header embed
            header_embed = discord.Embed(
                title="📰 Latest News Digest",
                description=f"{len(categories)} categories • {len(all_articles)} articles from {len(sources)} sources",
                color=0x3498DB,
            )
            header_embed_message = await ctx.send(embed=header_embed)

            # Send digest embeds (categorized overview)
            for digest_embed in digest_embeds:
                await ctx.send(embed=digest_embed)

            # Create thread for full articles
            try:
                # Check if bot has permission to create threads
                bot_permissions = ctx.channel.permissions_for(ctx.guild.me)
                if not bot_permissions.create_public_threads:
                    error_msg = (
                        "⚠️ **Missing Permission**: I need the **Create Public Threads** permission to post full articles.\n\n"
                        f"Please give me this permission in {ctx.channel.mention}, then try again."
                    )
                    await ctx.send(error_msg)
                    return

                thread_name = f"📰 Full Articles - {datetime.now().strftime('%B %d, %Y')}"

                # Create thread from the channel directly using the message
                if isinstance(ctx.channel, discord.TextChannel):
                    thread = await ctx.channel.create_thread(
                        name=thread_name,
                        message=header_embed_message,
                        auto_archive_duration=1440  # 24 hours
                    )
                else:
                    # Fallback to message.create_thread for other channel types
                    thread = await header_embed_message.create_thread(
                        name=thread_name,
                        auto_archive_duration=1440  # 24 hours
                    )
            except discord.Forbidden:
                error_msg = (
                    "⚠️ **Permission Error**: I don't have permission to create threads in this channel.\n\n"
                    f"Please give me the **Create Public Threads** permission in {ctx.channel.mention}."
                )
                await ctx.send(error_msg)
                return
            except Exception as thread_error:
                self.bot.logger.error(f"Failed to create thread: {thread_error}")
                await ctx.send(f"⚠️ Could not create thread: {thread_error}\n\nPosting summaries only.")
                return

            # Post each individual article with AI summary to the thread
            for article in all_articles:
                embed = discord.Embed(
                    title=article["title"][:256],
                    description=article.get("summary", article["description"]),
                    color=0x3498DB,
                    url=article["link"],
                )

                embed.add_field(
                    name="Source", value=article["source"], inline=True
                )
                embed.add_field(
                    name="Category", value=article.get("category", "Other"), inline=True
                )
                embed.add_field(
                    name="Type", value=article["article_type"], inline=True
                )
                embed.add_field(
                    name="Published",
                    value=self.parse_relative_time(article["published"]),
                    inline=True,
                )

                # Add image if available
                if article.get("image"):
                    embed.set_image(url=article["image"])

                embed.set_footer(text="Click the title to read the full article")

                await thread.send(embed=embed)

        except Exception as e:
            self.bot.logger.error(f"Error fetching news: {e}")
            embed = discord.Embed(
                description="❌ An error occurred while fetching news.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)

    async def _news_now(self, ctx: Context) -> None:
        """Post news update immediately (Admin only)."""
        configs = await self.bot.database.get_news_config(ctx.guild.id)

        if not configs:
            embed = discord.Embed(
                description="❌ News updates are not configured. Use `/news-admin setup` first.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        await ctx.defer()

        try:
            # Use channel from first config (all should use same channel)
            await self.post_news_to_server(ctx.guild.id, configs[0]["channel_id"])

            embed = discord.Embed(
                description=f"✅ News update posted to <#{configs[0]['channel_id']}>",
                color=0x2ECC71,
            )
            await ctx.send(embed=embed)

        except Exception as e:
            self.bot.logger.error(f"Error posting immediate news: {e}")
            embed = discord.Embed(
                description="❌ An error occurred while posting news.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(
        name="news",
        description="View current news or post news update immediately",
    )
    @app_commands.describe(action="Action to perform: view (default) or now (admin)")
    @commands.guild_only()
    async def news(
        self,
        ctx: Context,
        action: Literal["view", "now"] = "view"
    ) -> None:
        """
        Fetch and display news or post a manual update.

        :param ctx: The hybrid command context.
        :param action: Action to perform - view (default) or now (admin).
        """
        if action == "view":
            await self._news_view(ctx)
        elif action == "now":
            # Check admin permissions
            if not ctx.author.guild_permissions.administrator:
                embed = discord.Embed(
                    description="❌ You need administrator permissions to post news manually.",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed, ephemeral=True)
                return
            await self._news_now(ctx)

    # ========== CONSOLIDATED COMMAND 2: /news-sources ==========

    async def _sources_list(self, ctx: Context) -> None:
        """List all configured news sources."""
        sources = await self.bot.database.get_news_sources(ctx.guild.id)

        if not sources:
            embed = discord.Embed(
                title="📰 News Sources",
                description="No custom sources configured. Using default sources:\n"
                + "\n".join([f"• {name}" for name in DEFAULT_SOURCES.keys()]),
                color=0x3498DB,
            )
            embed.add_field(
                name="Manage Sources",
                value="• `/news-sources add <name> <rss_url>` - Add custom source\n• `/news-sources remove <name>` - Remove a source",
                inline=False,
            )
        else:
            source_list = "\n".join([f"• **{name}**\n  `{url[:60]}{'...' if len(url) > 60 else ''}`" for name, url in sources])
            embed = discord.Embed(
                title="📰 Configured News Sources",
                description=source_list,
                color=0x3498DB,
            )
            embed.add_field(
                name=f"Total: {len(sources)} sources",
                value="Use `/news-sources add` to add more or `/news-sources remove` to remove",
                inline=False,
            )

        await ctx.send(embed=embed)

    async def _sources_add(self, ctx: Context, name: str, rss_url: str) -> None:
        """Add a custom RSS news source (Admin only)."""
        # Validate URL format
        if not rss_url.startswith(("http://", "https://")):
            embed = discord.Embed(
                description="❌ Invalid URL. RSS feed URL must start with http:// or https://",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        # Validate name length
        if len(name) > 50:
            embed = discord.Embed(
                description="❌ Source name is too long. Please use 50 characters or less.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        try:
            # Check if source already exists
            existing_sources = await self.bot.database.get_news_sources(ctx.guild.id)
            if any(source[0] == name for source in existing_sources):
                embed = discord.Embed(
                    description=f"❌ A source named '{name}' already exists. Use a different name or remove the old one first.",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed, ephemeral=True)
                return

            # Test fetch the RSS feed
            await ctx.defer()
            test_articles = await self.fetch_news_from_rss(rss_url, limit=1)

            if not test_articles:
                embed = discord.Embed(
                    title="⚠️ Warning: Feed May Be Invalid",
                    description=f"Could not fetch articles from this RSS feed. The feed may be:\n• Invalid or malformed\n• Temporarily unavailable\n• Blocking automated requests\n\nSource has been added anyway, but it may not work.",
                    color=0xE67E22,
                )
                await ctx.send(embed=embed)

            # Add the source
            await self.bot.database.add_news_source(ctx.guild.id, name, rss_url)

            # Get updated count
            all_sources = await self.bot.database.get_news_sources(ctx.guild.id)

            embed = discord.Embed(
                title="✅ News Source Added",
                description=f"**{name}** has been added to your news sources",
                color=0x2ECC71,
            )
            embed.add_field(
                name="RSS URL",
                value=f"`{rss_url[:100]}{'...' if len(rss_url) > 100 else ''}`",
                inline=False,
            )
            embed.add_field(
                name="Total Sources",
                value=f"{len(all_sources)} sources configured",
                inline=True,
            )

            if test_articles:
                embed.add_field(
                    name="Test Article",
                    value=f"✅ Successfully fetched: {test_articles[0]['title'][:80]}",
                    inline=False,
                )

            await ctx.send(embed=embed)

        except Exception as e:
            self.bot.logger.error(f"Error adding news source: {e}")
            embed = discord.Embed(
                description="❌ An error occurred while adding the news source.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed, ephemeral=True)

    async def _sources_remove(self, ctx: Context, name: str) -> None:
        """Remove a news source (Admin only)."""
        try:
            # Check current sources count
            existing_sources = await self.bot.database.get_news_sources(ctx.guild.id)

            if not existing_sources:
                embed = discord.Embed(
                    description="❌ No custom news sources configured. Using default sources only.",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed, ephemeral=True)
                return

            if len(existing_sources) == 1:
                embed = discord.Embed(
                    description="❌ Cannot remove the last news source. Add another source first.",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed, ephemeral=True)
                return

            # Remove the source
            success = await self.bot.database.remove_news_source(ctx.guild.id, name)

            if success:
                remaining = await self.bot.database.get_news_sources(ctx.guild.id)
                embed = discord.Embed(
                    title="✅ News Source Removed",
                    description=f"**{name}** has been removed from your news sources",
                    color=0x2ECC71,
                )
                embed.add_field(
                    name="Remaining Sources",
                    value=f"{len(remaining)} sources configured",
                    inline=False,
                )
            else:
                embed = discord.Embed(
                    description=f"❌ No news source named '{name}' found. Use `/news-sources list` to see available sources.",
                    color=0xE02B2B,
                )

            await ctx.send(embed=embed)

        except Exception as e:
            self.bot.logger.error(f"Error removing news source: {e}")
            embed = discord.Embed(
                description="❌ An error occurred while removing the news source.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(
        name="news-sources",
        description="Manage RSS news sources",
    )
    @app_commands.describe(
        action="Action to perform: list, add, or remove",
        name="Name for the news source (required for add/remove)",
        rss_url="RSS feed URL (required for add)",
    )
    @commands.guild_only()
    async def news_sources(
        self,
        ctx: Context,
        action: Literal["list", "add", "remove"],
        name: str = None,
        rss_url: str = None
    ) -> None:
        """
        Manage news sources for this server.

        :param ctx: The hybrid command context.
        :param action: Action to perform - list, add, or remove.
        :param name: Name for the news source (required for add/remove).
        :param rss_url: RSS feed URL (required for add).
        """
        if action == "list":
            await self._sources_list(ctx)

        elif action == "add":
            # Check admin permissions
            if not ctx.author.guild_permissions.administrator:
                embed = discord.Embed(
                    description="❌ You need administrator permissions to add news sources.",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed, ephemeral=True)
                return

            if not name or not rss_url:
                embed = discord.Embed(
                    description="❌ Both `name` and `rss_url` are required for adding a source.\n\nUsage: `/news-sources add <name> <rss_url>`",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed, ephemeral=True)
                return

            await self._sources_add(ctx, name, rss_url)

        elif action == "remove":
            # Check admin permissions
            if not ctx.author.guild_permissions.administrator:
                embed = discord.Embed(
                    description="❌ You need administrator permissions to remove news sources.",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed, ephemeral=True)
                return

            if not name:
                embed = discord.Embed(
                    description="❌ `name` is required for removing a source.\n\nUsage: `/news-sources remove <name>`",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed, ephemeral=True)
                return

            await self._sources_remove(ctx, name)

    # ========== CONSOLIDATED COMMAND 3: /news-admin ==========

    async def _admin_setup(
        self,
        ctx: Context,
        channel: discord.TextChannel,
        time: str,
        timezone_offset: int
    ) -> None:
        """Setup daily news posting (Admin only)."""
        # Validate time format
        time_pattern = re.compile(r"^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$")
        if not time_pattern.match(time):
            embed = discord.Embed(
                description="❌ Invalid time format. Please use HH:MM format (e.g., 08:00 or 14:30)",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        # Validate timezone offset
        if timezone_offset < -12 or timezone_offset > 14:
            embed = discord.Embed(
                description="❌ Invalid timezone offset. Must be between -12 and 14.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        try:
            # Check how many times are already configured
            current_count = await self.bot.database.count_news_times(ctx.guild.id)

            if current_count >= 3:
                embed = discord.Embed(
                    description="❌ Maximum of 3 post times reached. Use `/news-admin remove-time <time>` to remove a time first.",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed, ephemeral=True)
                return

            # Save configuration
            await self.bot.database.set_news_config(
                ctx.guild.id, channel.id, time, timezone_offset
            )

            # Add default sources if none exist
            existing_sources = await self.bot.database.get_news_sources(ctx.guild.id)
            if not existing_sources:
                for source_name, rss_url in DEFAULT_SOURCES.items():
                    await self.bot.database.add_news_source(
                        ctx.guild.id, source_name, rss_url
                    )

            # Get updated count
            new_count = await self.bot.database.count_news_times(ctx.guild.id)

            embed = discord.Embed(
                title="✅ News Update Time Added",
                description=f"News will be posted to {channel.mention} at {time} (UTC{timezone_offset:+d})",
                color=0x2ECC71,
            )

            if new_count < 3:
                embed.add_field(
                    name="Add More Times",
                    value=f"You have {new_count}/3 post times configured. Run `/news-admin setup` again to add more times (max 3 per day).",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="Maximum Reached",
                    value="You have 3/3 post times configured (maximum).",
                    inline=False,
                )

            if not existing_sources:
                embed.add_field(
                    name="Default Sources Added",
                    value="\n".join([f"• {name}" for name in DEFAULT_SOURCES.keys()]),
                    inline=False,
                )

            embed.add_field(
                name="Commands",
                value="• `/news-admin status` - View all configured times\n• `/news-admin remove-time <time>` - Remove a post time\n• `/news-admin toggle <enabled>` - Enable/disable all updates\n• `/news now` - Post immediate update",
                inline=False,
            )

            await ctx.send(embed=embed)

        except Exception as e:
            self.bot.logger.error(f"Error setting up news: {e}")
            embed = discord.Embed(
                description="❌ An error occurred while setting up news updates.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed, ephemeral=True)

    async def _admin_toggle(self, ctx: Context, enabled: bool) -> None:
        """Enable or disable daily news updates (Admin only)."""
        success = await self.bot.database.toggle_news(ctx.guild.id, enabled)

        if success:
            status = "enabled" if enabled else "disabled"
            embed = discord.Embed(
                description=f"✅ News updates have been {status}.",
                color=0x2ECC71,
            )
        else:
            embed = discord.Embed(
                description="❌ News updates are not configured for this server. Use `/news-admin setup` first.",
                color=0xE02B2B,
            )

        await ctx.send(embed=embed)

    async def _admin_status(self, ctx: Context) -> None:
        """View news configuration."""
        configs = await self.bot.database.get_news_config(ctx.guild.id)

        if not configs:
            embed = discord.Embed(
                description="❌ News updates are not configured for this server. Use `/news-admin setup` to get started.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        # Get channel from first config (all should use same channel)
        channel = self.bot.get_channel(int(configs[0]["channel_id"]))
        channel_mention = channel.mention if channel else f"<#{configs[0]['channel_id']}>"

        # Check if all are enabled
        all_enabled = all(c["enabled"] for c in configs)
        status = "✅ Enabled" if all_enabled else "⚠️ Partially Enabled"

        embed = discord.Embed(
            title="📰 News Configuration",
            color=0x3498DB,
        )
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Channel", value=channel_mention, inline=True)
        embed.add_field(
            name="Post Times",
            value=f"{len(configs)}/3 configured",
            inline=True,
        )

        # List all post times
        times_list = []
        for config in configs:
            enabled_icon = "✅" if config["enabled"] else "❌"
            times_list.append(
                f"{enabled_icon} {config['post_time']} (UTC{config['timezone_offset']:+d})"
            )
            if config["last_post_date"]:
                times_list.append(f"   └─ Last posted: {config['last_post_date']}")

        embed.add_field(
            name="Scheduled Times",
            value="\n".join(times_list),
            inline=False,
        )

        # Get sources
        sources = await self.bot.database.get_news_sources(ctx.guild.id)
        if sources:
            source_list = "\n".join([f"• {name}" for name, _ in sources])
            embed.add_field(name="News Sources", value=source_list, inline=False)

        await ctx.send(embed=embed)

    async def _admin_remove_time(self, ctx: Context, time: str) -> None:
        """Remove a scheduled news post time (Admin only)."""
        # Validate time format
        time_pattern = re.compile(r"^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$")
        if not time_pattern.match(time):
            embed = discord.Embed(
                description="❌ Invalid time format. Please use HH:MM format (e.g., 08:00 or 14:30)",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        success = await self.bot.database.remove_news_time(ctx.guild.id, time)

        if success:
            remaining = await self.bot.database.count_news_times(ctx.guild.id)
            embed = discord.Embed(
                title="✅ Post Time Removed",
                description=f"News will no longer be posted at {time}",
                color=0x2ECC71,
            )
            embed.add_field(
                name="Remaining Times",
                value=f"{remaining}/3 post times configured",
                inline=False,
            )
        else:
            embed = discord.Embed(
                description=f"❌ No news post time found at {time}. Use `/news-admin status` to see configured times.",
                color=0xE02B2B,
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="news-admin",
        description="Admin configuration for news updates",
    )
    @app_commands.describe(
        action="Action to perform: setup, toggle, status, or remove-time",
        channel="The channel where news will be posted (for setup)",
        time="Time to post news in HH:MM format (for setup/remove-time)",
        timezone_offset="Timezone offset from UTC in hours (for setup)",
        enabled="Enable or disable news updates (for toggle)",
    )
    @commands.guild_only()
    async def news_admin(
        self,
        ctx: Context,
        action: Literal["setup", "toggle", "status", "remove-time"],
        channel: discord.TextChannel = None,
        time: str = None,
        timezone_offset: int = 0,
        enabled: bool = None
    ) -> None:
        """
        Admin configuration for news updates.

        :param ctx: The hybrid command context.
        :param action: Action to perform - setup, toggle, status, or remove-time.
        :param channel: The channel where news will be posted (for setup).
        :param time: Time to post news in HH:MM format (for setup/remove-time).
        :param timezone_offset: Timezone offset from UTC in hours (for setup).
        :param enabled: Enable or disable news updates (for toggle).
        """
        if action == "status":
            await self._admin_status(ctx)

        elif action == "setup":
            # Check admin permissions
            if not ctx.author.guild_permissions.administrator:
                embed = discord.Embed(
                    description="❌ You need administrator permissions to configure news updates.",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed, ephemeral=True)
                return

            if not channel or not time:
                embed = discord.Embed(
                    description="❌ `channel` and `time` are required for setup.\n\nUsage: `/news-admin setup <channel> <time> [timezone_offset]`",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed, ephemeral=True)
                return

            await self._admin_setup(ctx, channel, time, timezone_offset)

        elif action == "toggle":
            # Check admin permissions
            if not ctx.author.guild_permissions.administrator:
                embed = discord.Embed(
                    description="❌ You need administrator permissions to toggle news updates.",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed, ephemeral=True)
                return

            if enabled is None:
                embed = discord.Embed(
                    description="❌ `enabled` parameter is required for toggle.\n\nUsage: `/news-admin toggle <enabled:True/False>`",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed, ephemeral=True)
                return

            await self._admin_toggle(ctx, enabled)

        elif action == "remove-time":
            # Check admin permissions
            if not ctx.author.guild_permissions.administrator:
                embed = discord.Embed(
                    description="❌ You need administrator permissions to remove post times.",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed, ephemeral=True)
                return

            if not time:
                embed = discord.Embed(
                    description="❌ `time` is required for remove-time.\n\nUsage: `/news-admin remove-time <time>`",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed, ephemeral=True)
                return

            await self._admin_remove_time(ctx, time)


async def setup(bot) -> None:
    await bot.add_cog(News(bot))
