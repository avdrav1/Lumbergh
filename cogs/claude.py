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

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        Event listener that triggers when a message is sent.
        Responds when the bot is mentioned.

        :param message: The message that was sent.
        """
        # Ignore messages from the bot itself
        if message.author.bot:
            return

        # Check if bot was mentioned
        if self.bot.user not in message.mentions:
            return

        # Don't respond if it's a command
        if message.content.startswith(self.bot.bot_prefix) or message.content.startswith("/"):
            return

        # Extract the question (remove the mention)
        question = message.content
        for mention in message.mentions:
            question = question.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
        question = question.strip()

        if not question:
            embed = discord.Embed(
                description="You mentioned me, but didn't ask anything! Try asking me a question.",
                color=0x3498db,
            )
            await message.reply(embed=embed, mention_author=False)
            return

        # Process the question
        await self._process_question(message, question, message.author, message.channel)

    @commands.hybrid_command(
        name="ask",
        description="Ask Claude AI a question with conversation context.",
    )
    @app_commands.describe(question="The question you want to ask Claude")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ask(self, context: Context, *, question: str) -> None:
        """
        Ask Claude AI a question with conversation context.

        :param context: The hybrid command context.
        :param question: The question to ask Claude.
        """
        await self._process_question(context.message, question, context.author, context.channel)

    async def _process_question(
        self, message: discord.Message, question: str, author: discord.User, channel: discord.TextChannel
    ) -> None:
        """
        Process a question to Claude with conversation context.

        :param message: The Discord message object.
        :param question: The question to ask.
        :param author: The user asking the question.
        :param channel: The channel where the question was asked.
        """
        if not self.client:
            embed = discord.Embed(
                title="Error",
                description="Claude AI is not configured. Please contact the bot owner.",
                color=0xE02B2B,
            )
            await message.reply(embed=embed, mention_author=False)
            return

        if len(question) > 2000:
            embed = discord.Embed(
                title="Error",
                description="Your question is too long. Please keep it under 2000 characters.",
                color=0xE02B2B,
            )
            await message.reply(embed=embed, mention_author=False)
            return

        # Show typing indicator while processing
        async with channel.typing():
            try:
                # Get shared conversation history for this channel
                history = await self.bot.database.get_conversation_history(
                    channel.id, limit=20
                )

                # Build messages array for Claude
                messages = []
                for role, content in history:
                    messages.append({"role": role, "content": content})

                # Add the current question
                messages.append({"role": "user", "content": question})

                # Call the Anthropic API with Claude 3.5 Haiku
                api_response = await self.client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=2048,
                    messages=messages,
                )

                # Extract the response text
                response_text = api_response.content[0].text

                # Store the question and response in the database (shared conversation)
                await self.bot.database.add_claude_message(
                    channel.id, author.id, "user", question
                )
                await self.bot.database.add_claude_message(
                    channel.id, 0, "assistant", response_text
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
                    total_msgs = await self.bot.database.get_total_messages(channel.id)
                    embed.set_footer(text=f"Channel conversation: {total_msgs // 2} exchanges")
                    await message.reply(embed=embed, mention_author=False)

                    # Send remaining chunks as plain text
                    for chunk in chunks[1:]:
                        await channel.send(chunk)
                else:
                    # Create and send the response embed
                    embed = discord.Embed(
                        title="Claude's Response",
                        description=response_text,
                        color=0xBEBEFE,
                    )
                    total_msgs = await self.bot.database.get_total_messages(channel.id)
                    embed.set_footer(text=f"Channel conversation: {total_msgs // 2} exchanges")
                    await message.reply(embed=embed, mention_author=False)

                self.bot.logger.info(
                    f"{author} (ID: {author.id}) asked Claude in #{channel.name}: {question[:50]}..."
                )

            except Exception as e:
                self.bot.logger.error(f"Error calling Claude API: {e}")
                embed = discord.Embed(
                    title="Error",
                    description="An error occurred while processing your request. Please try again later.",
                    color=0xE02B2B,
                )
                await message.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(
        name="clear",
        description="Clear the shared conversation history with Claude in this channel.",
    )
    async def clear(self, context: Context) -> None:
        """
        Clear the shared conversation history with Claude in this channel.

        :param context: The hybrid command context.
        """
        deleted_count = await self.bot.database.clear_conversation(context.channel.id)

        if deleted_count > 0:
            embed = discord.Embed(
                title="Conversation Cleared",
                description=f"Successfully cleared {deleted_count} messages from this channel's conversation history.",
                color=0x2ecc71,
            )
        else:
            embed = discord.Embed(
                title="No History",
                description="This channel doesn't have any conversation history with Claude yet.",
                color=0x3498db,
            )

        await context.send(embed=embed)
        self.bot.logger.info(
            f"{context.author} cleared the Claude conversation history in #{context.channel.name}"
        )

    @commands.hybrid_command(
        name="context",
        description="View information about this channel's conversation with Claude.",
    )
    async def context_info(self, context: Context) -> None:
        """
        View information about this channel's conversation with Claude.

        :param context: The hybrid command context.
        """
        total_msgs = await self.bot.database.get_total_messages(context.channel.id)

        if total_msgs == 0:
            embed = discord.Embed(
                title="Conversation Info",
                description="This channel hasn't started a conversation with Claude yet.",
                color=0x3498db,
            )
        else:
            exchanges = total_msgs // 2
            embed = discord.Embed(
                title="Conversation Info",
                description=f"This channel's conversation has **{total_msgs}** messages ({exchanges} exchanges).\n\n"
                f"The conversation is shared by everyone in this channel.\n"
                f"Use `/clear` to reset the conversation.",
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
