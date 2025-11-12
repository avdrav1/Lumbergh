"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://github.com/kkrypt0nn)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.3.0
"""

import os
import re
import random
import sys
from datetime import datetime, time, timedelta
from typing import Optional, Dict, List, Tuple

import discord
from anthropic import AsyncAnthropic
from discord import app_commands
from discord.ext import commands, tasks
from discord.ext.commands import Context

# Import helpers
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import thread_manager
from helpers.claude_cog import ClaudeAICog


class Creative(ClaudeAICog, name="creative"):
    def __init__(self, bot) -> None:
        super().__init__(bot, cog_name="Creative cog")

        # Start background tasks
        self.check_daily_prompts.start()
        self.check_weekly_challenges.start()

        # Genre definitions
        self.STORY_GENRES = ["fantasy", "scifi", "mystery", "romance", "horror", "thriller", "adventure", "historical", "random"]
        self.MUSIC_GENRES = ["pop", "rock", "jazz", "blues", "country", "hiphop", "electronic", "classical", "folk", "random"]
        self.ART_STYLES = ["realistic", "anime", "cartoon", "abstract", "impressionist", "surreal", "minimalist", "steampunk", "cyberpunk", "random"]

        # Music moods
        self.MUSIC_MOODS = ["happy", "sad", "energetic", "calm", "mysterious", "romantic", "dark", "uplifting"]

        # Color palette themes
        self.PALETTE_THEMES = ["nature", "sunset", "ocean", "forest", "autumn", "winter", "neon", "pastel", "monochrome", "vibrant", "random"]

        # Character archetypes
        self.CHARACTER_ARCHETYPES = ["hero", "villain", "mentor", "trickster", "rebel", "innocent", "explorer", "sage", "random"]

    def cog_unload(self) -> None:
        """Clean up when cog is unloaded."""
        self.check_daily_prompts.cancel()
        self.check_weekly_challenges.cancel()

    # ==================== HELPER METHODS ====================

    async def get_monthly_theme(self, server_id: int) -> Optional[str]:
        """Get the current monthly theme for a server."""
        try:
            async with self.bot.database.connection.execute(
                "SELECT current_month_theme FROM creative_config WHERE server_id = ?",
                (server_id,)
            ) as cursor:
                result = await cursor.fetchone()
                return result[0] if result and result[0] else None
        except Exception:
            return None

    def get_current_date_for_server(self, timezone_offset: int) -> str:
        """Get current date string for a server's timezone."""
        utc_now = datetime.utcnow()
        server_time = utc_now + timedelta(hours=timezone_offset)
        return server_time.strftime("%Y-%m-%d")

    # ==================== WRITING PROMPTS ====================

    async def generate_story_prompt(self, genre: str = "random", theme: Optional[str] = None) -> str:
        """Generate a story writing prompt."""
        if not self.client:
            return "A mysterious stranger arrives in a small town with a secret that could change everything."

        theme_text = f" incorporating the theme '{theme}'" if theme else ""
        genre_desc = genre if genre != "random" else "any genre"

        prompt = f"""Generate a compelling story writing prompt for {genre_desc}{theme_text}.

The prompt should:
- Be 1-2 sentences long
- Include an interesting character or situation
- Suggest conflict or mystery
- Inspire creativity
- Be suitable for any skill level

Just provide the prompt, nothing else."""

        try:
            message = await self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text.strip().strip('"').strip("'")
        except Exception as e:
            self.bot.logger.error(f"Error generating story prompt: {e}")
            return "Write about a discovery that changes someone's understanding of their past."

    async def generate_writing_exercise(self, style: str = "general") -> str:
        """Generate a writing exercise or technique prompt."""
        if not self.client:
            return "Practice writing vivid sensory descriptions by describing your favorite meal using all five senses."

        styles = {
            "general": "general writing practice",
            "description": "descriptive writing focused on sensory details",
            "dialogue": "dialogue writing and character voice",
            "pacing": "story pacing and tension building",
            "character": "character development and depth",
            "worldbuilding": "world building and setting creation"
        }

        style_desc = styles.get(style, styles["general"])

        prompt = f"""Generate a focused writing exercise for {style_desc}.

The exercise should:
- Be specific and actionable
- Be completable in 15-30 minutes
- Help develop a particular skill
- Include clear instructions

Just provide the exercise, nothing else."""

        try:
            message = await self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text.strip().strip('"').strip("'")
        except Exception as e:
            self.bot.logger.error(f"Error generating writing exercise: {e}")
            return "Write a conversation between two characters who are hiding secrets from each other."

    # ==================== MUSIC PROMPTS ====================

    async def generate_song_prompt(self, genre: str = "random", theme: Optional[str] = None) -> Dict:
        """Generate a songwriting prompt with title, theme, and opening line."""
        if not self.client:
            return {
                "title": "Midnight Dreams",
                "theme": "longing and hope",
                "opening": "Under the stars, I wonder where you are"
            }

        theme_text = f" about {theme}" if theme else ""
        genre_desc = genre if genre != "random" else "any genre"

        prompt = f"""Generate a songwriting prompt for {genre_desc}{theme_text}.

Format your response EXACTLY like this:
TITLE: [a catchy song title]
THEME: [the main theme/emotion in 3-5 words]
OPENING: [a powerful opening line for the song]

Make it inspiring and suitable for songwriters of any level."""

        try:
            message = await self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )

            response = message.content[0].text.strip()
            title = theme_val = opening = ""

            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('TITLE:'):
                    title = line.replace('TITLE:', '').strip().strip('"').strip("'")
                elif line.startswith('THEME:'):
                    theme_val = line.replace('THEME:', '').strip()
                elif line.startswith('OPENING:'):
                    opening = line.replace('OPENING:', '').strip().strip('"').strip("'")

            return {
                "title": title or "Untitled Song",
                "theme": theme_val or "life and love",
                "opening": opening or "A melody plays in my mind"
            }

        except Exception as e:
            self.bot.logger.error(f"Error generating song prompt: {e}")
            return {
                "title": "New Horizons",
                "theme": "change and growth",
                "opening": "Every ending is a new beginning"
            }

    async def generate_chord_progression(self, genre: str = "pop", mood: str = "happy") -> Dict:
        """Generate a chord progression."""
        if not self.client:
            return {
                "progression": "C - G - Am - F",
                "key": "C Major",
                "description": "Classic pop progression, uplifting and familiar"
            }

        prompt = f"""Generate a chord progression for {genre} music with a {mood} mood.

Format your response EXACTLY like this:
CHORDS: [chord progression using standard notation, e.g., C - G - Am - F]
KEY: [the key, e.g., C Major]
DESCRIPTION: [one sentence describing the feel and usage]

Keep it practical for musicians."""

        try:
            message = await self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )

            response = message.content[0].text.strip()
            chords = key = description = ""

            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('CHORDS:'):
                    chords = line.replace('CHORDS:', '').strip()
                elif line.startswith('KEY:'):
                    key = line.replace('KEY:', '').strip()
                elif line.startswith('DESCRIPTION:'):
                    description = line.replace('DESCRIPTION:', '').strip()

            return {
                "progression": chords or "C - Am - F - G",
                "key": key or "C Major",
                "description": description or "A versatile progression"
            }

        except Exception as e:
            self.bot.logger.error(f"Error generating chord progression: {e}")
            return {
                "progression": "G - D - Em - C",
                "key": "G Major",
                "description": "Popular and emotional progression"
            }

    async def generate_lyrics(self, genre: str = "pop", theme: str = "love") -> str:
        """Generate lyric ideas or a verse."""
        if not self.client:
            return "Verse:\nIn the quiet of the night\nI hear your voice calling\nThrough the distance and the time\nOur love keeps holding on"

        prompt = f"""Generate lyrics for a {genre} song about {theme}.

Provide a verse (4-8 lines) that:
- Captures the theme emotionally
- Uses vivid imagery
- Has a natural rhythm
- Fits the genre style

Just provide the lyrics, no labels or explanations."""

        try:
            message = await self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text.strip()
        except Exception as e:
            self.bot.logger.error(f"Error generating lyrics: {e}")
            return "Walking through memories\nOf days we left behind\nEvery moment tells a story\nOf what we used to find"

    async def explain_music_theory(self, topic: str) -> str:
        """Explain a music theory concept."""
        if not self.client:
            return f"Music theory explanation for '{topic}' is currently unavailable."

        prompt = f"""Explain the music theory concept: {topic}

Provide a clear, concise explanation that:
- Defines the concept simply
- Gives practical examples
- Explains why it matters to musicians
- Is suitable for beginners to intermediate musicians
- Is 2-4 paragraphs long

Be helpful and educational."""

        try:
            message = await self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text.strip()
        except Exception as e:
            self.bot.logger.error(f"Error explaining music theory: {e}")
            return f"I couldn't explain '{topic}' right now. Please try again later."

    # ==================== ART PROMPTS ====================

    async def generate_draw_prompt(self, style: str = "random", theme: Optional[str] = None) -> str:
        """Generate a drawing/art prompt."""
        if not self.client:
            return "Draw a magical forest at twilight with glowing mushrooms and ancient trees."

        theme_text = f" incorporating {theme}" if theme else ""
        style_desc = style if style != "random" else "any style"

        prompt = f"""Generate a drawing/art prompt in {style_desc} style{theme_text}.

The prompt should:
- Describe a clear subject or scene
- Include interesting visual details
- Be achievable for various skill levels
- Inspire creativity
- Be 1-2 sentences

Just provide the prompt, nothing else."""

        try:
            message = await self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text.strip().strip('"').strip("'")
        except Exception as e:
            self.bot.logger.error(f"Error generating draw prompt: {e}")
            return "Create a portrait of a character with an unusual superpower that's subtly visible in the artwork."

    async def generate_style_challenge(self) -> Dict:
        """Generate an art style challenge."""
        if not self.client:
            return {
                "style": "Watercolor",
                "subject": "A peaceful countryside landscape",
                "constraint": "Use only cool colors (blues, greens, purples)"
            }

        prompt = """Generate an art style challenge.

Format your response EXACTLY like this:
STYLE: [art style/medium, e.g., Watercolor, Digital Art, Pen and Ink]
SUBJECT: [what to draw]
CONSTRAINT: [one creative limitation or requirement]

Make it fun and challenging."""

        try:
            message = await self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )

            response = message.content[0].text.strip()
            style = subject = constraint = ""

            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('STYLE:'):
                    style = line.replace('STYLE:', '').strip()
                elif line.startswith('SUBJECT:'):
                    subject = line.replace('SUBJECT:', '').strip()
                elif line.startswith('CONSTRAINT:'):
                    constraint = line.replace('CONSTRAINT:', '').strip()

            return {
                "style": style or "Mixed Media",
                "subject": subject or "A mysterious character",
                "constraint": constraint or "Use limited color palette"
            }

        except Exception as e:
            self.bot.logger.error(f"Error generating style challenge: {e}")
            return {
                "style": "Line Art",
                "subject": "An imaginary creature",
                "constraint": "Use only black and white"
            }

    async def generate_color_palette(self, theme: str = "random") -> Dict:
        """Generate a color palette with hex codes."""
        if not self.client:
            return {
                "name": "Ocean Depths",
                "colors": ["#001f3f", "#0074D9", "#7FDBFF", "#39CCCC", "#3D9970"],
                "description": "Deep blues and teals inspired by the ocean"
            }

        theme_desc = theme if theme != "random" else "any theme"

        prompt = f"""Generate a color palette for {theme_desc}.

Format your response EXACTLY like this:
NAME: [palette name]
COLORS: [5 hex codes separated by commas, e.g., #FF6B6B, #4ECDC4, #45B7D1, #96CEB4, #FFEAA7]
DESCRIPTION: [one sentence about the palette's mood/use]

Use valid 6-digit hex codes."""

        try:
            message = await self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )

            response = message.content[0].text.strip()
            name = colors_str = description = ""

            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('NAME:'):
                    name = line.replace('NAME:', '').strip()
                elif line.startswith('COLORS:'):
                    colors_str = line.replace('COLORS:', '').strip()
                elif line.startswith('DESCRIPTION:'):
                    description = line.replace('DESCRIPTION:', '').strip()

            # Parse colors
            colors = [c.strip() for c in colors_str.split(',') if c.strip().startswith('#')]

            return {
                "name": name or "Creative Palette",
                "colors": colors if len(colors) >= 4 else ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"],
                "description": description or "A vibrant and inspiring palette"
            }

        except Exception as e:
            self.bot.logger.error(f"Error generating color palette: {e}")
            return {
                "name": "Sunset Glow",
                "colors": ["#FF6B6B", "#FFA07A", "#FFD700", "#FF8C42", "#FF5E5B"],
                "description": "Warm sunset colors"
            }

    async def generate_character(self, archetype: str = "random") -> str:
        """Generate a detailed character description."""
        if not self.client:
            return "A weathered explorer in their 40s with kind eyes and calloused hands, carrying maps of places that no longer exist and stories of roads less traveled."

        archetype_desc = archetype if archetype != "random" else "any archetype"

        prompt = f"""Generate a detailed character description for a {archetype_desc} character.

Include:
- Age and appearance details
- Personality traits
- A unique characteristic or quirk
- Hint at their background/story

Keep it to 2-3 sentences that inspire artists. No name needed."""

        try:
            message = await self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text.strip()
        except Exception as e:
            self.bot.logger.error(f"Error generating character: {e}")
            return "A young inventor with paint-stained fingers and wild hair, wearing goggles pushed up on their forehead and carrying a notebook filled with sketches of impossible machines."

    # ==================== COLLABORATION HELPERS ====================

    async def continue_story_with_ai(self, story_id: int) -> str:
        """Have AI continue a collaborative story."""
        if not self.client:
            return None

        try:
            # Get the story and all contributions
            async with self.bot.database.connection.execute(
                "SELECT prompt, work_type FROM collaborative_works WHERE id = ?",
                (story_id,)
            ) as cursor:
                work = await cursor.fetchone()

            if not work:
                return None

            prompt_text, work_type = work

            async with self.bot.database.connection.execute(
                "SELECT content FROM work_contributions WHERE work_id = ? ORDER BY contribution_number ASC",
                (story_id,)
            ) as cursor:
                contributions = await cursor.fetchall()

            # Build the story so far
            story_so_far = f"Original prompt: {prompt_text}\n\n"
            story_so_far += "\n\n".join([c[0] for c in contributions])

            prompt = f"""Continue this collaborative {work_type} story with the next segment.

{story_so_far}

Write the next 100-200 words continuing the story naturally. Match the tone and style established so far."""

            message = await self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            return message.content[0].text.strip()

        except Exception as e:
            self.bot.logger.error(f"Error continuing story with AI: {e}")
            return None

    # ==================== CONSOLIDATED COMMANDS ====================

    @commands.hybrid_command(
        name="creative-prompt",
        description="Generate creative prompts for writing, music, or art",
    )
    @app_commands.describe(
        prompt_type="Type of prompt to generate",
        genre="Genre or style for the prompt",
        theme="Optional theme to incorporate"
    )
    @app_commands.choices(prompt_type=[
        app_commands.Choice(name="Story Prompt", value="story"),
        app_commands.Choice(name="Writing Exercise", value="writing"),
        app_commands.Choice(name="Song Prompt", value="song"),
        app_commands.Choice(name="Chord Progression", value="chords"),
        app_commands.Choice(name="Lyrics", value="lyrics"),
        app_commands.Choice(name="Music Theory", value="theory"),
        app_commands.Choice(name="Drawing Prompt", value="draw"),
        app_commands.Choice(name="Style Challenge", value="style"),
        app_commands.Choice(name="Color Palette", value="palette"),
        app_commands.Choice(name="Character Design", value="character")
    ])
    async def creative_prompt(
        self,
        context: Context,
        prompt_type: str,
        genre: Optional[str] = None,
        theme: Optional[str] = None
    ) -> None:
        """
        Generate a creative prompt.

        :param context: The command context.
        :param prompt_type: Type of prompt.
        :param genre: Genre or style.
        :param theme: Optional theme.
        """
        await context.defer()

        monthly_theme = await self.get_monthly_theme(context.guild.id)
        if monthly_theme and not theme:
            theme = monthly_theme

        # Route to appropriate helper based on prompt_type
        if prompt_type == "story":
            genre = genre or "random"
            if genre not in self.STORY_GENRES:
                genre = "random"
            prompt_text = await self.generate_story_prompt(genre, theme)
            embed = discord.Embed(
                title="✍️ Story Writing Prompt",
                description=prompt_text,
                color=0x9B59B6
            )
            if genre != "random":
                embed.add_field(name="Genre", value=genre.title(), inline=True)
            if theme:
                embed.add_field(name="Theme", value=theme.title(), inline=True)
            embed.set_footer(text="Use /creative-collab to start a collaborative story!")

        elif prompt_type == "writing":
            style = genre or "general"
            exercise = await self.generate_writing_exercise(style)
            embed = discord.Embed(
                title="📝 Writing Exercise",
                description=exercise,
                color=0x3498DB
            )
            if style != "general":
                embed.add_field(name="Focus", value=style.title(), inline=True)
            embed.set_footer(text="Take 15-30 minutes to complete this exercise!")

        elif prompt_type == "song":
            genre = genre or "random"
            if genre not in self.MUSIC_GENRES:
                genre = "random"
            prompt_data = await self.generate_song_prompt(genre, theme)
            embed = discord.Embed(
                title="🎵 Songwriting Prompt",
                color=0xE91E63
            )
            embed.add_field(name="Song Title", value=prompt_data["title"], inline=False)
            embed.add_field(name="Theme", value=prompt_data["theme"], inline=False)
            embed.add_field(name="Opening Line", value=f"*\"{prompt_data['opening']}\"*", inline=False)
            if genre != "random":
                embed.set_footer(text=f"Genre: {genre.title()}")

        elif prompt_type == "chords":
            genre = genre or "pop"
            mood = theme or "happy"
            if genre not in self.MUSIC_GENRES:
                genre = "pop"
            if mood not in self.MUSIC_MOODS:
                mood = "happy"
            progression_data = await self.generate_chord_progression(genre, mood)
            embed = discord.Embed(
                title="🎸 Chord Progression",
                color=0xFF5722
            )
            embed.add_field(name="Chords", value=f"**{progression_data['progression']}**", inline=False)
            embed.add_field(name="Key", value=progression_data["key"], inline=True)
            embed.add_field(name="Description", value=progression_data["description"], inline=False)
            embed.set_footer(text=f"Genre: {genre.title()} | Mood: {mood.title()}")

        elif prompt_type == "lyrics":
            genre = genre or "pop"
            theme = theme or "love"
            if genre not in self.MUSIC_GENRES:
                genre = "pop"
            lyrics_text = await self.generate_lyrics(genre, theme)
            embed = discord.Embed(
                title="🎤 Lyric Ideas",
                description=f"```\n{lyrics_text}\n```",
                color=0x9C27B0
            )
            embed.set_footer(text=f"Genre: {genre.title()} | Theme: {theme}")

        elif prompt_type == "theory":
            if not theme and not genre:
                embed = discord.Embed(
                    description="❌ Please provide a music theory topic to explain (use the theme or genre parameter).",
                    color=0xE02B2B
                )
                await context.send(embed=embed)
                return
            topic = theme or genre
            explanation = await self.explain_music_theory(topic)
            embed = discord.Embed(
                title=f"🎼 Music Theory: {topic.title()}",
                description=explanation,
                color=0x673AB7
            )

        elif prompt_type == "draw":
            style = genre or "random"
            if style not in self.ART_STYLES:
                style = "random"
            prompt_text = await self.generate_draw_prompt(style, theme)
            embed = discord.Embed(
                title="🎨 Drawing Prompt",
                description=prompt_text,
                color=0xFF9800
            )
            if style != "random":
                embed.add_field(name="Style", value=style.title(), inline=True)
            if theme:
                embed.add_field(name="Theme", value=theme.title(), inline=True)
            embed.set_footer(text="Share your artwork using /creative-gallery submit!")

        elif prompt_type == "style":
            challenge_data = await self.generate_style_challenge()
            embed = discord.Embed(
                title="🎨 Style Challenge",
                color=0xFF5722
            )
            embed.add_field(name="Style/Medium", value=challenge_data["style"], inline=False)
            embed.add_field(name="Subject", value=challenge_data["subject"], inline=False)
            embed.add_field(name="Constraint", value=challenge_data["constraint"], inline=False)
            embed.set_footer(text="Push your creative boundaries!")

        elif prompt_type == "palette":
            palette_theme = genre or theme or "random"
            if palette_theme not in self.PALETTE_THEMES:
                palette_theme = "random"
            palette_data = await self.generate_color_palette(palette_theme)
            embed = discord.Embed(
                title=f"🎨 {palette_data['name']}",
                description=palette_data["description"],
                color=int(palette_data["colors"][0].replace('#', ''), 16)
            )
            colors_text = ""
            for i, color in enumerate(palette_data["colors"], 1):
                colors_text += f"**{i}.** `{color}` ███\n"
            embed.add_field(name="Colors", value=colors_text, inline=False)
            embed.set_footer(text="Copy hex codes to use in your digital art!")

        elif prompt_type == "character":
            archetype = genre or "random"
            if archetype not in self.CHARACTER_ARCHETYPES:
                archetype = "random"
            character_desc = await self.generate_character(archetype)
            embed = discord.Embed(
                title="👤 Character Generator",
                description=character_desc,
                color=0x795548
            )
            if archetype != "random":
                embed.set_footer(text=f"Archetype: {archetype.title()}")

        await context.send(embed=embed)

    @commands.hybrid_command(
        name="creative-collab",
        description="Start a collaborative story in a thread",
    )
    @app_commands.describe(prompt="The story prompt or opening")
    async def creative_collab(self, context: Context, prompt: str) -> None:
        """
        Start a collaborative story.

        :param context: The command context.
        :param prompt: The story prompt.
        """
        try:
            # Create embed
            embed = discord.Embed(
                title="📖 New Collaborative Story",
                description=f"**Prompt:** {prompt}\n\n*Add to this story using the thread below!*",
                color=0x9B59B6
            )
            embed.set_footer(text=f"Started by {context.author.display_name}")

            # Send message and create thread
            message = await context.send(embed=embed)
            thread = await thread_manager.create_bot_thread(
                message=message,
                thread_name=f"Story: {prompt[:50]}...",
                auto_archive_duration=1440,
                logger=self.bot.logger
            )

            if not thread:
                await context.send("⚠️ Could not create thread. Please check bot permissions.")
                return

            # Save to database
            await self.bot.database.connection.execute(
                """INSERT INTO collaborative_works (server_id, channel_id, thread_id, work_type, title, prompt, started_by_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (context.guild.id, context.channel.id, thread.id, "story", prompt[:100], prompt, context.author.id)
            )
            await self.bot.database.connection.commit()

            # Send instructions in thread
            await thread.send(
                "Welcome to the collaborative story! 📖\n\n"
                "**How to participate:**\n"
                "• Write 100-500 words continuing the story\n"
                "• Mention @Lumbergh to have AI continue the story\n"
                "• Build on what others have written\n"
                "• Have fun and be creative!\n\n"
                "*The story begins...*"
            )

            self.bot.logger.info(f"Collaborative story started in guild {context.guild.id}")

        except Exception as e:
            self.bot.logger.error(f"Error starting collaborative story: {e}")
            embed = discord.Embed(
                description="❌ Failed to start collaborative story. Please try again.",
                color=0xE02B2B
            )
            await context.send(embed=embed)

    @commands.hybrid_command(
        name="creative-gallery",
        description="Manage your creative gallery",
    )
    @app_commands.describe(
        action="Gallery action",
        work_type="Type of work (for submit/view)",
        title="Title of your work (for submit)",
        description="Description (for submit)",
        image_url="Optional image URL (for submit)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Submit Work", value="submit"),
        app_commands.Choice(name="View Gallery", value="view"),
        app_commands.Choice(name="My Works", value="my-work")
    ])
    async def creative_gallery(
        self,
        context: Context,
        action: str,
        work_type: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> None:
        """
        Manage creative gallery.

        :param context: The command context.
        :param action: The action to perform.
        :param work_type: Type of work.
        :param title: Work title.
        :param description: Work description.
        :param image_url: Optional image URL.
        """
        if action == "submit":
            if not all([work_type, title, description]):
                embed = discord.Embed(
                    description="❌ To submit work, you must provide: work_type, title, and description.",
                    color=0xE02B2B
                )
                await context.send(embed=embed)
                return

            try:
                # Save to gallery
                await self.bot.database.connection.execute(
                    """INSERT INTO creative_gallery (server_id, user_id, work_type, title, content, image_url)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (context.guild.id, context.author.id, work_type, title, description, image_url)
                )
                await self.bot.database.connection.commit()

                # Create showcase embed
                embed = discord.Embed(
                    title=f"✨ {title}",
                    description=description,
                    color=0xFFD700
                )

                embed.set_author(
                    name=context.author.display_name,
                    icon_url=context.author.display_avatar.url
                )

                embed.add_field(name="Type", value=work_type.title(), inline=True)

                if image_url:
                    embed.set_image(url=image_url)

                embed.set_footer(text="React to show appreciation!")

                await context.send(embed=embed)
                self.bot.logger.info(f"Work showcased in guild {context.guild.id}")

            except Exception as e:
                self.bot.logger.error(f"Error showcasing work: {e}")
                embed = discord.Embed(
                    description="❌ Failed to showcase work. Please try again.",
                    color=0xE02B2B
                )
                await context.send(embed=embed)

        elif action == "view":
            try:
                if work_type:
                    query = "SELECT title, user_id, work_type, reactions FROM creative_gallery WHERE server_id = ? AND work_type = ? ORDER BY showcased_at DESC LIMIT 10"
                    params = (context.guild.id, work_type)
                else:
                    query = "SELECT title, user_id, work_type, reactions FROM creative_gallery WHERE server_id = ? ORDER BY showcased_at DESC LIMIT 10"
                    params = (context.guild.id,)

                async with self.bot.database.connection.execute(query, params) as cursor:
                    results = await cursor.fetchall()

                if not results:
                    embed = discord.Embed(
                        description="No works in the gallery yet! Use `/creative-gallery submit` to add yours.",
                        color=0x3498DB
                    )
                    await context.send(embed=embed)
                    return

                embed = discord.Embed(
                    title="🖼️ Creative Gallery",
                    description=f"Recent works{' ('+work_type+')' if work_type else ''}",
                    color=0xFFD700
                )

                for title_val, user_id, wtype, reactions in results:
                    embed.add_field(
                        name=f"{title_val}",
                        value=f"by <@{user_id}> • {wtype.title()} • {reactions} ❤️",
                        inline=False
                    )

                await context.send(embed=embed)

            except Exception as e:
                self.bot.logger.error(f"Error browsing gallery: {e}")
                embed = discord.Embed(
                    description="❌ Failed to load gallery. Please try again.",
                    color=0xE02B2B
                )
                await context.send(embed=embed)

        elif action == "my-work":
            try:
                query = "SELECT title, work_type, showcased_at, reactions FROM creative_gallery WHERE server_id = ? AND user_id = ? ORDER BY showcased_at DESC LIMIT 10"
                params = (context.guild.id, context.author.id)

                async with self.bot.database.connection.execute(query, params) as cursor:
                    results = await cursor.fetchall()

                if not results:
                    embed = discord.Embed(
                        description="You haven't submitted any works yet! Use `/creative-gallery submit` to add your first piece.",
                        color=0x3498DB
                    )
                    await context.send(embed=embed)
                    return

                embed = discord.Embed(
                    title=f"🖼️ {context.author.display_name}'s Gallery",
                    description="Your submitted works",
                    color=0xFFD700
                )

                for title_val, wtype, showcased_at, reactions in results:
                    embed.add_field(
                        name=f"{title_val}",
                        value=f"{wtype.title()} • {showcased_at} • {reactions} ❤️",
                        inline=False
                    )

                await context.send(embed=embed)

            except Exception as e:
                self.bot.logger.error(f"Error fetching user works: {e}")
                embed = discord.Embed(
                    description="❌ Failed to load your works. Please try again.",
                    color=0xE02B2B
                )
                await context.send(embed=embed)

    @commands.hybrid_command(
        name="creative-challenge",
        description="Participate in creative challenges",
    )
    @app_commands.describe(
        action="Challenge action",
        challenge_id="Challenge ID",
        submission="Your work (for submit)",
        url="Optional URL (for submit)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="View Challenge", value="view"),
        app_commands.Choice(name="Submit Work", value="submit")
    ])
    async def creative_challenge(
        self,
        context: Context,
        action: str,
        challenge_id: int,
        submission: Optional[str] = None,
        url: Optional[str] = None
    ) -> None:
        """
        Participate in challenges.

        :param context: The command context.
        :param action: The action to perform.
        :param challenge_id: Challenge ID.
        :param submission: Submission text.
        :param url: Optional URL.
        """
        if action == "submit":
            if not submission:
                embed = discord.Embed(
                    description="❌ Please provide your submission text.",
                    color=0xE02B2B
                )
                await context.send(embed=embed)
                return

            try:
                # Check if challenge exists and is active
                async with self.bot.database.connection.execute(
                    "SELECT challenge_type, prompt, end_date FROM creative_challenges WHERE id = ? AND server_id = ?",
                    (challenge_id, context.guild.id)
                ) as cursor:
                    challenge = await cursor.fetchone()

                if not challenge:
                    embed = discord.Embed(
                        description=f"❌ Challenge #{challenge_id} not found.",
                        color=0xE02B2B
                    )
                    await context.send(embed=embed)
                    return

                challenge_type, prompt, end_date = challenge

                # Check if challenge has ended
                if datetime.utcnow().strftime("%Y-%m-%d") > end_date:
                    embed = discord.Embed(
                        description="❌ This challenge has ended.",
                        color=0xE02B2B
                    )
                    await context.send(embed=embed)
                    return

                # Submit
                await self.bot.database.connection.execute(
                    """INSERT INTO challenge_submissions (challenge_id, user_id, submission_text, submission_url)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(challenge_id, user_id) DO UPDATE SET
                       submission_text = excluded.submission_text,
                       submission_url = excluded.submission_url,
                       submitted_at = CURRENT_TIMESTAMP""",
                    (challenge_id, context.author.id, submission, url)
                )
                await self.bot.database.connection.commit()

                embed = discord.Embed(
                    title="✅ Submission Received!",
                    description=f"Your work has been submitted to Challenge #{challenge_id}",
                    color=0x2ECC71
                )

                embed.add_field(name="Your Submission", value=submission[:200] + "..." if len(submission) > 200 else submission, inline=False)
                if url:
                    embed.add_field(name="URL", value=url, inline=False)

                embed.set_footer(text="Others can vote on submissions after the challenge ends!")

                await context.send(embed=embed)
                self.bot.logger.info(f"Challenge submission from user {context.author.id} in guild {context.guild.id}")

            except Exception as e:
                self.bot.logger.error(f"Error submitting to challenge: {e}")
                embed = discord.Embed(
                    description="❌ Failed to submit. Please try again.",
                    color=0xE02B2B
                )
                await context.send(embed=embed)

        elif action == "view":
            try:
                # Get challenge info
                async with self.bot.database.connection.execute(
                    "SELECT challenge_type, prompt, start_date, end_date FROM creative_challenges WHERE id = ? AND server_id = ?",
                    (challenge_id, context.guild.id)
                ) as cursor:
                    challenge = await cursor.fetchone()

                if not challenge:
                    embed = discord.Embed(
                        description=f"❌ Challenge #{challenge_id} not found.",
                        color=0xE02B2B
                    )
                    await context.send(embed=embed)
                    return

                challenge_type, prompt, start_date, end_date = challenge

                # Get submissions
                async with self.bot.database.connection.execute(
                    "SELECT user_id, submission_text, votes FROM challenge_submissions WHERE challenge_id = ? ORDER BY votes DESC LIMIT 10",
                    (challenge_id,)
                ) as cursor:
                    submissions = await cursor.fetchall()

                embed = discord.Embed(
                    title=f"📋 Challenge #{challenge_id} - {challenge_type.title()}",
                    description=prompt,
                    color=0x3498DB
                )

                embed.add_field(name="Duration", value=f"{start_date} to {end_date}", inline=False)

                if submissions:
                    for idx, (user_id, text, votes) in enumerate(submissions, 1):
                        embed.add_field(
                            name=f"{idx}. <@{user_id}> ({votes} votes)",
                            value=text[:100] + "..." if len(text) > 100 else text,
                            inline=False
                        )
                else:
                    embed.add_field(name="Submissions", value="No submissions yet.", inline=False)

                await context.send(embed=embed)

            except Exception as e:
                self.bot.logger.error(f"Error viewing challenge: {e}")
                embed = discord.Embed(
                    description="❌ Failed to load challenge.",
                    color=0xE02B2B
                )
                await context.send(embed=embed)

    @commands.hybrid_command(
        name="creative-admin",
        description="Admin commands for creative studio (Admin only)",
    )
    @app_commands.describe(
        action="Admin action",
        channel="Channel for daily prompts (for schedule)",
        time="Post time HH:MM (for schedule)",
        timezone="UTC offset (for schedule)",
        theme="Monthly theme (for theme)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Schedule Daily Prompts", value="schedule"),
        app_commands.Choice(name="Set Monthly Theme", value="theme"),
        app_commands.Choice(name="View Config", value="config")
    ])
    @commands.has_permissions(administrator=True)
    async def creative_admin(
        self,
        context: Context,
        action: str,
        channel: Optional[discord.TextChannel] = None,
        time: Optional[str] = None,
        timezone: Optional[int] = None,
        theme: Optional[str] = None
    ) -> None:
        """
        Admin commands for creative studio.

        :param context: The command context.
        :param action: Admin action.
        :param channel: Channel for prompts.
        :param time: Post time.
        :param timezone: Timezone offset.
        :param theme: Monthly theme.
        """
        if action == "schedule":
            if not all([channel, time, timezone is not None]):
                embed = discord.Embed(
                    description="❌ To schedule, you must provide: channel, time (HH:MM), and timezone offset.",
                    color=0xE02B2B
                )
                await context.send(embed=embed)
                return

            # Validate time
            time_pattern = r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$'
            if not re.match(time_pattern, time):
                embed = discord.Embed(
                    description="❌ Invalid time format. Use HH:MM (24-hour).",
                    color=0xE02B2B
                )
                await context.send(embed=embed)
                return

            # Validate timezone
            if timezone < -12 or timezone > 14:
                embed = discord.Embed(
                    description="❌ Invalid timezone offset. Must be between -12 and +14.",
                    color=0xE02B2B
                )
                await context.send(embed=embed)
                return

            try:
                await self.bot.database.connection.execute(
                    """INSERT INTO creative_config (server_id, channel_id, post_time, timezone_offset)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(server_id) DO UPDATE SET
                       channel_id = excluded.channel_id,
                       post_time = excluded.post_time,
                       timezone_offset = excluded.timezone_offset""",
                    (context.guild.id, channel.id, time, timezone)
                )
                await self.bot.database.connection.commit()

                embed = discord.Embed(
                    title="✅ Creative Prompts Scheduled!",
                    description=(
                        f"Daily creative prompts will be posted in {channel.mention}\n"
                        f"**Time:** {time} (UTC{timezone:+d})\n"
                        f"**Rotation:** Writing → Music → Art"
                    ),
                    color=0x2ECC71
                )

                await context.send(embed=embed)
                self.bot.logger.info(f"Creative prompts scheduled for guild {context.guild.id}")

            except Exception as e:
                self.bot.logger.error(f"Error scheduling creative prompts: {e}")
                embed = discord.Embed(
                    description="❌ Failed to schedule. Please try again.",
                    color=0xE02B2B
                )
                await context.send(embed=embed)

        elif action == "theme":
            if not theme:
                embed = discord.Embed(
                    description="❌ Please provide a theme.",
                    color=0xE02B2B
                )
                await context.send(embed=embed)
                return

            try:
                await self.bot.database.connection.execute(
                    """INSERT INTO creative_config (server_id, channel_id, post_time, timezone_offset, current_month_theme)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(server_id) DO UPDATE SET current_month_theme = excluded.current_month_theme""",
                    (context.guild.id, 0, "00:00", 0, theme)
                )
                await self.bot.database.connection.commit()

                embed = discord.Embed(
                    title="✅ Monthly Theme Set!",
                    description=f"This month's creative theme: **{theme}**\n\nAll prompts will incorporate this theme.",
                    color=0x2ECC71
                )

                await context.send(embed=embed)

            except Exception as e:
                self.bot.logger.error(f"Error setting theme: {e}")
                embed = discord.Embed(
                    description="❌ Failed to set theme. Please try again.",
                    color=0xE02B2B
                )
                await context.send(embed=embed)

        elif action == "config":
            try:
                async with self.bot.database.connection.execute(
                    "SELECT channel_id, post_time, timezone_offset, daily_prompts_enabled, current_month_theme FROM creative_config WHERE server_id = ?",
                    (context.guild.id,)
                ) as cursor:
                    result = await cursor.fetchone()

                if not result:
                    embed = discord.Embed(
                        title="📋 Creative Studio Configuration",
                        description="Not configured yet.\n\nUse `/creative-admin schedule` to set up!",
                        color=0x3498DB
                    )
                    await context.send(embed=embed)
                    return

                channel_id, post_time, tz_offset, enabled, theme_val = result
                channel_obj = context.guild.get_channel(int(channel_id)) if channel_id else None
                channel_mention = channel_obj.mention if channel_obj else "Not set"

                embed = discord.Embed(
                    title="📋 Creative Studio Configuration",
                    color=0x3498DB
                )

                embed.add_field(
                    name="⚙️ Settings",
                    value=(
                        f"**Channel:** {channel_mention}\n"
                        f"**Time:** {post_time} (UTC{tz_offset:+d})\n"
                        f"**Daily Prompts:** {'✅ Enabled' if enabled else '❌ Disabled'}\n"
                        f"**Monthly Theme:** {theme_val or 'None set'}"
                    ),
                    inline=False
                )

                await context.send(embed=embed)

            except Exception as e:
                self.bot.logger.error(f"Error fetching config: {e}")
                embed = discord.Embed(
                    description="❌ Failed to fetch configuration.",
                    color=0xE02B2B
                )
                await context.send(embed=embed)

    @commands.hybrid_command(
        name="creative-help",
        description="Get help with creative studio commands",
    )
    async def creative_help(self, context: Context) -> None:
        """
        Show help information.

        :param context: The command context.
        """
        embed = discord.Embed(
            title="🎨 Creative Studio Help",
            description="A complete creative toolkit for writers, musicians, and artists!",
            color=0x9B59B6
        )

        embed.add_field(
            name="📝 /creative-prompt",
            value=(
                "Generate creative prompts\n"
                "**Types:** story, writing, song, chords, lyrics, theory, draw, style, palette, character\n"
                "**Usage:** `/creative-prompt type:story genre:fantasy theme:dragons`"
            ),
            inline=False
        )

        embed.add_field(
            name="📖 /creative-collab",
            value=(
                "Start a collaborative story\n"
                "**Usage:** `/creative-collab prompt:A mysterious door appears in the forest`\n"
                "**Tip:** Mention the bot in the thread to have AI continue the story!"
            ),
            inline=False
        )

        embed.add_field(
            name="🖼️ /creative-gallery",
            value=(
                "Manage your creative gallery\n"
                "**Actions:** submit, view, my-work\n"
                "**Usage:** `/creative-gallery action:submit work_type:art title:... description:...`"
            ),
            inline=False
        )

        embed.add_field(
            name="🏆 /creative-challenge",
            value=(
                "Participate in challenges\n"
                "**Actions:** view, submit\n"
                "**Usage:** `/creative-challenge action:submit challenge_id:1 submission:...`"
            ),
            inline=False
        )

        embed.add_field(
            name="⚙️ /creative-admin",
            value=(
                "Admin-only configuration\n"
                "**Actions:** schedule, theme, config\n"
                "**Usage:** `/creative-admin action:schedule channel:#prompts time:09:00 timezone:-5`"
            ),
            inline=False
        )

        embed.set_footer(text="Created with Claude AI | Use daily for inspiration!")

        await context.send(embed=embed)

    # ==================== BACKGROUND TASKS ====================

    @tasks.loop(minutes=15)
    async def check_daily_prompts(self):
        """Check if daily prompts should be posted."""
        try:
            async with self.bot.database.connection.execute(
                "SELECT server_id, channel_id, post_time, timezone_offset, last_daily_post, prompt_rotation FROM creative_config WHERE daily_prompts_enabled = 1"
            ) as cursor:
                configs = await cursor.fetchall()

            for server_id, channel_id, post_time, tz_offset, last_post, rotation in configs:
                utc_now = datetime.utcnow()
                server_time = utc_now + timedelta(hours=tz_offset)
                server_date = server_time.strftime("%Y-%m-%d")

                hour, minute = map(int, post_time.split(':'))
                time_diff = abs((server_time.hour * 60 + server_time.minute) - (hour * 60 + minute))

                if time_diff <= 60 and last_post != server_date:
                    guild = self.bot.get_guild(int(server_id))
                    if guild:
                        channel = guild.get_channel(int(channel_id))
                        if channel:
                            # Determine which type of prompt to post
                            next_rotation = {"writing": "music", "music": "art", "art": "writing"}.get(rotation or "writing", "writing")

                            await self.post_daily_prompt(guild, channel, rotation or "writing")

                            # Update rotation and last post date
                            await self.bot.database.connection.execute(
                                "UPDATE creative_config SET last_daily_post = ?, prompt_rotation = ? WHERE server_id = ?",
                                (server_date, next_rotation, server_id)
                            )
                            await self.bot.database.connection.commit()

        except Exception as e:
            self.bot.logger.error(f"Error in daily prompts task: {e}")

    @check_daily_prompts.before_loop
    async def before_check_daily_prompts(self):
        """Wait until bot is ready."""
        await self.bot.wait_until_ready()

    async def post_daily_prompt(self, guild: discord.Guild, channel: discord.TextChannel, prompt_type: str):
        """Post a daily creative prompt."""
        try:
            monthly_theme = await self.get_monthly_theme(guild.id)

            if prompt_type == "writing":
                prompt_text = await self.generate_story_prompt("random", monthly_theme)
                embed = discord.Embed(
                    title="✍️ Daily Writing Prompt",
                    description=prompt_text,
                    color=0x9B59B6
                )
                embed.set_footer(text="Use /creative-prompt for more prompts!")

            elif prompt_type == "music":
                prompt_data = await self.generate_song_prompt("random", monthly_theme)
                embed = discord.Embed(
                    title="🎵 Daily Songwriting Prompt",
                    color=0xE91E63
                )
                embed.add_field(name="Song Title", value=prompt_data["title"], inline=False)
                embed.add_field(name="Theme", value=prompt_data["theme"], inline=False)
                embed.add_field(name="Opening Line", value=f"*\"{prompt_data['opening']}\"*", inline=False)
                embed.set_footer(text="Use /creative-prompt for more ideas!")

            else:  # art
                prompt_text = await self.generate_draw_prompt("random", monthly_theme)
                embed = discord.Embed(
                    title="🎨 Daily Art Prompt",
                    description=prompt_text,
                    color=0xFF9800
                )
                embed.set_footer(text="Use /creative-prompt for more prompts!")

            if monthly_theme:
                embed.add_field(name="Monthly Theme", value=f"*{monthly_theme}*", inline=False)

            await channel.send(embed=embed)
            self.bot.logger.info(f"Posted daily {prompt_type} prompt to guild {guild.id}")

        except Exception as e:
            self.bot.logger.error(f"Error posting daily prompt: {e}")

    @tasks.loop(minutes=60)
    async def check_weekly_challenges(self):
        """Check if weekly challenges should be posted (Mondays)."""
        try:
            utc_now = datetime.utcnow()
            # Post on Mondays
            if utc_now.weekday() == 0:  # Monday
                async with self.bot.database.connection.execute(
                    "SELECT server_id, channel_id, timezone_offset, last_weekly_post FROM creative_config WHERE weekly_challenges_enabled = 1"
                ) as cursor:
                    configs = await cursor.fetchall()

                for server_id, channel_id, tz_offset, last_post in configs:
                    server_time = utc_now + timedelta(hours=tz_offset)
                    server_date = server_time.strftime("%Y-%m-%d")

                    # Only post once per week
                    if last_post != server_date:
                        guild = self.bot.get_guild(int(server_id))
                        if guild and channel_id:
                            channel = guild.get_channel(int(channel_id))
                            if channel:
                                await self.post_weekly_challenge(guild, channel)

                                await self.bot.database.connection.execute(
                                    "UPDATE creative_config SET last_weekly_post = ? WHERE server_id = ?",
                                    (server_date, server_id)
                                )
                                await self.bot.database.connection.commit()

        except Exception as e:
            self.bot.logger.error(f"Error in weekly challenges task: {e}")

    @check_weekly_challenges.before_loop
    async def before_check_weekly_challenges(self):
        """Wait until bot is ready."""
        await self.bot.wait_until_ready()

    async def post_weekly_challenge(self, guild: discord.Guild, channel: discord.TextChannel):
        """Post a weekly creative challenge."""
        try:
            # Randomly select challenge type
            challenge_type = random.choice(["writing", "music", "art"])
            monthly_theme = await self.get_monthly_theme(guild.id)

            if challenge_type == "writing":
                prompt_text = await self.generate_story_prompt("random", monthly_theme)
                title = "Weekly Writing Challenge"
                icon = "✍️"
            elif challenge_type == "music":
                prompt_data = await self.generate_song_prompt("random", monthly_theme)
                prompt_text = f"**Title:** {prompt_data['title']}\n**Theme:** {prompt_data['theme']}\n**Opening:** {prompt_data['opening']}"
                title = "Weekly Songwriting Challenge"
                icon = "🎵"
            else:
                prompt_text = await self.generate_draw_prompt("random", monthly_theme)
                title = "Weekly Art Challenge"
                icon = "🎨"

            # Calculate dates
            start_date = datetime.utcnow().strftime("%Y-%m-%d")
            end_date = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d")

            # Save challenge
            cursor = await self.bot.database.connection.execute(
                """INSERT INTO creative_challenges (server_id, challenge_type, prompt, start_date, end_date)
                   VALUES (?, ?, ?, ?, ?)""",
                (guild.id, challenge_type, prompt_text, start_date, end_date)
            )
            await self.bot.database.connection.commit()
            challenge_id = cursor.lastrowid

            # Post challenge
            embed = discord.Embed(
                title=f"{icon} {title}",
                description=prompt_text,
                color=0xFF6B6B
            )

            embed.add_field(name="Duration", value="7 days", inline=True)
            embed.add_field(name="Challenge ID", value=f"`{challenge_id}`", inline=True)
            embed.set_footer(text="Submit with /creative-challenge submit")

            await channel.send(embed=embed)
            self.bot.logger.info(f"Posted weekly {challenge_type} challenge to guild {guild.id}")

        except Exception as e:
            self.bot.logger.error(f"Error posting weekly challenge: {e}")

    # ==================== EVENT LISTENER (AI PARTICIPATION) ====================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for AI participation requests in collaborative threads."""
        # Ignore own messages
        if message.author == self.bot.user:
            return

        # Check if message is in a thread and mentions the bot
        if isinstance(message.channel, discord.Thread) and self.bot.user.mentioned_in(message):
            try:
                # Check if this is a collaborative work thread
                async with self.bot.database.connection.execute(
                    "SELECT id, work_type FROM collaborative_works WHERE thread_id = ? AND completed = 0",
                    (message.channel.id,)
                ) as cursor:
                    work = await cursor.fetchone()

                if work:
                    work_id, work_type = work

                    # Generate AI continuation
                    async with message.channel.typing():
                        continuation = await self.continue_story_with_ai(work_id)

                    if continuation:
                        # Post continuation
                        await message.channel.send(f"*[AI Contribution]*\n\n{continuation}")

                        # Save contribution
                        word_count = len(continuation.split())
                        async with self.bot.database.connection.execute(
                            "SELECT MAX(contribution_number) FROM work_contributions WHERE work_id = ?",
                            (work_id,)
                        ) as cursor:
                            max_contrib = await cursor.fetchone()
                            next_number = (max_contrib[0] or 0) + 1

                        await self.bot.database.connection.execute(
                            """INSERT INTO work_contributions (work_id, user_id, content, contribution_number, word_count)
                               VALUES (?, ?, ?, ?, ?)""",
                            (work_id, self.bot.user.id, continuation, next_number, word_count)
                        )

                        # Update contribution count
                        await self.bot.database.connection.execute(
                            "UPDATE collaborative_works SET contribution_count = contribution_count + 1 WHERE id = ?",
                            (work_id,)
                        )

                        await self.bot.database.connection.commit()

            except Exception as e:
                self.bot.logger.error(f"Error in AI participation: {e}")


async def setup(bot) -> None:
    await bot.add_cog(Creative(bot))
