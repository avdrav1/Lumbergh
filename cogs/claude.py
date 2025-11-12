"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.3.0
"""

import os
import time
import asyncio

import discord
from anthropic import AsyncAnthropic
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context


class ExpandableView(discord.ui.View):
    """View with a button to expand/collapse long responses."""

    def __init__(self, full_text: str, truncated_text: str, embed: discord.Embed, question_display: str, conversation_footer: str):
        super().__init__(timeout=None)  # Persistent view
        self.full_text = full_text
        self.truncated_text = truncated_text
        self.base_embed = embed
        self.question_display = question_display
        self.conversation_footer = conversation_footer
        self.expanded = False

    @discord.ui.button(label="Show Full Response", style=discord.ButtonStyle.primary, custom_id="expand_response")
    async def toggle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle between expanded and collapsed view."""
        self.expanded = not self.expanded

        # Create new embed to avoid mutation issues
        embed = discord.Embed(
            title="Claude's Response",
            description=self.full_text if self.expanded else self.truncated_text,
            color=0xBEBEFE,
        )
        embed.set_author(
            name=self.question_display,
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )

        if self.expanded:
            # Expanded state
            button.label = "Show Less"
            button.style = discord.ButtonStyle.secondary
            embed.set_footer(text=self.conversation_footer)
        else:
            # Collapsed state
            button.label = "Show Full Response"
            button.style = discord.ButtonStyle.primary
            embed.set_footer(text=f"{self.conversation_footer} • Response truncated")

        await interaction.response.edit_message(embed=embed, view=self)


