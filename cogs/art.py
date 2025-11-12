"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.3.0
"""

import base64
import io
import os
import random
import re
from datetime import datetime, time, timedelta
from typing import Optional, Dict, List

import aiohttp
import discord
from anthropic import AsyncAnthropic
from discord import app_commands
from discord.ext import commands, tasks
from discord.ext.commands import Context


class Art(commands.Cog, name="art"):
    def __init__(self, bot) -> None:
        self.bot = bot

        # Initialize Claude client for AI analysis
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            self.bot.logger.warning(
                "ANTHROPIC_API_KEY not found. Art analysis features will be limited."
            )
            self.client = None
        else:
            self.client = AsyncAnthropic(api_key=api_key)
            self.bot.logger.info("Art cog initialized with Claude AI.")

        # Start the background task
        self.daily_art_task.start()

    def cog_unload(self) -> None:
        """Clean up when cog is unloaded."""
        self.daily_art_task.cancel()

    # Focus area keywords for filtering art
    FOCUS_AREAS = {
        "all": "all periods and styles",
        "classical": "classical, ancient, renaissance, baroque",
        "modern": "modern, contemporary, abstract, impressionist",
        "photography": "photography, photographic",
        "sculpture": "sculpture, sculptural, three-dimensional",
        "painting": "painting, oil, watercolor, acrylic"
    }

    def parse_time_string(self, time_str: str) -> Optional[time]:
        """Parse time string in HH:MM format (24-hour)."""
        time_str = time_str.strip()
        pattern = r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$'
        match = re.match(pattern, time_str)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            return time(hour, minute)
        return None

    def get_current_date_for_server(self, timezone_offset: int) -> str:
        """Get current date string for a server's timezone."""
        utc_now = datetime.utcnow()
        server_time = utc_now + timedelta(hours=timezone_offset)
        return server_time.strftime("%Y-%m-%d")

    def get_current_time_for_server(self, timezone_offset: int) -> time:
        """Get current time for a server's timezone."""
        utc_now = datetime.utcnow()
        server_time = utc_now + timedelta(hours=timezone_offset)
        return server_time.time()

    async def fetch_met_artwork(self) -> Optional[Dict]:
        """
        Fetch a random artwork from the Metropolitan Museum of Art API.

        :return: Dictionary with artwork data or None if failed.
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Get random object IDs from Met collection
                search_url = "https://collectionapi.metmuseum.org/public/collection/v1/search"
                params = {
                    "hasImages": "true",
                    "q": random.choice(["painting", "sculpture", "drawing", "print", "photograph"])
                }

                async with session.get(search_url, params=params, timeout=10) as response:
                    if response.status != 200:
                        return None

                    data = await response.json()
                    object_ids = data.get("objectIDs", [])

                    if not object_ids:
                        return None

                    # Try up to 10 random artworks to find one with good data
                    for _ in range(10):
                        random_id = random.choice(object_ids)
                        object_url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{random_id}"

                        async with session.get(object_url, timeout=10) as obj_response:
                            if obj_response.status != 200:
                                continue

                            artwork = await obj_response.json()

                            # Validate the artwork has required fields
                            if (artwork.get("primaryImage") and
                                artwork.get("title") and
                                artwork.get("artistDisplayName")):

                                return {
                                    "title": artwork.get("title", "Untitled"),
                                    "artist": artwork.get("artistDisplayName", "Unknown Artist"),
                                    "date": artwork.get("objectDate", "Date Unknown"),
                                    "medium": artwork.get("medium", "Medium not specified"),
                                    "culture": artwork.get("culture", ""),
                                    "department": artwork.get("department", ""),
                                    "image_url": artwork.get("primaryImage"),
                                    "object_url": artwork.get("objectURL", ""),
                                    "museum": "Metropolitan Museum of Art"
                                }

                    return None

        except Exception as e:
            self.bot.logger.error(f"Error fetching Met artwork: {e}")
            return None

    async def fetch_art_institute_artwork(self) -> Optional[Dict]:
        """
        Fetch a random artwork from the Art Institute of Chicago API.

        :return: Dictionary with artwork data or None if failed.
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Get random artworks
                search_url = "https://api.artic.edu/api/v1/artworks/search"
                params = {
                    "q": random.choice(["painting", "sculpture", "print", "drawing", "photograph"]),
                    "query[term][is_public_domain]": "true",
                    "fields": "id",
                    "limit": 100
                }

                async with session.get(search_url, params=params, timeout=10) as response:
                    if response.status != 200:
                        return None

                    data = await response.json()
                    artworks = data.get("data", [])

                    if not artworks:
                        return None

                    # Try up to 10 random artworks
                    for _ in range(10):
                        artwork_id = random.choice(artworks)["id"]
                        object_url = f"https://api.artic.edu/api/v1/artworks/{artwork_id}"

                        async with session.get(object_url, timeout=10) as obj_response:
                            if obj_response.status != 200:
                                continue

                            result = await obj_response.json()
                            artwork = result.get("data", {})

                            # Check for image
                            if artwork.get("image_id"):
                                iiif_url = f"https://www.artic.edu/iiif/2/{artwork['image_id']}/full/843,/0/default.jpg"

                                return {
                                    "title": artwork.get("title", "Untitled"),
                                    "artist": artwork.get("artist_display", "Unknown Artist").split('\n')[0],
                                    "date": artwork.get("date_display", "Date Unknown"),
                                    "medium": artwork.get("medium_display", "Medium not specified"),
                                    "culture": artwork.get("place_of_origin", ""),
                                    "department": artwork.get("department_title", ""),
                                    "image_url": iiif_url,
                                    "object_url": f"https://www.artic.edu/artworks/{artwork_id}",
                                    "museum": "Art Institute of Chicago"
                                }

                    return None

        except Exception as e:
            self.bot.logger.error(f"Error fetching Art Institute artwork: {e}")
            return None

    async def generate_art_story(self, artwork: Dict) -> str:
        """
        Generate an engaging story about the artwork using Claude vision analysis.

        Uses cached analysis if available, otherwise analyzes with Claude vision.
        Falls back to text-only if vision fails.

        :param artwork: Dictionary containing artwork information.
        :return: Generated story text.
        """
        artwork_url = artwork.get('object_url', '')

        # Check cache first
        if artwork_url:
            cached = await self.bot.database.get_cached_art_analysis(artwork_url)
            if cached:
                self.bot.logger.info(f"Cache hit for artwork: {artwork['title']}")
                await self.bot.database.update_art_analysis_last_used(artwork_url)
                return cached['vision_story']

        # Attempt vision analysis
        self.bot.logger.info(f"Generating vision analysis for: {artwork['title']}")

        image_url = artwork.get('image_url')
        if image_url and self.client:
            try:
                # Download and encode image
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url, timeout=15) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            image_base64 = base64.b64encode(image_data).decode('utf-8')

                            # Determine media type
                            content_type = response.headers.get('Content-Type', 'image/jpeg')
                            if 'png' in content_type:
                                media_type = "image/png"
                            elif 'webp' in content_type:
                                media_type = "image/webp"
                            elif 'gif' in content_type:
                                media_type = "image/gif"
                            else:
                                media_type = "image/jpeg"

                            # Create enhanced vision prompt
                            prompt = f"""You are analyzing this artwork to create an engaging educational story for a Discord community.

ARTWORK METADATA:
- Title: {artwork['title']}
- Artist: {artwork['artist']}
- Date: {artwork['date']}
- Medium: {artwork['medium']}
- Culture: {artwork.get('culture', 'Unknown')}
- Museum: {artwork['museum']}

Using BOTH what you see in the image AND the metadata above, write 2-3 short paragraphs (max 300 words) that:

1. **Visual Description**: Briefly describe what you see (subjects, colors, composition, mood)
2. **Context & Significance**: Connect the visual elements to historical/cultural context
3. **Engagement Hook**: End with a thought-provoking question or observation that sparks discussion

Tone: Conversational and enthusiastic, not academic. Make people excited to look closely at the artwork and discuss it.

Focus on what makes this piece interesting or unique visually and historically."""

                            # Call Claude vision API
                            message = await self.client.messages.create(
                                model="claude-3-5-sonnet-20241022",
                                max_tokens=600,
                                messages=[{
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "image",
                                            "source": {
                                                "type": "base64",
                                                "media_type": media_type,
                                                "data": image_base64
                                            }
                                        },
                                        {
                                            "type": "text",
                                            "text": prompt
                                        }
                                    ]
                                }]
                            )

                            vision_story = f"📚 **Story & Context:**\n\n{message.content[0].text.strip()}"

                            # Cache the result
                            if artwork_url:
                                try:
                                    await self.bot.database.save_art_analysis(
                                        artwork_url,
                                        image_url,
                                        artwork['title'],
                                        artwork['artist'],
                                        artwork['museum'],
                                        vision_story
                                    )
                                    self.bot.logger.info(f"Cached vision analysis for: {artwork['title']}")
                                except Exception as e:
                                    self.bot.logger.error(f"Failed to save analysis to cache: {e}")

                            return vision_story

            except Exception as e:
                self.bot.logger.warning(f"Vision analysis failed for {artwork['title']}: {e}")

        # Fallback to text-only generation
        self.bot.logger.info(f"Using text-only fallback for: {artwork['title']}")

        fallback_story = f"📚 **About this artwork:**\n\n"
        fallback_story += f"Created by {artwork['artist']} in {artwork['date']}, "
        fallback_story += f"this {artwork['medium'].lower()} is part of the {artwork['museum']} collection."

        if artwork.get('culture'):
            fallback_story += f" It originates from {artwork['culture']}."

        fallback_story += f"\n\nThis piece represents {artwork['medium'].lower()} artistry from the {artwork['date']} period."

        # Cache text-only fallback
        if artwork_url and self.client:
            try:
                await self.bot.database.save_art_analysis(
                    artwork_url,
                    image_url or '',
                    artwork['title'],
                    artwork['artist'],
                    artwork['museum'],
                    fallback_story
                )
            except Exception as e:
                self.bot.logger.error(f"Failed to save fallback to cache: {e}")

        return fallback_story

    async def post_artwork_to_channel(self, server_id: int, channel_id: int, artwork: Dict) -> bool:
        """Post an artwork with story to a channel."""
        try:
            guild = self.bot.get_guild(server_id)
            if not guild:
                self.bot.logger.warning(f"Could not find guild {server_id} for art posting")
                return False

            # Diagnostic logging
            self.bot.logger.info(f"Looking for channel {channel_id} in guild {guild.name} (ID: {guild.id})")

            # Log all available channels for debugging
            all_channels = [(ch.id, ch.name, type(ch).__name__) for ch in guild.channels]
            self.bot.logger.info(f"Guild has {len(all_channels)} channels: {all_channels[:5]}...")  # Show first 5

            channel = guild.get_channel(channel_id)
            if not channel:
                # Try fetching instead (works for threads, forum posts, etc.)
                self.bot.logger.warning(
                    f"get_channel() failed for {channel_id}, attempting fetch_channel()..."
                )
                try:
                    channel = await guild.fetch_channel(channel_id)
                    self.bot.logger.info(f"fetch_channel() succeeded! Channel type: {type(channel).__name__}")
                except Exception as e:
                    self.bot.logger.error(
                        f"Could not find/fetch channel {channel_id} in guild {guild.name}: {e}"
                    )
                    return False

            # Generate story
            story = await self.generate_art_story(artwork)

            # Create embed
            embed = discord.Embed(
                title=f"🎨 {artwork['title']}",
                description=story,
                color=0x9B59B6,  # Purple for art
                url=artwork.get('object_url', '')
            )

            # Add fields
            embed.add_field(name="Artist", value=artwork['artist'], inline=True)
            embed.add_field(name="Date", value=artwork['date'], inline=True)
            embed.add_field(name="Medium", value=artwork['medium'], inline=False)

            if artwork.get('culture'):
                embed.add_field(name="Origin", value=artwork['culture'], inline=True)

            embed.add_field(name="Museum", value=artwork['museum'], inline=True)

            # Set image
            if artwork.get('image_url'):
                embed.set_image(url=artwork['image_url'])

            # Footer
            embed.set_footer(text="💬 React and share your thoughts! • Use /art-analyze to learn more about any artwork")

            await channel.send(embed=embed)
            return True

        except Exception as e:
            self.bot.logger.error(f"Error posting artwork: {e}")
            return False

    @tasks.loop(minutes=15)
    async def daily_art_task(self) -> None:
        """Background task that checks every 15 minutes for servers needing art posts."""
        try:
            servers = await self.bot.database.get_servers_needing_art()

            for server_data in servers:
                server_id, channel_id, post_time_str, tz_offset, last_post_date = server_data

                # Parse the post time
                target_time = self.parse_time_string(post_time_str)
                if not target_time:
                    continue

                # Get current date and time for this server's timezone
                current_date = self.get_current_date_for_server(tz_offset)
                current_time = self.get_current_time_for_server(tz_offset)

                # Check if we've already posted today
                if last_post_date == current_date:
                    continue

                # Check if it's time to post (within 15-minute window)
                target_datetime = datetime.combine(datetime.today(), target_time)
                current_datetime = datetime.combine(datetime.today(), current_time)
                time_diff = abs((current_datetime - target_datetime).total_seconds() / 60)

                if time_diff <= 15:
                    # Time to post! Try different museums
                    artwork = None
                    for fetch_func in [self.fetch_met_artwork, self.fetch_art_institute_artwork]:
                        artwork = await fetch_func()
                        if artwork:
                            break

                    if artwork:
                        await self.post_artwork_to_channel(int(server_id), int(channel_id), artwork)
                        # Update last post date
                        await self.bot.database.update_art_last_post_date(
                            int(server_id), current_date
                        )

        except Exception as e:
            self.bot.logger.error(f"Error in daily art task: {e}")

    @daily_art_task.before_loop
    async def before_daily_art_task(self) -> None:
        """Wait for bot to be ready before starting task."""
        await self.bot.wait_until_ready()

    async def analyze_image_with_vision(self, image_url: str, analysis_type: str = "general") -> str:
        """
        Analyze an image using Claude's vision capabilities.

        :param image_url: URL of the image to analyze.
        :param analysis_type: Type of analysis ("general", "beginner", "compare").
        :return: Analysis text.
        """
        if not self.client:
            return "⚠️ AI analysis is not available. Please configure ANTHROPIC_API_KEY."

        try:
            # Download image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=15) as response:
                    if response.status != 200:
                        return "⚠️ Could not download the image for analysis."

                    image_data = await response.read()

                    # Convert to base64
                    image_base64 = base64.b64encode(image_data).decode('utf-8')

                    # Determine media type
                    content_type = response.headers.get('Content-Type', 'image/jpeg')
                    if 'png' in content_type:
                        media_type = "image/png"
                    elif 'webp' in content_type:
                        media_type = "image/webp"
                    elif 'gif' in content_type:
                        media_type = "image/gif"
                    else:
                        media_type = "image/jpeg"

            # Create appropriate prompt based on analysis type
            if analysis_type == "beginner":
                prompt = """Analyze this artwork as if explaining to someone new to art. Keep it friendly and accessible.

Include:
1. **What you see**: Describe the visual elements (colors, shapes, subjects)
2. **Style & Technique**: Explain the artistic style in simple terms
3. **Mood & Feeling**: What emotions or atmosphere does it convey?
4. **Interesting Details**: Point out 2-3 cool things to notice
5. **Why it matters**: Brief context on its significance

Keep it conversational and under 300 words. No jargon!"""

            else:  # general analysis
                prompt = """Provide a comprehensive art analysis covering:

1. **Visual Analysis**: Composition, color palette, technique, style
2. **Artistic Elements**: Use of line, form, space, texture, value
3. **Art Historical Context**: Likely period, movement, or influences
4. **Interpretation**: Themes, symbolism, meaning
5. **Technical Observations**: Medium, methods, skill level

Be insightful and educational. Around 300-400 words."""

            # Call Claude vision API
            message = await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Use Sonnet for better vision analysis
                max_tokens=800,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            return message.content[0].text.strip()

        except Exception as e:
            self.bot.logger.error(f"Error analyzing image: {e}")
            return f"⚠️ Error analyzing image: {str(e)}"

    @commands.hybrid_command(
        name="art-analyze",
        description="Analyze any artwork or image using AI vision"
    )
    @app_commands.describe(
        image_url="URL of the image to analyze (or attach an image)"
    )
    async def art_analyze(self, context: Context, image_url: str = None) -> None:
        """
        Analyze an artwork or image using Claude's vision AI.

        :param context: The command context.
        :param image_url: Optional URL of image to analyze.
        """
        await context.defer()

        # Check for attached image
        if not image_url and context.message.attachments:
            image_url = context.message.attachments[0].url

        if not image_url:
            embed = discord.Embed(
                description="❌ Please provide an image URL or attach an image!",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        # Validate URL
        if not image_url.startswith(('http://', 'https://')):
            embed = discord.Embed(
                description="❌ Please provide a valid image URL!",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        # Analyze the image
        analysis = await self.analyze_image_with_vision(image_url, "general")

        # Create embed
        embed = discord.Embed(
            title="🎨 Artwork Analysis",
            description=analysis,
            color=0x9B59B6
        )
        embed.set_thumbnail(url=image_url)
        embed.set_footer(text="Powered by Claude AI Vision")

        await context.send(embed=embed)

    @commands.hybrid_command(
        name="art-explain",
        description="Get a beginner-friendly explanation of any artwork"
    )
    @app_commands.describe(
        image_url="URL of the image to explain (or attach an image)"
    )
    async def art_explain(self, context: Context, image_url: str = None) -> None:
        """
        Get a simple, beginner-friendly explanation of an artwork.

        :param context: The command context.
        :param image_url: Optional URL of image to explain.
        """
        await context.defer()

        # Check for attached image
        if not image_url and context.message.attachments:
            image_url = context.message.attachments[0].url

        if not image_url:
            embed = discord.Embed(
                description="❌ Please provide an image URL or attach an image!",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        # Validate URL
        if not image_url.startswith(('http://', 'https://')):
            embed = discord.Embed(
                description="❌ Please provide a valid image URL!",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        # Analyze the image (beginner mode)
        explanation = await self.analyze_image_with_vision(image_url, "beginner")

        # Create embed
        embed = discord.Embed(
            title="🎨 Art Explained (Beginner-Friendly)",
            description=explanation,
            color=0x3498DB
        )
        embed.set_thumbnail(url=image_url)
        embed.set_footer(text="Powered by Claude AI Vision")

        await context.send(embed=embed)

    @commands.hybrid_command(
        name="art-compare",
        description="Compare two artworks side by side using AI"
    )
    @app_commands.describe(
        image_url1="URL of the first image",
        image_url2="URL of the second image"
    )
    async def art_compare(self, context: Context, image_url1: str, image_url2: str) -> None:
        """
        Compare two artworks and analyze their similarities and differences.

        :param context: The command context.
        :param image_url1: URL of first image.
        :param image_url2: URL of second image.
        """
        await context.defer()

        if not self.client:
            embed = discord.Embed(
                description="⚠️ AI analysis is not available. Please configure ANTHROPIC_API_KEY.",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        try:
            # Download both images
            images_data = []
            async with aiohttp.ClientSession() as session:
                for url in [image_url1, image_url2]:
                    async with session.get(url, timeout=15) as response:
                        if response.status != 200:
                            embed = discord.Embed(
                                description=f"❌ Could not download image: {url}",
                                color=0xE02B2B
                            )
                            await context.send(embed=embed)
                            return

                        image_data = await response.read()
                        image_base64 = base64.b64encode(image_data).decode('utf-8')

                        content_type = response.headers.get('Content-Type', 'image/jpeg')
                        if 'png' in content_type:
                            media_type = "image/png"
                        elif 'webp' in content_type:
                            media_type = "image/webp"
                        else:
                            media_type = "image/jpeg"

                        images_data.append((image_base64, media_type))

            # Create comparison prompt
            prompt = """Compare these two artworks in detail. Analyze:

1. **Similarities**: What do they have in common? (style, technique, themes, color, composition)
2. **Differences**: How do they differ? (approach, mood, execution, period)
3. **Style & Period**: Identify the likely artistic movements or periods
4. **Technical Comparison**: Compare the techniques and mediums
5. **Overall Assessment**: Which artwork excels in what areas?

Be thorough and insightful. Around 300-400 words."""

            # Call Claude with both images
            message = await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": images_data[0][1],
                                "data": images_data[0][0]
                            }
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": images_data[1][1],
                                "data": images_data[1][0]
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            comparison = message.content[0].text.strip()

            # Create embed
            embed = discord.Embed(
                title="🎨 Artwork Comparison",
                description=comparison,
                color=0xF39C12
            )
            embed.set_footer(text="Powered by Claude AI Vision")

            await context.send(embed=embed)

        except Exception as e:
            self.bot.logger.error(f"Error comparing images: {e}")
            embed = discord.Embed(
                description=f"⚠️ Error comparing images: {str(e)}",
                color=0xE02B2B
            )
            await context.send(embed=embed)

    @commands.hybrid_group(
        name="art-admin",
        description="Admin commands for art feature configuration"
    )
    @commands.has_permissions(administrator=True)
    async def art_admin(self, context: Context) -> None:
        """Admin commands for managing art features."""
        if context.invoked_subcommand is None:
            embed = discord.Embed(
                title="🎨 Art Admin Commands",
                description="Available admin commands:\n"
                "• `/art-admin setup` - Configure daily art posts\n"
                "• `/art-admin toggle` - Enable/disable daily posts\n"
                "• `/art-admin now` - Post artwork immediately\n"
                "• `/art-admin status` - View current configuration",
                color=0x9B59B6
            )
            await context.send(embed=embed)

    @art_admin.command(
        name="setup",
        description="Setup daily art posts for this server"
    )
    @app_commands.describe(
        channel="Channel for daily art posts",
        post_time="Time to post (HH:MM in 24-hour format, e.g., 09:00)",
        timezone_offset="Timezone offset from UTC (e.g., -5 for EST, 0 for UTC)"
    )
    async def art_admin_setup(
        self,
        context: Context,
        channel: discord.TextChannel,
        post_time: str,
        timezone_offset: int = 0
    ) -> None:
        """
        Configure daily art posts for the server.

        :param context: The command context.
        :param channel: Channel to post art in.
        :param post_time: Time to post (HH:MM format).
        :param timezone_offset: Hours offset from UTC.
        """
        # Validate time format
        parsed_time = self.parse_time_string(post_time)
        if not parsed_time:
            embed = discord.Embed(
                description="❌ Invalid time format! Use HH:MM (24-hour format), e.g., 09:00 or 14:30",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        # Validate timezone offset
        if timezone_offset < -12 or timezone_offset > 14:
            embed = discord.Embed(
                description="❌ Invalid timezone offset! Must be between -12 and +14",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        # Save configuration
        await self.bot.database.setup_art_config(
            context.guild.id,
            channel.id,
            post_time,
            timezone_offset
        )

        embed = discord.Embed(
            title="✅ Daily Art Posts Configured!",
            description=f"Art will be posted daily in {channel.mention} at {post_time} (UTC{timezone_offset:+d})",
            color=0x2ECC71
        )
        embed.add_field(
            name="Next Steps",
            value="• Use `/art-admin now` to test immediately\n"
            "• Use `/art-admin toggle` to enable/disable\n"
            "• Use `/art-admin status` to view settings",
            inline=False
        )
        await context.send(embed=embed)

    @art_admin.command(
        name="toggle",
        description="Enable or disable daily art posts"
    )
    async def art_admin_toggle(self, context: Context) -> None:
        """
        Toggle daily art posts on/off.

        :param context: The command context.
        """
        config = await self.bot.database.get_art_config(context.guild.id)

        if not config:
            embed = discord.Embed(
                description="❌ Daily art posts are not configured! Use `/art-admin setup` first.",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        # Toggle the enabled status
        new_status = not config[4]  # enabled is index 4
        await self.bot.database.toggle_art_enabled(context.guild.id, new_status)

        status_text = "✅ enabled" if new_status else "⛔ disabled"
        embed = discord.Embed(
            title=f"Daily Art Posts {status_text.split()[1].title()}",
            description=f"Daily art posts are now {status_text}",
            color=0x2ECC71 if new_status else 0xE02B2B
        )
        await context.send(embed=embed)

    @art_admin.command(
        name="now",
        description="Post an artwork immediately (testing)"
    )
    async def art_admin_now(self, context: Context) -> None:
        """
        Post an artwork immediately for testing.

        :param context: The command context.
        """
        config = await self.bot.database.get_art_config(context.guild.id)

        if not config:
            embed = discord.Embed(
                description="❌ Daily art posts are not configured! Use `/art-admin setup` first.",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        await context.defer()

        channel_id = config[1]

        # Fetch artwork
        artwork = None
        for fetch_func in [self.fetch_met_artwork, self.fetch_art_institute_artwork]:
            artwork = await fetch_func()
            if artwork:
                break

        if not artwork:
            embed = discord.Embed(
                description="⚠️ Could not fetch artwork at this time. Please try again.",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        # Post artwork
        success = await self.post_artwork_to_channel(context.guild.id, channel_id, artwork)

        if success:
            embed = discord.Embed(
                title="✅ Artwork Posted!",
                description=f"Posted **{artwork['title']}** by {artwork['artist']}",
                color=0x2ECC71
            )
        else:
            embed = discord.Embed(
                description="⚠️ Failed to post artwork. Check channel permissions.",
                color=0xE02B2B
            )

        await context.send(embed=embed)

    @art_admin.command(
        name="status",
        description="View current art configuration"
    )
    async def art_admin_status(self, context: Context) -> None:
        """
        Display current art post configuration.

        :param context: The command context.
        """
        config = await self.bot.database.get_art_config(context.guild.id)

        if not config:
            embed = discord.Embed(
                description="❌ Daily art posts are not configured!\n\nUse `/art-admin setup` to get started.",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        server_id, channel_id, post_time, tz_offset, enabled, last_post_date, focus_areas, include_contemporary = config

        channel = self.bot.get_channel(channel_id)
        channel_mention = channel.mention if channel else f"Unknown Channel ({channel_id})"

        status_emoji = "✅" if enabled else "⛔"
        status_text = "Enabled" if enabled else "Disabled"

        embed = discord.Embed(
            title="🎨 Art Configuration Status",
            color=0x2ECC71 if enabled else 0xE02B2B
        )

        embed.add_field(name="Status", value=f"{status_emoji} {status_text}", inline=True)
        embed.add_field(name="Channel", value=channel_mention, inline=True)
        embed.add_field(name="Post Time", value=f"{post_time} (UTC{tz_offset:+d})", inline=True)
        embed.add_field(name="Last Posted", value=last_post_date or "Never", inline=True)
        embed.add_field(name="Focus Areas", value=focus_areas or "All", inline=True)
        embed.add_field(name="Include Contemporary", value="Yes" if include_contemporary else "No", inline=True)

        embed.set_footer(text="Use /art-admin to manage settings")

        await context.send(embed=embed)

    @commands.hybrid_command(
        name="art-help",
        description="Get help with art discovery features"
    )
    async def art_help(self, context: Context) -> None:
        """
        Display help information for art commands.

        :param context: The command context.
        """
        embed = discord.Embed(
            title="🎨 Art Discovery Guide",
            description="Explore, learn about, and analyze artworks from world-class museums!",
            color=0x9B59B6
        )

        embed.add_field(
            name="📅 Daily Art Posts",
            value="Receive beautiful artworks daily with AI-generated stories and context. "
            "Admins can configure this with `/art-admin setup`.",
            inline=False
        )

        embed.add_field(
            name="🔍 Analysis Commands",
            value="**`/art-analyze <image>`** - Get a detailed artistic analysis\n"
            "**`/art-explain <image>`** - Get a beginner-friendly explanation\n"
            "**`/art-compare <image1> <image2>`** - Compare two artworks\n\n"
            "*Attach an image or provide a URL!*",
            inline=False
        )

        embed.add_field(
            name="🏛️ Museum Sources",
            value="• Metropolitan Museum of Art\n"
            "• Art Institute of Chicago\n"
            "• More museums coming soon!",
            inline=False
        )

        embed.add_field(
            name="🎓 Educational Features",
            value="• Learn about art history, movements, and techniques\n"
            "• Discover artists from different periods and cultures\n"
            "• Develop visual literacy and critical thinking\n"
            "• Engage in discussions about art and creativity",
            inline=False
        )

        embed.add_field(
            name="👑 Admin Commands",
            value="**`/art-admin setup`** - Configure daily posts\n"
            "**`/art-admin toggle`** - Enable/disable\n"
            "**`/art-admin now`** - Post immediately\n"
            "**`/art-admin status`** - View configuration",
            inline=False
        )

        embed.set_footer(text="🤖 Powered by Claude AI Vision • Art from public domain collections")

        await context.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(Art(bot))
