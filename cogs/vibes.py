"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized discord bot in Python programming language.

Version: 6.3.0
"""

import os
import re
import sys
import traceback
from datetime import datetime, timedelta, time as dt_time
from typing import Optional, Tuple

import discord
from anthropic import AsyncAnthropic
from discord import app_commands
from discord.ext import commands, tasks
from discord.ext.commands import Context

# Import helpers
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import scheduling
from helpers.claude_cog import ClaudeAICog


class Vibes(ClaudeAICog, name="vibes"):
    """Community vibes features: Memory Bank and Question of the Day."""

    def __init__(self, bot) -> None:
        super().__init__(bot, cog_name="Vibes cog")

        # Start background tasks
        self.bot.logger.info("Starting QOTD background task...")
        self.qotd_task.start()
        self.qotd_task.add_exception_type(Exception)
        self.qotd_task.error(self.qotd_task_error)

        self.bot.logger.info("Starting Throwback background task...")
        self.throwback_task.start()
        self.throwback_task.add_exception_type(Exception)
        self.throwback_task.error(self.throwback_task_error)

    def cog_unload(self) -> None:
        """Clean up when cog is unloaded."""
        self.qotd_task.cancel()
        self.throwback_task.cancel()

    # ===== UTILITY METHODS =====

    async def get_message_context(
        self, channel: discord.TextChannel, message: discord.Message, limit: int = 2
    ) -> tuple:
        """
        Get messages before and after a message for context.

        :param channel: The channel.
        :param message: The target message.
        :param limit: Number of messages to get before/after.
        :return: Tuple of (context_before, context_after) as strings.
        """
        try:
            # Get messages before
            before_messages = []
            async for msg in channel.history(limit=limit, before=message):
                before_messages.insert(0, f"{msg.author.display_name}: {msg.content[:100]}")

            # Get messages after
            after_messages = []
            async for msg in channel.history(limit=limit, after=message, oldest_first=True):
                after_messages.append(f"{msg.author.display_name}: {msg.content[:100]}")

            context_before = "\n".join(before_messages) if before_messages else None
            context_after = "\n".join(after_messages) if after_messages else None

            return (context_before, context_after)
        except Exception as e:
            self.bot.logger.error(f"Error getting message context: {e}")
            return (None, None)

    async def get_server_memory_emoji(self, server_id: int) -> str:
        """Get the configured memory emoji for a server, or default."""
        config = await self.bot.database.get_vibes_config(server_id)
        if config:
            return config["memory_emoji"]
        return "💾"  # Default fallback

    # ===== CONSOLIDATED MEMORY COMMAND =====

    @commands.hybrid_command(
        name="vibes-memory",
        description="Memory Bank operations: save, view, stats",
    )
    @app_commands.describe(
        action="What to do with memories",
        message_id="Message ID to save (for 'save' action)",
        filter_type="How to filter memories (for 'view' action)",
        value="Filter value: username for 'from', keyword for 'search'",
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Save a memory", value="save"),
        app_commands.Choice(name="View memories", value="view"),
        app_commands.Choice(name="Memory statistics", value="stats"),
    ])
    @app_commands.choices(filter_type=[
        app_commands.Choice(name="All memories", value="all"),
        app_commands.Choice(name="Random memory", value="random"),
        app_commands.Choice(name="From specific user", value="from"),
        app_commands.Choice(name="Search keyword", value="search"),
    ])
    async def vibes_memory(
        self,
        ctx: Context,
        action: str,
        message_id: str = None,
        filter_type: str = "all",
        value: str = None,
    ) -> None:
        """
        Memory Bank operations: save, view, or get stats.

        :param ctx: The hybrid command context.
        :param action: The action to perform (save/view/stats).
        :param message_id: Message ID to save (for save action).
        :param filter_type: Type of filter to apply (for view action).
        :param value: Filter value (for view action).
        """
        if ctx.interaction:
            await ctx.defer()

        if action == "save":
            await self._memory_save(ctx, message_id)
        elif action == "view":
            await self._memory_view(ctx, filter_type, value)
        elif action == "stats":
            await self._memory_stats(ctx)

    async def _memory_save(self, ctx: Context, message_id: str) -> None:
        """Save a message as a memory."""
        if not message_id:
            embed = discord.Embed(
                description="❌ Please provide a message ID. Example: `/vibes-memory save message_id:123456789`",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        try:
            # Get the message
            msg_id = int(message_id)
            message = await ctx.channel.fetch_message(msg_id)

            if not message.content:
                embed = discord.Embed(
                    description="❌ This message has no text content to save.",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed)
                return

            # Get context
            context_before, context_after = await self.get_message_context(
                ctx.channel, message
            )

            # Count reactions
            reactions_count = sum(reaction.count for reaction in message.reactions)

            # Save to database
            success = await self.bot.database.save_memory(
                server_id=ctx.guild.id,
                message_id=message.id,
                channel_id=message.channel.id,
                author_id=message.author.id,
                saved_by_id=ctx.author.id,
                content=message.content,
                context_before=context_before,
                context_after=context_after,
                save_reason="manual",
                reactions_count=reactions_count,
            )

            if success:
                memory_emoji = await self.get_server_memory_emoji(ctx.guild.id)
                embed = discord.Embed(
                    title=f"{memory_emoji} Memory Saved!",
                    description=f"Saved message from {message.author.mention}",
                    color=0x2ECC71,
                )
                embed.add_field(
                    name="Preview",
                    value=message.content[:200] + ("..." if len(message.content) > 200 else ""),
                    inline=False,
                )
                embed.set_footer(text=f"Saved by {ctx.author.display_name}")

                # Try to react to the original message
                try:
                    await message.add_reaction(memory_emoji)
                except:
                    pass
            else:
                embed = discord.Embed(
                    description="⚠️ This message is already saved as a memory!",
                    color=0xE67E22,
                )

            await ctx.send(embed=embed)

        except discord.NotFound:
            embed = discord.Embed(
                description="❌ Message not found. Make sure you're using the correct message ID from this channel.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
        except ValueError:
            embed = discord.Embed(
                description="❌ Invalid message ID format.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
        except Exception as e:
            self.bot.logger.error(f"Error saving memory: {e}")
            embed = discord.Embed(
                description="❌ An error occurred while saving the memory.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)

    async def _memory_view(self, ctx: Context, filter_type: str, value: str) -> None:
        """Browse saved memories with optional filtering."""
        try:
            if filter_type == "random":
                # Get random memory
                memory = await self.bot.database.get_random_memory(ctx.guild.id)
                if not memory:
                    embed = discord.Embed(
                        description="📭 No memories saved yet! Use `/vibes-memory save` to save your first memory.",
                        color=0x3498DB,
                    )
                    await ctx.send(embed=embed)
                    return

                # Display the random memory
                author = await self.bot.fetch_user(int(memory["author_id"]))
                embed = discord.Embed(
                    title="🎲 Random Memory",
                    description=memory["content"],
                    color=0xBEBEFE,
                    timestamp=datetime.fromisoformat(memory["created_at"]),
                )
                embed.set_author(
                    name=author.display_name if author else "Unknown User",
                    icon_url=author.avatar.url if author and author.avatar else None,
                )
                embed.add_field(
                    name="Reactions",
                    value=f"❤️ {memory['reactions_count']}",
                    inline=True,
                )
                if memory["category"]:
                    embed.add_field(
                        name="Category", value=memory["category"], inline=True
                    )
                embed.set_footer(text=f"Memory #{memory['id']}")

                await ctx.send(embed=embed)

            elif filter_type == "from":
                if not value:
                    embed = discord.Embed(
                        description="❌ Please provide a username to filter by.",
                        color=0xE02B2B,
                    )
                    await ctx.send(embed=embed)
                    return

                # Try to find the user (simple search by username)
                member = discord.utils.find(
                    lambda m: value.lower() in m.display_name.lower(), ctx.guild.members
                )
                if not member:
                    embed = discord.Embed(
                        description=f"❌ Couldn't find a user matching '{value}'.",
                        color=0xE02B2B,
                    )
                    await ctx.send(embed=embed)
                    return

                memories = await self.bot.database.get_memories(
                    ctx.guild.id, limit=10, author_id=member.id
                )

                if not memories:
                    embed = discord.Embed(
                        description=f"📭 No memories found from {member.mention}.",
                        color=0x3498DB,
                    )
                    await ctx.send(embed=embed)
                    return

                # Display list of memories
                embed = discord.Embed(
                    title=f"💬 Memories from {member.display_name}",
                    description=f"Found {len(memories)} memories",
                    color=0xBEBEFE,
                )

                for memory in memories[:5]:  # Show first 5
                    preview = memory["content"][:100] + (
                        "..." if len(memory["content"]) > 100 else ""
                    )
                    embed.add_field(
                        name=f"Memory #{memory['id']} • ❤️ {memory['reactions_count']}",
                        value=preview,
                        inline=False,
                    )

                embed.set_footer(text=f"Showing {min(5, len(memories))} of {len(memories)} memories")
                await ctx.send(embed=embed)

            elif filter_type == "search":
                if not value:
                    embed = discord.Embed(
                        description="❌ Please provide a keyword to search for.",
                        color=0xE02B2B,
                    )
                    await ctx.send(embed=embed)
                    return

                memories = await self.bot.database.get_memories(
                    ctx.guild.id, limit=10, search_query=value
                )

                if not memories:
                    embed = discord.Embed(
                        description=f"📭 No memories found matching '{value}'.",
                        color=0x3498DB,
                    )
                    await ctx.send(embed=embed)
                    return

                # Display search results
                embed = discord.Embed(
                    title=f"🔍 Search Results for '{value}'",
                    description=f"Found {len(memories)} memories",
                    color=0xBEBEFE,
                )

                for memory in memories[:5]:
                    preview = memory["content"][:100] + (
                        "..." if len(memory["content"]) > 100 else ""
                    )
                    embed.add_field(
                        name=f"Memory #{memory['id']} • ❤️ {memory['reactions_count']}",
                        value=preview,
                        inline=False,
                    )

                embed.set_footer(text=f"Showing {min(5, len(memories))} of {len(memories)} memories")
                await ctx.send(embed=embed)

            else:  # "all"
                memories = await self.bot.database.get_memories(ctx.guild.id, limit=10)

                if not memories:
                    embed = discord.Embed(
                        description="📭 No memories saved yet! Use `/vibes-memory save` to save your first memory.",
                        color=0x3498DB,
                    )
                    await ctx.send(embed=embed)
                    return

                # Display list of all memories
                embed = discord.Embed(
                    title="💾 Memory Bank",
                    description=f"Recent memories from this server",
                    color=0xBEBEFE,
                )

                for memory in memories[:5]:
                    preview = memory["content"][:100] + (
                        "..." if len(memory["content"]) > 100 else ""
                    )
                    try:
                        author = await self.bot.fetch_user(int(memory["author_id"]))
                        author_name = author.display_name if author else "Unknown"
                    except:
                        author_name = "Unknown"

                    embed.add_field(
                        name=f"Memory #{memory['id']} • by {author_name} • ❤️ {memory['reactions_count']}",
                        value=preview,
                        inline=False,
                    )

                embed.set_footer(text=f"Showing {min(5, len(memories))} of {len(memories)} memories")
                await ctx.send(embed=embed)

        except Exception as e:
            self.bot.logger.error(f"Error browsing memories: {e}")
            embed = discord.Embed(
                description="❌ An error occurred while browsing memories.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)

    async def _memory_stats(self, ctx: Context) -> None:
        """Display memory statistics for the server."""
        try:
            stats = await self.bot.database.get_memory_stats(ctx.guild.id)

            if stats["total_memories"] == 0:
                embed = discord.Embed(
                    description="📭 No memories saved yet! Use `/vibes-memory save` to save your first memory.",
                    color=0x3498DB,
                )
                await ctx.send(embed=embed)
                return

            embed = discord.Embed(
                title="📊 Memory Bank Statistics",
                description=f"Stats for {ctx.guild.name}",
                color=0xBEBEFE,
            )

            embed.add_field(
                name="Total Memories", value=str(stats["total_memories"]), inline=True
            )

            if stats["top_saver"]:
                try:
                    user = await self.bot.fetch_user(int(stats["top_saver"]["user_id"]))
                    embed.add_field(
                        name="Top Memory Saver",
                        value=f"{user.mention} ({stats['top_saver']['count']} saves)",
                        inline=True,
                    )
                except:
                    embed.add_field(
                        name="Top Memory Saver",
                        value=f"{stats['top_saver']['count']} saves",
                        inline=True,
                    )

            if stats["most_quoted"]:
                try:
                    user = await self.bot.fetch_user(int(stats["most_quoted"]["user_id"]))
                    embed.add_field(
                        name="Most Quoted Person",
                        value=f"{user.mention} ({stats['most_quoted']['count']} memories)",
                        inline=True,
                    )
                except:
                    embed.add_field(
                        name="Most Quoted Person",
                        value=f"{stats['most_quoted']['count']} memories",
                        inline=True,
                    )

            if stats["categories"]:
                categories_text = "\n".join(
                    [f"• {cat['category']}: {cat['count']}" for cat in stats["categories"][:5]]
                )
                embed.add_field(
                    name="Top Categories", value=categories_text, inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            self.bot.logger.error(f"Error getting memory stats: {e}")
            embed = discord.Embed(
                description="❌ An error occurred while getting statistics.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)

    # ===== MEMORY REACTION LISTENER =====

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Listen for memory emoji reactions to save messages."""
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return

        try:
            # Get guild to check emoji
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return

            # Get configured memory emoji
            memory_emoji = await self.get_server_memory_emoji(guild.id)

            # Check if this is the memory emoji
            # Handle both unicode and custom emojis
            emoji_str = str(payload.emoji)
            if emoji_str != memory_emoji and payload.emoji.name != memory_emoji.strip(":"):
                return

            # Get the message
            channel = self.bot.get_channel(payload.channel_id)
            if not channel:
                return

            message = await channel.fetch_message(payload.message_id)
            if not message.content:
                return

            # Get context
            context_before, context_after = await self.get_message_context(
                channel, message
            )

            # Count reactions
            reactions_count = sum(reaction.count for reaction in message.reactions)

            # Save to database
            await self.bot.database.save_memory(
                server_id=guild.id,
                message_id=message.id,
                channel_id=message.channel.id,
                author_id=message.author.id,
                saved_by_id=payload.user_id,
                content=message.content,
                context_before=context_before,
                context_after=context_after,
                save_reason="reaction",
                reactions_count=reactions_count,
            )

            self.bot.logger.info(
                f"Memory saved via reaction in {guild.name}: Message {message.id}"
            )

        except Exception as e:
            self.bot.logger.error(f"Error handling memory reaction: {e}")

    # ===== QOTD AI GENERATION =====

    async def generate_qotd(self, category: str = "random") -> str:
        """
        Generate a Question of the Day using Claude AI.

        :param category: The category of question to generate.
        :return: The generated question text.
        """
        if not self.client:
            # Fallback questions if no AI
            fallbacks = {
                "creative": "If you could create anything without limitations, what would it be?",
                "deep": "What's a belief you held strongly that you've since changed your mind about?",
                "silly": "If you could only eat one food for the rest of your life, but it would taste different every time, what would it be?",
                "random": "What's something you're looking forward to this week?",
            }
            return fallbacks.get(category, fallbacks["random"])

        category_descriptions = {
            "creative": "creative and thought-provoking, related to art, imagination, or innovation",
            "deep": "deep and philosophical, encouraging meaningful reflection",
            "silly": "fun and lighthearted, playful and entertaining",
            "random": "engaging and interesting, on any topic",
        }

        description = category_descriptions.get(category, category_descriptions["random"])

        prompt = f"""Generate a single engaging question that is {description}.

Requirements:
- Should be open-ended (not yes/no)
- Encourage discussion and sharing
- Be wholesome and inclusive
- 10-25 words long
- Don't use quotation marks

Just provide the question, nothing else."""

        try:
            message = await self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
            )

            question = message.content[0].text.strip().strip('"').strip("'")
            return question

        except Exception as e:
            self.bot.logger.error(f"Error generating QOTD with Claude: {e}")
            return "What's something that made you smile recently?"

    async def post_qotd_to_server(self, server_id: int, channel_id: int) -> Tuple[bool, str]:
        """
        Post a Question of the Day to a server channel.

        :param server_id: The server ID.
        :param channel_id: The channel ID.
        :return: Tuple of (success, error_message). error_message is empty if successful.
        """
        try:
            # Step 1: Get the channel
            self.bot.logger.info(f"Looking up channel ID: {channel_id} (type: {type(channel_id)})")

            # Try cache first (fast)
            channel = self.bot.get_channel(channel_id)

            if not channel:
                # Cache miss - try fetching from API (slower but more reliable)
                self.bot.logger.info(f"Channel {channel_id} not in cache, fetching from API...")
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                    self.bot.logger.info(f"Successfully fetched channel: #{channel.name}")
                except discord.NotFound:
                    error = f"Channel ID {channel_id} not found. It may have been deleted."
                    self.bot.logger.warning(f"QOTD Error: {error}")
                    return (False, error)
                except discord.Forbidden:
                    error = f"Bot cannot access channel ID {channel_id}. Missing 'View Channel' permission."
                    self.bot.logger.warning(f"QOTD Error: {error}")
                    return (False, error)
                except Exception as e:
                    error = f"Failed to fetch channel {channel_id}: {str(e)}"
                    self.bot.logger.error(f"QOTD Error: {error}")
                    return (False, error)
            else:
                self.bot.logger.info(f"Found channel in cache: #{channel.name}")

            # Step 2: Check bot permissions
            permissions = channel.permissions_for(channel.guild.me)
            if not permissions.send_messages:
                error = f"Missing 'Send Messages' permission in {channel.mention}"
                self.bot.logger.warning(f"QOTD Error: {error}")
                return (False, error)

            if not permissions.add_reactions:
                error = f"Missing 'Add Reactions' permission in {channel.mention}"
                self.bot.logger.warning(f"QOTD Error: {error}")
                return (False, error)

            # Step 3: Get or generate a question
            self.bot.logger.info(f"Fetching QOTD question for server {server_id}")
            question_data = await self.bot.database.get_next_qotd_question(server_id)

            if not question_data:
                self.bot.logger.info("No questions in pool, generating new ones...")
                # Generate new questions and add to pool
                try:
                    for category in ["creative", "deep", "silly", "random"]:
                        question_text = await self.generate_qotd(category)
                        self.bot.logger.debug(f"Generated {category} question: {question_text}")
                        await self.bot.database.add_qotd_question(
                            question=question_text, category=category
                        )
                except Exception as gen_error:
                    error = f"Failed to generate questions: {str(gen_error)}"
                    self.bot.logger.error(f"QOTD Error: {error}")
                    self.bot.logger.error(traceback.format_exc())
                    return (False, error)

                # Try again
                question_data = await self.bot.database.get_next_qotd_question(server_id)

            if not question_data:
                error = "Failed to get question even after generation. Check database connection."
                self.bot.logger.error(f"QOTD Error: {error}")
                return (False, error)

            self.bot.logger.info(f"Using question: {question_data['question'][:50]}...")

            # Step 4: Create embed
            category_emojis = {
                "creative": "🎨",
                "deep": "💭",
                "silly": "🎲",
                "random": "💬",
            }

            category_colors = {
                "creative": 0xE67E22,
                "deep": 0x3498DB,
                "silly": 0xF1C40F,
                "random": 0xBEBEFE,
            }

            emoji = category_emojis.get(question_data["category"], "💬")
            color = category_colors.get(question_data["category"], 0xBEBEFE)

            embed = discord.Embed(
                title=f"{emoji} Question of the Day",
                description=question_data["question"],
                color=color,
                timestamp=datetime.utcnow(),
            )
            embed.set_footer(
                text=f"Category: {question_data['category'].capitalize()} • Share your thoughts below!"
            )

            # Step 5: Send message
            try:
                message = await channel.send(embed=embed)
                self.bot.logger.info(f"Successfully posted QOTD embed to {channel.name}")
            except discord.Forbidden as e:
                error = f"Permission denied when posting to {channel.mention}: {str(e)}"
                self.bot.logger.error(f"QOTD Error: {error}")
                return (False, error)
            except Exception as e:
                error = f"Failed to send message: {str(e)}"
                self.bot.logger.error(f"QOTD Error: {error}")
                self.bot.logger.error(traceback.format_exc())
                return (False, error)

            # Step 6: Add reaction options
            try:
                await message.add_reaction("💬")  # Comment reaction
                await message.add_reaction("❤️")  # Love it
            except discord.Forbidden:
                self.bot.logger.warning("Could not add reactions - missing Add Reactions permission")
                # Not a critical error, continue anyway
            except Exception as e:
                self.bot.logger.warning(f"Could not add reactions: {e}")
                # Not a critical error, continue anyway

            # Step 7: Mark question as asked
            try:
                today = datetime.utcnow().strftime("%Y-%m-%d")
                await self.bot.database.mark_question_asked(question_data["id"], today)
            except Exception as e:
                self.bot.logger.warning(f"Could not mark question as asked: {e}")
                # Not critical, the question was posted successfully

            self.bot.logger.info(f"Successfully posted QOTD to {channel.guild.name}")
            return (True, "")

        except Exception as e:
            error = f"Unexpected error: {str(e)}"
            self.bot.logger.error(f"QOTD Error: {error}")
            self.bot.logger.error(traceback.format_exc())
            return (False, error)

    @tasks.loop(minutes=15)
    async def qotd_task(self) -> None:
        """Background task that checks every 15 minutes for servers needing QOTD posts."""
        try:
            self.bot.logger.info("QOTD task running - checking for servers needing posts...")
            servers = await self.bot.database.get_servers_needing_qotd()
            self.bot.logger.info(f"Found {len(servers)} server(s) with QOTD configured")

            for server_data in servers:
                server_id, channel_id, post_time_str, tz_offset, last_post_date = server_data

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
                    self.bot.logger.info(
                        f"Posting QOTD to server {server_id} at {post_time_str}"
                    )
                    success, error_msg = await self.post_qotd_to_server(int(server_id), int(channel_id))

                    if success:
                        # Update last post date
                        current_date = scheduling.get_server_date(tz_offset)
                        await self.bot.database.update_qotd_last_post(
                            int(server_id), current_date
                        )
                    else:
                        self.bot.logger.error(f"Failed to post scheduled QOTD to server {server_id}: {error_msg}")

        except Exception as e:
            self.bot.logger.error(f"Error in QOTD task: {e}")
            self.bot.logger.error(traceback.format_exc())

    @qotd_task.before_loop
    async def before_qotd_task(self) -> None:
        """Wait for bot to be ready before starting task."""
        self.bot.logger.info("QOTD task waiting for bot to be ready...")
        await self.bot.wait_until_ready()
        self.bot.logger.info("Bot ready! QOTD task will start running every 15 minutes.")

    @tasks.loop(hours=24)
    async def throwback_task(self) -> None:
        """Post random memory throwbacks."""
        try:
            self.bot.logger.info("Throwback task running...")
            # Get all guilds with throwback enabled
            # For now, we'll just check if vibes_config exists and throwback is enabled
            # This would need a proper query method, but for simplicity:
            for guild in self.bot.guilds:
                config = await self.bot.database.get_vibes_config(guild.id)
                if not config or not config["throwback_enabled"]:
                    continue

                # Get a random old memory (at least 30 days old)
                memory = await self.bot.database.get_random_memory(guild.id)
                if not memory:
                    continue

                # Check if memory is old enough (at least 30 days)
                created_at = datetime.fromisoformat(memory["created_at"])
                age_days = (datetime.utcnow() - created_at).days
                if age_days < 30:
                    continue

                # Find a general/main channel to post in
                # This is a simple heuristic - post in first text channel bot can access
                channel = None
                for ch in guild.text_channels:
                    if ch.permissions_for(guild.me).send_messages:
                        channel = ch
                        break

                if not channel:
                    continue

                # Create throwback embed
                try:
                    author = await self.bot.fetch_user(int(memory["author_id"]))
                    author_name = author.display_name if author else "Unknown User"
                    author_avatar = author.avatar.url if author and author.avatar else None
                except:
                    author_name = "Unknown User"
                    author_avatar = None

                embed = discord.Embed(
                    title="🎭 Memory Lane",
                    description=memory["content"],
                    color=0x9B59B6,
                    timestamp=created_at,
                )
                embed.set_author(name=author_name, icon_url=author_avatar)
                embed.set_footer(
                    text=f"From {age_days} days ago • Memory #{memory['id']}"
                )

                await channel.send(embed=embed)
                self.bot.logger.info(f"Posted throwback memory to {guild.name}")

        except Exception as e:
            self.bot.logger.error(f"Error in throwback task: {e}")
            self.bot.logger.error(traceback.format_exc())

    @throwback_task.before_loop
    async def before_throwback_task(self) -> None:
        """Wait for bot to be ready before starting task."""
        self.bot.logger.info("Throwback task waiting for bot to be ready...")
        await self.bot.wait_until_ready()
        self.bot.logger.info("Bot ready! Throwback task will run daily.")

    async def qotd_task_error(self, error: Exception) -> None:
        """Handle errors in QOTD task."""
        self.bot.logger.error(f"QOTD task crashed with error: {error}")
        self.bot.logger.error(traceback.format_exc())

    async def throwback_task_error(self, error: Exception) -> None:
        """Handle errors in throwback task."""
        self.bot.logger.error(f"Throwback task crashed with error: {error}")
        self.bot.logger.error(traceback.format_exc())

    # ===== CONSOLIDATED QOTD COMMAND =====

    @commands.hybrid_command(
        name="vibes-qotd",
        description="Question of the Day operations",
    )
    @app_commands.describe(
        action="What to do with QOTD",
        question="Your question (for 'suggest' action)",
        category="Category for question (for 'suggest' action)",
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Get current QOTD", value="get"),
        app_commands.Choice(name="Post QOTD now (admin)", value="now"),
        app_commands.Choice(name="Suggest a question", value="suggest"),
    ])
    @app_commands.choices(category=[
        app_commands.Choice(name="🎨 Creative", value="creative"),
        app_commands.Choice(name="💭 Deep Thoughts", value="deep"),
        app_commands.Choice(name="🎲 Silly & Fun", value="silly"),
        app_commands.Choice(name="💬 Random", value="random"),
    ])
    async def vibes_qotd(
        self,
        ctx: Context,
        action: str,
        question: str = None,
        category: str = "random",
    ) -> None:
        """
        Question of the Day operations: get, post now, or suggest.

        :param ctx: The hybrid command context.
        :param action: The action to perform (get/now/suggest).
        :param question: The suggested question (for suggest action).
        :param category: The category for the question (for suggest action).
        """
        if ctx.interaction:
            await ctx.defer()

        if action == "get":
            await self._qotd_get(ctx)
        elif action == "now":
            await self._qotd_now(ctx)
        elif action == "suggest":
            await self._qotd_suggest(ctx, question, category)

    async def _qotd_get(self, ctx: Context) -> None:
        """Get information about QOTD for this server."""
        schedule = await self.bot.database.get_qotd_schedule(ctx.guild.id)
        if not schedule:
            embed = discord.Embed(
                description="❌ QOTD is not configured. An admin needs to use `/vibes-admin setup` first.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        config = await self.bot.database.get_vibes_config(ctx.guild.id)
        qotd_enabled = config["qotd_enabled"] if config else False

        embed = discord.Embed(
            title="💬 Question of the Day Status",
            description=f"Configuration for {ctx.guild.name}",
            color=0xBEBEFE,
        )

        status = "✅ Enabled" if qotd_enabled else "❌ Disabled"
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Channel", value=f"<#{schedule['channel_id']}>", inline=True)
        embed.add_field(
            name="Post Time",
            value=f"{schedule['post_time']} (UTC{schedule['timezone_offset']:+d})",
            inline=True,
        )

        if schedule["last_post_date"]:
            embed.add_field(
                name="Last Posted",
                value=schedule["last_post_date"],
                inline=True,
            )

        embed.set_footer(text="Use /vibes-qotd suggest to add your own questions!")
        await ctx.send(embed=embed)

    async def _qotd_now(self, ctx: Context) -> None:
        """Post a Question of the Day immediately (admin only)."""
        if not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                description="❌ This action requires administrator permissions.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        schedule = await self.bot.database.get_qotd_schedule(ctx.guild.id)
        if not schedule:
            embed = discord.Embed(
                description="❌ QOTD is not configured. Use `/vibes-admin setup` first.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        success, error_msg = await self.post_qotd_to_server(ctx.guild.id, schedule["channel_id"])

        if success:
            embed = discord.Embed(
                title="✅ Question Posted!",
                description=f"Check <#{schedule['channel_id']}>",
                color=0x2ECC71,
            )
        else:
            embed = discord.Embed(
                title="❌ Failed to Post Question",
                description=f"**Error:** {error_msg}\n\nTry these fixes:\n• Check bot has permissions in <#{schedule['channel_id']}>\n• Verify the channel exists\n• Check `discord.log` for more details",
                color=0xE02B2B,
            )

        await ctx.send(embed=embed)

    async def _qotd_suggest(self, ctx: Context, question: str, category: str) -> None:
        """Suggest a custom question for the question pool."""
        if not question:
            embed = discord.Embed(
                description="❌ Please provide a question. Example: `/vibes-qotd suggest question:What's your favorite hobby?`",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        if len(question) < 10:
            embed = discord.Embed(
                description="❌ Question is too short. Please make it at least 10 characters.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        if len(question) > 500:
            embed = discord.Embed(
                description="❌ Question is too long. Please keep it under 500 characters.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        # Add to question pool
        question_id = await self.bot.database.add_qotd_question(
            question=question,
            category=category,
            is_custom=True,
            submitted_by_id=ctx.author.id,
            server_id=ctx.guild.id,
        )

        embed = discord.Embed(
            title="✅ Question Suggested!",
            description=f"Your question has been added to the {category} category.",
            color=0x2ECC71,
        )
        embed.add_field(name="Your Question", value=question, inline=False)
        embed.set_footer(text=f"Question ID: {question_id}")

        await ctx.send(embed=embed)

    # ===== CONSOLIDATED ADMIN COMMAND =====

    @commands.hybrid_command(
        name="vibes-admin",
        description="Admin operations for vibes features",
    )
    @app_commands.describe(
        action="Admin action to perform",
        feature="Which feature to configure or toggle",
        emoji="Memory emoji (for 'setup memory_emoji')",
        channel="QOTD channel (for 'setup qotd_schedule')",
        time="QOTD time in HH:MM format (for 'setup qotd_schedule')",
        timezone="Timezone offset from UTC (for 'setup qotd_schedule')",
        enabled="Enable or disable (for 'toggle' action)",
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Setup features", value="setup"),
        app_commands.Choice(name="Toggle features", value="toggle"),
        app_commands.Choice(name="View status", value="status"),
    ])
    @app_commands.choices(feature=[
        app_commands.Choice(name="Memory Emoji", value="memory_emoji"),
        app_commands.Choice(name="QOTD Schedule", value="qotd_schedule"),
        app_commands.Choice(name="QOTD", value="qotd"),
        app_commands.Choice(name="Throwback Memories", value="throwback"),
        app_commands.Choice(name="Auto-Suggest Memories", value="auto_suggest"),
    ])
    @commands.has_permissions(administrator=True)
    async def vibes_admin(
        self,
        ctx: Context,
        action: str,
        feature: str = None,
        emoji: str = None,
        channel: discord.TextChannel = None,
        time: str = None,
        timezone: int = 0,
        enabled: bool = None,
    ) -> None:
        """
        Admin operations for vibes features: setup, toggle, or view status.

        :param ctx: The hybrid command context.
        :param action: The admin action to perform.
        :param feature: Which feature to configure or toggle.
        :param emoji: Memory emoji (for setup memory_emoji).
        :param channel: QOTD channel (for setup qotd_schedule).
        :param time: QOTD time (for setup qotd_schedule).
        :param timezone: Timezone offset (for setup qotd_schedule).
        :param enabled: Enable or disable (for toggle action).
        """
        if ctx.interaction:
            await ctx.defer()

        if action == "setup":
            await self._admin_setup(ctx, feature, emoji, channel, time, timezone)
        elif action == "toggle":
            await self._admin_toggle(ctx, feature, enabled)
        elif action == "status":
            await self._admin_status(ctx)

    async def _admin_setup(
        self,
        ctx: Context,
        feature: str,
        emoji: str,
        channel: discord.TextChannel,
        time: str,
        timezone: int,
    ) -> None:
        """Setup vibes features."""
        if not feature:
            embed = discord.Embed(
                description="❌ Please specify a feature to setup: `memory_emoji` or `qotd_schedule`",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        if feature == "memory_emoji":
            if not emoji:
                embed = discord.Embed(
                    description="❌ Please provide an emoji. Example: `/vibes-admin setup feature:memory_emoji emoji:💾`",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed)
                return

            # Save the emoji
            await self.bot.database.set_memory_emoji(ctx.guild.id, emoji)

            embed = discord.Embed(
                title="✅ Memory Emoji Updated!",
                description=f"Memory emoji is now: {emoji}",
                color=0x2ECC71,
            )
            embed.add_field(
                name="How to Use",
                value=f"React to any message with {emoji} to save it as a memory!",
                inline=False,
            )

            await ctx.send(embed=embed)

        elif feature == "qotd_schedule":
            if not channel or not time:
                embed = discord.Embed(
                    description="❌ Please provide both channel and time. Example: `/vibes-admin setup feature:qotd_schedule channel:#general time:09:00 timezone:-5`",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed)
                return

            # Validate time format
            parsed_time = scheduling.parse_time_string(time)
            if not parsed_time:
                embed = discord.Embed(
                    description="❌ Invalid time format. Please use HH:MM (24-hour), like 09:00 or 14:30",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed)
                return

            # Validate timezone
            if timezone < -12 or timezone > 14:
                embed = discord.Embed(
                    description="❌ Invalid timezone offset. Must be between -12 and +14.",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed)
                return

            # Validate bot can access and post to channel
            self.bot.logger.info(f"Validating channel access: {channel.name} (ID: {channel.id})")
            permissions = channel.permissions_for(ctx.guild.me)

            missing_perms = []
            if not permissions.view_channel:
                missing_perms.append("View Channel")
            if not permissions.send_messages:
                missing_perms.append("Send Messages")
            if not permissions.embed_links:
                missing_perms.append("Embed Links")
            if not permissions.add_reactions:
                missing_perms.append("Add Reactions")

            if missing_perms:
                perms_list = ", ".join(missing_perms)
                embed = discord.Embed(
                    title="❌ Missing Permissions",
                    description=f"I don't have the required permissions in {channel.mention}.\n\n**Missing:** {perms_list}\n\nPlease grant these permissions and try again.",
                    color=0xE02B2B,
                )
                await ctx.send(embed=embed)
                return

            # Save schedule
            await self.bot.database.set_qotd_schedule(
                ctx.guild.id, channel.id, time, timezone
            )

            self.bot.logger.info(f"QOTD configured successfully for {ctx.guild.name}: #{channel.name} at {time} UTC{timezone:+d}")

            embed = discord.Embed(
                title="✅ Question of the Day Configured!",
                description="Daily questions will now be posted automatically.",
                color=0x2ECC71,
            )
            embed.add_field(name="Channel", value=channel.mention, inline=True)
            embed.add_field(name="Time", value=f"{time} (UTC{timezone:+d})", inline=True)
            embed.add_field(
                name="Commands",
                value="• `/vibes-qotd now` - Post question now\n• `/vibes-qotd suggest` - Add your own questions\n• `/vibes-admin toggle` - Enable/disable",
                inline=False,
            )

            await ctx.send(embed=embed)

        else:
            embed = discord.Embed(
                description=f"❌ Unknown feature: {feature}. Use `memory_emoji` or `qotd_schedule`.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)

    async def _admin_toggle(self, ctx: Context, feature: str, enabled: bool) -> None:
        """Toggle vibes features on or off."""
        if not feature:
            embed = discord.Embed(
                description="❌ Please specify a feature to toggle: `qotd`, `throwback`, or `auto_suggest`",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        if enabled is None:
            embed = discord.Embed(
                description="❌ Please specify whether to enable or disable. Example: `/vibes-admin toggle feature:qotd enabled:True`",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        # Map friendly names to database feature names
        feature_map = {
            "qotd_schedule": "qotd",
            "memory_emoji": None,  # Not a toggle-able feature
        }

        # Use mapped name if exists, otherwise use as-is
        db_feature = feature_map.get(feature, feature)

        if db_feature is None:
            embed = discord.Embed(
                description=f"❌ '{feature}' cannot be toggled. Use `qotd`, `throwback`, or `auto_suggest`.",
                color=0xE02B2B,
            )
            await ctx.send(embed=embed)
            return

        success = await self.bot.database.toggle_vibes_feature(
            ctx.guild.id, db_feature, enabled
        )

        if success:
            status = "enabled" if enabled else "disabled"
            emoji = "✅" if enabled else "❌"
            color = 0x2ECC71 if enabled else 0xE02B2B

            feature_names = {
                "qotd": "Question of the Day",
                "throwback": "Throwback Memories",
                "auto_suggest": "Auto-Suggest Memories",
            }

            embed = discord.Embed(
                title=f"{emoji} {feature_names.get(db_feature, db_feature).title()} {status.capitalize()}",
                description=f"{feature_names.get(db_feature, db_feature)} has been {status}.",
                color=color,
            )
        else:
            embed = discord.Embed(
                description="❌ Failed to toggle feature. Please try again.",
                color=0xE02B2B,
            )

        await ctx.send(embed=embed)

    async def _admin_status(self, ctx: Context) -> None:
        """View the current vibes configuration for this server."""
        config = await self.bot.database.get_vibes_config(ctx.guild.id)
        qotd_schedule = await self.bot.database.get_qotd_schedule(ctx.guild.id)
        stats = await self.bot.database.get_memory_stats(ctx.guild.id)

        embed = discord.Embed(
            title="✨ Community Vibes Status",
            description=f"Configuration for {ctx.guild.name}",
            color=0xBEBEFE,
        )

        # Memory Bank status
        memory_emoji = config["memory_emoji"] if config else "💾"
        embed.add_field(
            name="💾 Memory Bank",
            value=f"Emoji: {memory_emoji}\nTotal Memories: {stats['total_memories']}",
            inline=True,
        )

        # QOTD status
        if config and qotd_schedule:
            qotd_status = "✅ Enabled" if config["qotd_enabled"] else "❌ Disabled"
            embed.add_field(
                name="💬 Question of the Day",
                value=f"Status: {qotd_status}\nChannel: <#{qotd_schedule['channel_id']}>\nTime: {qotd_schedule['post_time']} (UTC{qotd_schedule['timezone_offset']:+d})",
                inline=True,
            )
        else:
            embed.add_field(
                name="💬 Question of the Day",
                value="Not configured\nUse `/vibes-admin setup`",
                inline=True,
            )

        # Other features
        if config:
            throwback_status = "✅" if config["throwback_enabled"] else "❌"
            auto_suggest_status = "✅" if config["auto_suggest_memories"] else "❌"

            embed.add_field(
                name="Other Features",
                value=f"{throwback_status} Throwback Memories\n{auto_suggest_status} Auto-Suggest",
                inline=False,
            )

        embed.set_footer(
            text="Use /vibes-admin setup to configure • /vibes-admin toggle to enable/disable"
        )

        await ctx.send(embed=embed)

    # ===== HELP COMMAND =====

    @commands.hybrid_command(
        name="vibes-help",
        description="Get help with vibes commands",
    )
    async def vibes_help(self, ctx: Context) -> None:
        """
        Display help information for vibes commands.

        :param ctx: The hybrid command context.
        """
        embed = discord.Embed(
            title="✨ Community Vibes - Help",
            description="Save memories and share questions with your community!",
            color=0xBEBEFE,
        )

        # Memory commands
        embed.add_field(
            name="💾 Memory Bank",
            value=(
                "**`/vibes-memory save`** - Save a message as a memory\n"
                "**`/vibes-memory view`** - Browse memories (all/random/from user/search)\n"
                "**`/vibes-memory stats`** - View memory statistics\n"
                "\n*Tip: React with the memory emoji to save messages automatically!*"
            ),
            inline=False,
        )

        # QOTD commands
        embed.add_field(
            name="💬 Question of the Day",
            value=(
                "**`/vibes-qotd get`** - View QOTD status\n"
                "**`/vibes-qotd now`** - Post QOTD now (admin)\n"
                "**`/vibes-qotd suggest`** - Suggest a question\n"
            ),
            inline=False,
        )

        # Admin commands
        if ctx.author.guild_permissions.administrator:
            embed.add_field(
                name="⚙️ Admin Commands",
                value=(
                    "**`/vibes-admin setup`** - Configure features\n"
                    "  • `memory_emoji` - Set memory emoji\n"
                    "  • `qotd_schedule` - Schedule QOTD posts\n"
                    "**`/vibes-admin toggle`** - Enable/disable features\n"
                    "**`/vibes-admin status`** - View configuration\n"
                ),
                inline=False,
            )

        embed.set_footer(text="Need more help? Ask your server admins!")
        await ctx.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(Vibes(bot))
