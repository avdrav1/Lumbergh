"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.3.0
"""

import os
import re
import sys
from datetime import datetime, time, timedelta
from typing import Optional

import discord
from anthropic import AsyncAnthropic
from discord import app_commands
from discord.ext import commands, tasks
from discord.ext.commands import Context

# Import helpers
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import scheduling
from helpers.claude_cog import ClaudeAICog


class Affirmations(ClaudeAICog, name="affirmations"):
    def __init__(self, bot) -> None:
        super().__init__(bot, cog_name="Affirmations cog")

        # Start the background task
        self.daily_affirmation_task.start()

    def cog_unload(self) -> None:
        """Clean up when cog is unloaded."""
        self.daily_affirmation_task.cancel()

    # Theme definitions
    THEMES = {
        "motivation": "motivational and energizing, focused on taking action and achieving goals",
        "gratitude": "centered on gratitude, appreciation, and recognizing life's blessings",
        "confidence": "building self-confidence, self-worth, and inner strength",
        "mindfulness": "promoting mindfulness, presence, and inner peace",
        "success": "focused on success, abundance, and personal growth",
        "random": "any positive and uplifting theme"
    }

    # Fallback quotes for each theme
    FALLBACK_QUOTES = {
        "motivation": ("The only way to do great work is to love what you do.", "Steve Jobs"),
        "gratitude": ("Gratitude turns what we have into enough.", "Aesop"),
        "confidence": ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
        "mindfulness": ("The present moment is the only time over which we have dominion.", "Thích Nhất Hạnh"),
        "success": ("Success is not final, failure is not fatal: it is the courage to continue that counts.", "Winston Churchill"),
        "random": ("The best way to predict the future is to create it.", "Peter Drucker")
    }

    async def generate_affirmation(self, theme: str = "motivation") -> tuple:
        """
        Generate an affirmation and related quote using Claude AI.

        :param theme: The theme for the affirmation.
        :return: Tuple of (affirmation_text, quote_text, quote_author).
        """
        fallback_quote = self.FALLBACK_QUOTES.get(theme, self.FALLBACK_QUOTES["motivation"])

        if not self.client:
            return (
                "You are capable of amazing things today!",
                fallback_quote[0],
                fallback_quote[1]
            )

        theme_description = self.THEMES.get(theme, self.THEMES["motivation"])

        prompt = f"""Generate a powerful daily affirmation and a related inspirational quote that are {theme_description}.

Format your response EXACTLY like this:
AFFIRMATION: [one powerful sentence, 15-25 words, present tense, personal, no quotes]
QUOTE: [an inspirational quote from a famous person]
AUTHOR: [the person who said the quote]

Example:
AFFIRMATION: I embrace challenges as opportunities to grow and discover my true potential
QUOTE: The only impossible journey is the one you never begin
AUTHOR: Tony Robbins