class Claude(commands.Cog, name="claude"):
    def __init__(self, bot) -> None:
        self.bot = bot
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            self.bot.logger.warning(
                "ANTHROPIC_API_KEY not found in environment variables. Claude commands will not work."
            )
            self.client = None
        else:
            self.client = AsyncAnthropic(api_key=api_key)
            self.bot.logger.info("Claude AI integration initialized successfully.")

    @commands.hybrid_command(
        name="ask",
        description="Ask Claude AI a question with conversation context.",
    )
    @app_commands.describe(
        input="Your question or prompt for Claude",
        context="Choose conversation context (shared or personal)"
    )
    @app_commands.choices(context=[
        app_commands.Choice(name="shared", value="shared"),
        app_commands.Choice(name="personal", value="personal")
    ])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ask(self, ctx: Context, input: str, context: str = "shared") -> None:
        """
        Ask Claude AI a question with conversation context.

        :param ctx: The hybrid command context.
        :param input: Your question or prompt for Claude.
        :param context: Conversation context mode - "shared" or "personal" (default: shared).
        """
        # Convert string context to boolean for internal processing
        shared = (context == "shared")
        await self._process_question(ctx, input, shared)

    @commands.hybrid_command(
        name="prompt",
        description="Ask Claude AI a question (alias for /ask).",
    )
    @app_commands.describe(
        input="Your question or prompt for Claude",
        context="Choose conversation context (shared or personal)"
    )
    @app_commands.choices(context=[
        app_commands.Choice(name="shared", value="shared"),
        app_commands.Choice(name="personal", value="personal")
    ])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def prompt(self, ctx: Context, input: str, context: str = "shared") -> None:
        """
        Ask Claude AI a question with conversation context.
        This is an alias for the /ask command.

        :param ctx: The hybrid command context.
        :param input: Your question or prompt for Claude.
        :param context: Conversation context mode - "shared" or "personal" (default: shared).
        """
        # Convert string context to boolean for internal processing
        shared = (context == "shared")
        await self._process_question(ctx, input, shared)

    def _format_for_discord(self, text: str) -> str:
        """
        Format Claude's response for proper Discord markdown rendering.
        Adds indentation to bullet points so they render as nested lists.

        :param text: The raw response text from Claude.
        :return: Formatted text with proper indentation for Discord.
        """
        lines = text.split('\n')
        formatted_lines = []
        in_numbered_list = False

        for line in lines:
            stripped = line.lstrip()

            # Check if this is a numbered list item (e.g., "1. ", "2. ", etc.)
            if stripped and len(stripped) > 2 and stripped[0].isdigit() and stripped[1:3] in ['. ', ') ']:
                in_numbered_list = True
                formatted_lines.append(line)
            # Check if this is a bullet point that should be indented
            elif stripped.startswith('-') or stripped.startswith('*') or stripped.startswith('•'):
                # Add indentation (2 spaces) for proper nesting
                formatted_lines.append('  ' + stripped)
            else:
                # Empty line or regular text - check if we should exit numbered list context
                if not stripped:
                    in_numbered_list = False
                formatted_lines.append(line)

        return '\n'.join(formatted_lines)

    async def _process_question(
        self, context: Context, question: str, shared: bool = True
    ) -> None:
        """
        Process a question to Claude with conversation context.

        :param context: The command context.
        :param question: The question to ask.
        :param shared: Whether to use shared channel conversation (default: True).
        """
        # Defer the response immediately for slash commands to prevent timeout
        if context.interaction:
            await context.defer()

        if not self.client:
            embed = discord.Embed(
                title="Error",
                description="Claude AI is not configured. Please contact the bot owner.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return

        if len(question) > 2000:
            embed = discord.Embed(
                title="Error",
                description="Your question is too long. Please keep it under 2000 characters.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return

        # Show typing indicator while processing
        async with context.channel.typing():
            try:
                # Store the user's question FIRST to ensure conversation consistency
                await self.bot.database.add_claude_message(
                    context.channel.id, context.author.id, "user", question
                )

                # Get conversation history for this channel (shared or personal based on mode)
                user_id_filter = None if shared else context.author.id
                history = await self.bot.database.get_conversation_history(
                    context.channel.id, limit=20, user_id=user_id_filter
                )

                # Build messages array for Claude from the complete history
                messages = []
                for role, content in history:
                    messages.append({"role": role, "content": content})

                # Prepare embed metadata
                question_display = question[:250] + "..." if len(question) > 250 else question
                conversation_type = "Shared" if shared else "Personal"

                # Get current message count (will be incremented after response)
                total_msgs = await self.bot.database.get_total_messages(context.channel.id, user_id=user_id_filter)

                # Create initial embed
                embed = discord.Embed(
                    title="Claude's Response",
                    description="*Thinking...*",
                    color=0xBEBEFE,
                )
                embed.set_author(
                    name=question_display,
                    icon_url=context.author.avatar.url if context.author.avatar else None
                )
                embed.set_footer(text=f"{conversation_type} conversation: {total_msgs + 1} questions")

                # Send initial message immediately
                message = await context.send(embed=embed)

                # Stream the response from Claude API
                accumulated_text = ""
                last_update = time.time()
                update_interval = 0.75  # Update every 0.75 seconds to avoid rate limits

                try:
                    async with self.client.messages.stream(
                        model="claude-3-5-haiku-20241022",
                        max_tokens=2048,
                        messages=messages,
                    ) as stream:
                        async for text in stream.text_stream:
                            accumulated_text += text

                            # Update message periodically to show progress
                            current_time = time.time()
                            if current_time - last_update >= update_interval:
                                # Truncate if getting long (embed limit is 4096)
                                display_text = accumulated_text
                                if len(display_text) > 3900:
                                    display_text = accumulated_text[:3900] + "\n\n*...streaming continues...*"

                                embed.description = display_text
                                try:
                                    await message.edit(embed=embed)
                                    last_update = current_time
                                except discord.errors.HTTPException:
                                    # Rate limit hit, skip this update
                                    pass

                    # Format the complete response for proper Discord markdown rendering
                    response_text = self._format_for_discord(accumulated_text)

                    # Store the complete response in database
                    user_id_for_response = 0 if shared else context.author.id
                    await self.bot.database.add_claude_message(
                        context.channel.id, user_id_for_response, "assistant", response_text
                    )

                    # Final update with formatted response
                    if len(response_text) <= 4000:
                        # Check if response should be truncated with expand button
                        # Show only 1-2 lines (~150 chars) by default
                        truncation_threshold = 150
                        min_truncation = 100  # Minimum chars to show (at least 1 line)
                        conversation_footer = f"{conversation_type} conversation: {total_msgs + 1} questions"

                        if len(response_text) > truncation_threshold:
                            # Response is long - add truncation with expand button
                            # Find a good truncation point (prefer end of sentence)
                            truncate_at = truncation_threshold

                            # Look for sentence ending near threshold
                            for i in range(truncation_threshold - 50, min(truncation_threshold + 100, len(response_text))):
                                if i < len(response_text) and response_text[i] in ['.', '!', '?']:
                                    truncate_at = i + 1
                                    break

                            # If no sentence ending found, look for word boundary
                            if truncate_at == truncation_threshold:
                                for i in range(truncation_threshold, min(truncation_threshold + 50, len(response_text))):
                                    if i < len(response_text) and response_text[i] == ' ':
                                        truncate_at = i
                                        break

                            # Ensure minimum truncation length
                            if truncate_at < min_truncation:
                                truncate_at = min(min_truncation, len(response_text))

                            truncated_text = response_text[:truncate_at].strip() + "...\n\n*⬇️ Click button below to read full response*"

                            # Create view with expand button
                            view = ExpandableView(
                                full_text=response_text,
                                truncated_text=truncated_text,
                                embed=embed,
                                question_display=question_display,
                                conversation_footer=conversation_footer
                            )

                            # Update message with truncated text and button
                            embed.description = truncated_text
                            embed.set_footer(text=f"{conversation_footer} • Tap button to expand")
                            await message.edit(embed=embed, view=view)
                        else:
                            # Response is short enough - show normally
                            embed.description = response_text
                            await message.edit(embed=embed)
                    else:
                        # Response too long for single embed - send in chunks
                        chunks = []
                        remaining_text = response_text

                        while remaining_text:
                            chunk_limit = 4000 if not chunks else 1900

                            if len(remaining_text) <= chunk_limit:
                                chunks.append(remaining_text)
                                break

                            # Find a good break point
                            split_point = chunk_limit
                            for i in range(chunk_limit - 100, chunk_limit):
                                if i < len(remaining_text) and remaining_text[i] in ['\n', ' ', '.', '!', '?']:
                                    split_point = i + 1
                                    break

                            chunks.append(remaining_text[:split_point])
                            remaining_text = remaining_text[split_point:]

                        # Update initial message with first chunk
                        embed.description = chunks[0]
                        await message.edit(embed=embed)

                        # Send remaining chunks as separate messages
                        for chunk in chunks[1:]:
                            await context.send(chunk)

                except Exception as e:
                    # Handle streaming errors
                    self.bot.logger.error(f"Error during Claude streaming: {e}")

                    # If we got some response, show it
                    if accumulated_text:
                        response_text = self._format_for_discord(accumulated_text)
                        embed.description = response_text + "\n\n*⚠️ Stream interrupted - showing partial response*"
                        await message.edit(embed=embed)

                        # Still store partial response
                        user_id_for_response = 0 if shared else context.author.id
                        await self.bot.database.add_claude_message(
                            context.channel.id, user_id_for_response, "assistant", response_text
                        )
                    else:
                        # No response received, show error
                        embed.description = "❌ An error occurred while generating the response. Please try again."
                        embed.color = 0xE02B2B
                        await message.edit(embed=embed)
                        raise

                self.bot.logger.info(
                    f"{context.author} (ID: {context.author.id}) asked Claude in #{context.channel.name}: {question[:50]}..."
                )

            except Exception as e:
                self.bot.logger.error(f"Error calling Claude API: {e}")
                embed = discord.Embed(
                    title="Error",
                    description="An error occurred while processing your request. Please try again later.",
                    color=0xE02B2B,
                )
                await context.send(embed=embed)

    @commands.hybrid_command(
        name="clear",
        description="Clear conversation history with Claude in this channel.",
    )
    @app_commands.describe(shared="Clear shared channel conversation (default: yes)")
    async def clear(self, context: Context, shared: bool = True) -> None:
        """
        Clear conversation history with Claude in this channel.

        :param context: The hybrid command context.
        :param shared: Whether to clear shared channel conversation (default: True).
        """
        # Defer the response for slash commands
        if context.interaction:
            await context.defer()

        user_id_filter = None if shared else context.author.id
        deleted_count = await self.bot.database.clear_conversation(context.channel.id, user_id=user_id_filter)

        conversation_type = "shared channel" if shared else "your personal"
        if deleted_count > 0:
            embed = discord.Embed(
                title="Conversation Cleared",
                description=f"Successfully cleared {deleted_count} messages from {conversation_type} conversation history.",
                color=0x2ecc71,
            )
        else:
            embed = discord.Embed(
                title="No History",
                description=f"This channel doesn't have any {conversation_type} conversation history with Claude yet.",
                color=0x3498db,
            )

        await context.send(embed=embed)
        mode_str = "shared" if shared else "personal"
        self.bot.logger.info(
            f"{context.author} cleared the {mode_str} Claude conversation history in #{context.channel.name}"
        )

    @commands.hybrid_command(
        name="context",
        description="View information about conversation with Claude.",
    )
    @app_commands.describe(shared="View shared channel conversation (default: yes)")
    async def context_info(self, context: Context, shared: bool = True) -> None:
        """
        View information about conversation with Claude.

        :param context: The hybrid command context.
        :param shared: Whether to view shared channel conversation (default: True).
        """
        # Defer the response for slash commands
        if context.interaction:
            await context.defer()

        user_id_filter = None if shared else context.author.id
        total_msgs = await self.bot.database.get_total_messages(context.channel.id, user_id=user_id_filter)

        conversation_type = "shared channel" if shared else "your personal"
        clear_command = "/clear" if shared else "/clear shared:false"

        if total_msgs == 0:
            embed = discord.Embed(
                title="Conversation Info",
                description=f"This channel doesn't have any {conversation_type} conversation with Claude yet.",
                color=0x3498db,
            )
        else:
            mode_description = "The conversation is shared by everyone in this channel." if shared else "This is your personal conversation - only you can see it."
            embed = discord.Embed(
                title="Conversation Info",
                description=f"This {conversation_type} conversation has **{total_msgs}** questions asked.\n\n"
                f"{mode_description}\n"
                f"Use `{clear_command}` to reset the conversation.",
                color=0xBEBEFE,
            )

        await context.send(embed=embed)

    @ask.error
    async def ask_error(self, context: Context, error: commands.CommandError) -> None:
        """
        Error handler for the ask command.

        :param context: The hybrid command context.
        :param error: The error that occurred.
        """
        if isinstance(error, commands.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            hours, minutes = divmod(minutes, 60)
            hours = hours % 24
            embed = discord.Embed(
                description=f"**Please slow down** - You can use this command again in {f'{round(hours)} hours' if round(hours) > 0 else ''} {f'{round(minutes)} minutes' if round(minutes) > 0 else ''} {f'{round(seconds)} seconds' if round(seconds) > 0 else ''}.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)

    @prompt.error
    async def prompt_error(self, context: Context, error: commands.CommandError) -> None:
        """
        Error handler for the prompt command.

        :param context: The hybrid command context.
        :param error: The error that occurred.
        """
        if isinstance(error, commands.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            hours, minutes = divmod(minutes, 60)
            hours = hours % 24
            embed = discord.Embed(
                description=f"**Please slow down** - You can use this command again in {f'{round(hours)} hours' if round(hours) > 0 else ''} {f'{round(minutes)} minutes' if round(minutes) > 0 else ''} {f'{round(seconds)} seconds' if round(seconds) > 0 else ''}.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        Listen for bot mentions and respond with Claude.

        :param message: The message that was sent.
        """
        # Ignore messages from bots (prevent loops)
        if message.author.bot:
            return

        # Check if bot is mentioned
        if not self.bot.user.mentioned_in(message):
            return

        # Check if Claude client is available
        if not self.client:
            return

        # Ignore messages in art analysis threads (they're created by the art cog)
        if isinstance(message.channel, discord.Thread):
            if message.channel.name.startswith("Analysis: "):
                self.bot.logger.debug(f"Ignoring mention in art analysis thread: {message.channel.name}")
                return

        # Extract question by removing bot mentions
        question = message.content
        for mention in message.mentions:
            if mention.id == self.bot.user.id:
                question = question.replace(f'<@{mention.id}>', '').replace(f'<@!{mention.id}>', '')

        # Clean up whitespace
        question = question.strip()

        # Ignore empty messages
        if not question:
            return

        # Create context from message
        context = await self.bot.get_context(message)

        # Check if this is a bot command (e.g., "@Lumbergh sync guild")
        # If it is, let the command system handle it, don't process as Claude prompt
        if context.command is not None:
            return

        # Process as a shared conversation by default
        try:
            await self._process_question(context, question, shared=True)
        except Exception as e:
            self.bot.logger.error(f"Error processing mention: {e}")


async def setup(bot) -> None:
    await bot.add_cog(Claude(bot))
