"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.3.0
"""

import os

import discord
from anthropic import AsyncAnthropic
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context


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
        question="The question you want to ask Claude",
        shared="Use shared channel conversation (default: yes)"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ask(self, context: Context, question: str, shared: bool = True) -> None:
        """
        Ask Claude AI a question with conversation context.

        :param context: The hybrid command context.
        :param question: The question to ask Claude.
        :param shared: Whether to use shared channel conversation (default: True).
        """
        await self._process_question(context, question, shared)

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

                # Call the Anthropic API with Claude 3.5 Haiku
                api_response = await self.client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=2048,
                    messages=messages,
                )

                # Extract the response text
                response_text = api_response.content[0].text

                # Store only the assistant's response in the database
                await self.bot.database.add_claude_message(
                    context.channel.id, 0, "assistant", response_text
                )

                # If response is too long, split into multiple messages
                if len(response_text) > 4000:
                    # Split response into chunks
                    chunks = []
                    while response_text:
                        if len(response_text) <= 4000:
                            chunks.append(response_text)
                            break
                        # Find a good break point (newline or space)
                        split_point = 4000
                        for i in range(3900, 4000):
                            if i < len(response_text) and response_text[i] in ['\n', ' ', '.', '!', '?']:
                                split_point = i + 1
                                break
                        chunks.append(response_text[:split_point])
                        response_text = response_text[split_point:]

                    # Send first chunk with embed
                    embed = discord.Embed(
                        title="Claude's Response",
                        description=chunks[0],
                        color=0xBEBEFE,
                    )
                    # Add the question as the author field with user's avatar
                    question_display = question[:250] + "..." if len(question) > 250 else question
                    embed.set_author(
                        name=question_display,
                        icon_url=context.author.avatar.url if context.author.avatar else None
                    )
                    total_msgs = await self.bot.database.get_total_messages(context.channel.id, user_id=user_id_filter)
                    conversation_type = "Shared" if shared else "Personal"
                    embed.set_footer(text=f"{conversation_type} conversation: {total_msgs // 2} exchanges")
                    await context.send(embed=embed)

                    # Send remaining chunks as plain text
                    for chunk in chunks[1:]:
                        await context.channel.send(chunk)
                else:
                    # Create and send the response embed
                    embed = discord.Embed(
                        title="Claude's Response",
                        description=response_text,
                        color=0xBEBEFE,
                    )
                    # Add the question as the author field with user's avatar
                    question_display = question[:250] + "..." if len(question) > 250 else question
                    embed.set_author(
                        name=question_display,
                        icon_url=context.author.avatar.url if context.author.avatar else None
                    )
                    total_msgs = await self.bot.database.get_total_messages(context.channel.id, user_id=user_id_filter)
                    conversation_type = "Shared" if shared else "Personal"
                    embed.set_footer(text=f"{conversation_type} conversation: {total_msgs // 2} exchanges")
                    await context.send(embed=embed)

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
            exchanges = total_msgs // 2
            mode_description = "The conversation is shared by everyone in this channel." if shared else "This is your personal conversation - only you can see it."
            embed = discord.Embed(
                title="Conversation Info",
                description=f"This {conversation_type} conversation has **{total_msgs}** messages ({exchanges} exchanges).\n\n"
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


async def setup(bot) -> None:
    await bot.add_cog(Claude(bot))