Generate now:"""

        try:
            message = await self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )

            response = message.content[0].text.strip()

            # Parse the response
            affirmation = ""
            quote = ""
            author = ""

            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('AFFIRMATION:'):
                    affirmation = line.replace('AFFIRMATION:', '').strip().strip('"').strip("'")
                elif line.startswith('QUOTE:'):
                    quote = line.replace('QUOTE:', '').strip().strip('"').strip("'")
                elif line.startswith('AUTHOR:'):
                    author = line.replace('AUTHOR:', '').strip()

            # Validate we got all parts
            if not affirmation or not quote or not author:
                raise ValueError("Failed to parse AI response")

            return (affirmation, quote, author)

        except Exception as e:
            self.bot.logger.error(f"Error generating affirmation: {e}")
            return (
                "Today is filled with endless possibilities and opportunities for growth.",
                fallback_quote[0],
                fallback_quote[1]
            )

    @tasks.loop(minutes=15)
    async def daily_affirmation_task(self) -> None:
        """Background task that checks every 15 minutes for servers needing affirmations."""
        try:
            servers = await self.bot.database.get_servers_needing_affirmations()

            for server_data in servers:
                server_id, channel_id, post_time_str, tz_offset, theme, last_post_date = server_data

                # Parse the post time
                target_time = scheduling.parse_time_string(post_time_str)
                if not target_time:
                    continue

                # Check if already posted today
                if not scheduling.should_post_today(last_post_date, tz_offset):
                    continue

                # Check if within posting window
                if scheduling.should_post_now(target_time, tz_offset, window_minutes=15):
                    # Time to post!
                    await self.post_affirmation_to_server(
                        int(server_id), int(channel_id), theme
                    )
                    # Update last post date
                    current_date = scheduling.get_server_date(tz_offset)
                    await self.bot.database.update_last_post_date(
                        int(server_id), current_date
                    )

        except Exception as e:
            self.bot.logger.error(f"Error in daily affirmation task: {e}")

    @daily_affirmation_task.before_loop
    async def before_daily_affirmation_task(self) -> None:
        """Wait for bot to be ready before starting task."""
        await self.bot.wait_until_ready()

    async def post_affirmation_to_server(
        self, server_id: int, channel_id: int, theme: str
    ) -> bool:
        """Post an affirmation to a specific server channel."""
        try:
            guild = self.bot.get_guild(server_id)
            if not guild:
                self.bot.logger.warning(f"Could not find guild {server_id} for affirmations")
                return False

            channel = guild.get_channel(channel_id)
            if not channel:
                self.bot.logger.warning(
                    f"Could not find channel {channel_id} in guild {guild.name}"
                )
                return False

            # Generate affirmation and quote
            affirmation_text, quote_text, quote_author = await self.generate_affirmation(theme)

            # Create embed
            theme_emojis = {
                "motivation": "💪",
                "gratitude": "🙏",
                "confidence": "✨",
                "mindfulness": "🧘",
                "success": "🌟",
                "random": "💫"
            }

            theme_colors = {
                "motivation": 0xE74C3C,  # Red
                "gratitude": 0x2ECC71,   # Green
                "confidence": 0xF39C12,  # Orange
                "mindfulness": 0x3498DB, # Blue
                "success": 0x9B59B6,     # Purple
                "random": 0xBEBEFE      # Light purple
            }

            emoji = theme_emojis.get(theme, "💫")
            color = theme_colors.get(theme, 0xBEBEFE)

            # Build description with affirmation and quote
            description = f"*{affirmation_text}*\n\n"
            description += "━━━━━━━━━━━━━━━━━\n\n"
            description += f"💬 **Related Quote:**\n"
            description += f"*\"{quote_text}\"*\n"
            description += f"— {quote_author}"

            embed = discord.Embed(
                title=f"{emoji} Daily Affirmation",
                description=description,
                color=color,
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text=f"Theme: {theme.capitalize()} • Have a wonderful day!")

            await channel.send(embed=embed)
            self.bot.logger.info(
                f"Posted daily affirmation to {guild.name} (#{channel.name})"
            )
            return True

        except discord.Forbidden:
            self.bot.logger.warning(
                f"Missing permissions to post affirmation in channel {channel_id}"
            )
            return False
        except Exception as e:
            self.bot.logger.error(f"Error posting affirmation: {e}")
            return False

    @commands.hybrid_command(
        name="affirmation",
        description="Get an instant affirmation for yourself",
    )
    @app_commands.describe(
        theme="Choose a theme for your affirmation (optional)"
    )
    @app_commands.choices(theme=[
        app_commands.Choice(name="💪 Motivation", value="motivation"),
        app_commands.Choice(name="🙏 Gratitude", value="gratitude"),
        app_commands.Choice(name="✨ Confidence", value="confidence"),
        app_commands.Choice(name="🧘 Mindfulness", value="mindfulness"),
        app_commands.Choice(name="🌟 Success", value="success"),
        app_commands.Choice(name="💫 Random", value="random"),
    ])
    async def affirmation(self, ctx: Context, theme: str = "motivation") -> None:
        """
        Get an instant affirmation.

        :param ctx: The hybrid command context.
        :param theme: The theme for the affirmation.
        """
        # Defer for slash commands
        if ctx.interaction:
            await ctx.defer()

        if not self.client:
            embed = discord.Embed(
                title="Error",
                description="Affirmations are not configured. Please contact the bot owner.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        async with ctx.channel.typing():
            affirmation_text, quote_text, quote_author = await self.generate_affirmation(theme)

            theme_emojis = {
                "motivation": "💪",
                "gratitude": "🙏",
                "confidence": "✨",
                "mindfulness": "🧘",
                "success": "🌟",
                "random": "💫"
            }

            theme_colors = {
                "motivation": 0xE74C3C,
                "gratitude": 0x2ECC71,
                "confidence": 0xF39C12,
                "mindfulness": 0x3498DB,
                "success": 0x9B59B6,
                "random": 0xBEBEFE
            }

            emoji = theme_emojis.get(theme, "💫")
            color = theme_colors.get(theme, 0xBEBEFE)

            # Build description with affirmation and quote
            description = f"*{affirmation_text}*\n\n"
            description += "━━━━━━━━━━━━━━━━━\n\n"
            description += f"💬 **Related Quote:**\n"
            description += f"*\"{quote_text}\"*\n"
            description += f"— {quote_author}"

            embed = discord.Embed(
                title=f"{emoji} Your Affirmation",
                description=description,
                color=color,
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text=f"Theme: {theme.capitalize()} • Requested by {ctx.author.display_name}")

            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="affirmation-admin",
        description="Manage daily affirmations (Admin only)",
    )
    @app_commands.describe(
        action="Admin action to perform",
        channel="[setup] The channel where affirmations will be posted",
        time="[setup] Time to post (24-hour format, e.g., '09:00' or '14:30')",
        timezone="[setup] Timezone offset from UTC (e.g., -5 for EST, +1 for CET)",
        theme="[setup] Theme for affirmations",
        enabled="[toggle] Enable or disable daily affirmations"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Setup", value="setup"),
            app_commands.Choice(name="Toggle", value="toggle"),
            app_commands.Choice(name="Post Now", value="now"),
            app_commands.Choice(name="Status", value="status"),
        ],
        theme=[
            app_commands.Choice(name="💪 Motivation", value="motivation"),
            app_commands.Choice(name="🙏 Gratitude", value="gratitude"),
            app_commands.Choice(name="✨ Confidence", value="confidence"),
            app_commands.Choice(name="🧘 Mindfulness", value="mindfulness"),
            app_commands.Choice(name="🌟 Success", value="success"),
            app_commands.Choice(name="💫 Random", value="random"),
        ]
    )
    @commands.has_permissions(administrator=True)
    async def affirmation_admin(
        self,
        ctx: Context,
        action: str,
        channel: Optional[discord.TextChannel] = None,
        time: Optional[str] = None,
        timezone: Optional[int] = None,
        theme: Optional[str] = None,
        enabled: Optional[bool] = None
    ) -> None:
        """
        Manage daily affirmations for this server.

        :param ctx: The hybrid command context.
        :param action: The admin action to perform (setup, toggle, now, status).
        :param channel: Channel for setup action.
        :param time: Post time for setup action.
        :param timezone: Timezone offset for setup action.
        :param theme: Theme for setup action.
        :param enabled: Enable/disable for toggle action.
        """
        # Defer for slash commands
        if ctx.interaction:
            await ctx.defer()

        # Route to appropriate private method based on action
        if action == "setup":
            await self._admin_setup(ctx, channel, time, timezone, theme)
        elif action == "toggle":
            await self._admin_toggle(ctx, enabled)
        elif action == "now":
            await self._admin_now(ctx)
        elif action == "status":
            await self._admin_status(ctx)
        else:
            embed = discord.Embed(
                title="Invalid Action",
                description="Please choose a valid action: setup, toggle, now, or status",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)

    async def _admin_setup(
        self,
        ctx: Context,
        channel: Optional[discord.TextChannel],
        time: Optional[str],
        timezone: Optional[int],
        theme: Optional[str]
    ) -> None:
        """
        Configure daily affirmations for this server.

        :param ctx: The hybrid command context.
        :param channel: The channel to post affirmations to.
        :param time: Time in 24-hour format (HH:MM).
        :param timezone: Timezone offset from UTC (-12 to +14).
        :param theme: The theme for affirmations.
        """
        # Validate required parameters
        if not channel or not time or timezone is None:
            embed = discord.Embed(
                title="Missing Parameters",
                description="Setup requires: channel, time, and timezone parameters.\n\nExample: `/affirmation-admin action:setup channel:#general time:09:00 timezone:-5 theme:motivation`",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        # Validate time format
        parsed_time = scheduling.parse_time_string(time)
        if not parsed_time:
            embed = discord.Embed(
                title="Invalid Time Format",
                description="Please use 24-hour format like `09:00` or `14:30`",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        # Validate timezone
        if timezone < -12 or timezone > 14:
            embed = discord.Embed(
                title="Invalid Timezone",
                description="Timezone offset must be between -12 and +14",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        # Validate theme
        if not theme or theme not in self.THEMES:
            theme = "motivation"

        # Save configuration
        await self.bot.database.set_affirmation_config(
            ctx.guild.id, channel.id, time, timezone, theme
        )

        # Create confirmation embed
        embed = discord.Embed(
            title="✅ Daily Affirmations Configured",
            description=f"Daily affirmations are now set up for this server!",
            color=0x2ECC71,
        )
        embed.add_field(name="📍 Channel", value=channel.mention, inline=True)
        embed.add_field(name="⏰ Time", value=f"`{time}` (UTC{timezone:+d})", inline=True)
        embed.add_field(name="🎨 Theme", value=theme.capitalize(), inline=True)
        embed.add_field(
            name="Status",
            value="Enabled - affirmations will start posting tomorrow",
            inline=False
        )
        embed.set_footer(text="Use /affirmation-admin action:toggle to enable/disable • action:now to test")

        await ctx.send(embed=embed)
        self.bot.logger.info(
            f"{ctx.author} configured affirmations for {ctx.guild.name}"
        )

    async def _admin_toggle(self, ctx: Context, enabled: Optional[bool]) -> None:
        """
        Enable or disable daily affirmations.

        :param ctx: The hybrid command context.
        :param enabled: True to enable, False to disable.
        """
        if enabled is None:
            embed = discord.Embed(
                title="Missing Parameter",
                description="Toggle requires the `enabled` parameter.\n\nExample: `/affirmation-admin action:toggle enabled:True`",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        # Check if config exists
        config = await self.bot.database.get_affirmation_config(ctx.guild.id)
        if not config:
            embed = discord.Embed(
                title="Not Configured",
                description="Daily affirmations haven't been set up yet. Use `/affirmation-admin action:setup` first.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        # Toggle
        success = await self.bot.database.toggle_affirmations(ctx.guild.id, enabled)

        if success:
            status = "enabled" if enabled else "disabled"
            emoji = "✅" if enabled else "❌"
            color = 0x2ECC71 if enabled else 0xE02B2B

            embed = discord.Embed(
                title=f"{emoji} Daily Affirmations {status.capitalize()}",
                description=f"Daily affirmations have been **{status}** for this server.",
                color=color,
            )
            await ctx.send(embed=embed)
            self.bot.logger.info(
                f"{ctx.author} {status} affirmations for {ctx.guild.name}"
            )
        else:
            embed = discord.Embed(
                title="Error",
                description="Could not update affirmation settings.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)

    async def _admin_now(self, ctx: Context) -> None:
        """
        Immediately post an affirmation to the configured channel.

        :param ctx: The hybrid command context.
        """
        # Get config
        config = await self.bot.database.get_affirmation_config(ctx.guild.id)
        if not config:
            embed = discord.Embed(
                title="Not Configured",
                description="Daily affirmations haven't been set up yet. Use `/affirmation-admin action:setup` first.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        if not config["enabled"]:
            embed = discord.Embed(
                title="Disabled",
                description="Daily affirmations are currently disabled. Use `/affirmation-admin action:toggle` to enable them.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        # Post affirmation
        success = await self.post_affirmation_to_server(
            ctx.guild.id, config["channel_id"], config["theme"]
        )

        if success:
            embed = discord.Embed(
                title="✅ Affirmation Posted",
                description=f"An affirmation has been posted to <#{config['channel_id']}>",
                color=0x2ECC71,
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error",
                description="Could not post affirmation. Check bot permissions and channel configuration.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)

    async def _admin_status(self, ctx: Context) -> None:
        """
        View the current affirmation configuration for this server.

        :param ctx: The hybrid command context.
        """
        config = await self.bot.database.get_affirmation_config(ctx.guild.id)

        if not config:
            embed = discord.Embed(
                title="📊 Affirmation Status",
                description="Daily affirmations have not been configured for this server yet.\n\nAdmins can use `/affirmation-admin action:setup` to get started!",
                color=0x3498DB,
            )
            await ctx.send(embed=embed)
            return

        status_emoji = "✅" if config["enabled"] else "❌"
        status_text = "Enabled" if config["enabled"] else "Disabled"
        color = 0x2ECC71 if config["enabled"] else 0xE02B2B

        embed = discord.Embed(
            title=f"📊 Daily Affirmation Status",
            description=f"Configuration for {ctx.guild.name}",
            color=color,
        )
        embed.add_field(
            name="Status",
            value=f"{status_emoji} {status_text}",
            inline=True
        )
        embed.add_field(
            name="Channel",
            value=f"<#{config['channel_id']}>",
            inline=True
        )
        embed.add_field(
            name="Theme",
            value=config["theme"].capitalize(),
            inline=True
        )
        embed.add_field(
            name="Post Time",
            value=f"`{config['post_time']}` (UTC{config['timezone_offset']:+d})",
            inline=True
        )
        embed.add_field(
            name="Last Posted",
            value=config["last_post_date"] or "Never",
            inline=True
        )

        embed.set_footer(text="Use /affirmation-admin action:setup to reconfigure • action:toggle to enable/disable")

        await ctx.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(Affirmations(bot))
