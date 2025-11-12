"""Shared fixtures for all tests."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
import discord


@pytest.fixture
def mock_bot():
    """Mock Discord bot with logger and database."""
    bot = Mock()
    bot.logger = Mock()
    bot.logger.info = Mock()
    bot.logger.warning = Mock()
    bot.logger.error = Mock()
    bot.logger.debug = Mock()

    # Mock database
    bot.database = AsyncMock()
    bot.database.connection = AsyncMock()

    # Mock user
    bot.user = Mock()
    bot.user.id = 12345
    bot.user.mention = "<@12345>"
    bot.user.name = "TestBot"

    # Mock methods
    bot.wait_until_ready = AsyncMock()
    bot.get_channel = Mock(return_value=None)
    bot.fetch_channel = AsyncMock()
    bot.get_guild = Mock(return_value=None)

    return bot


@pytest.fixture
def mock_author():
    """Mock Discord user/author."""
    author = Mock()
    author.id = 67890
    author.mention = "<@67890>"
    author.name = "TestUser"
    author.display_name = "TestUser"
    author.avatar = Mock()
    author.avatar.url = "https://example.com/avatar.png"
    author.bot = False

    # Guild permissions
    author.guild_permissions = Mock()
    author.guild_permissions.administrator = False
    author.guild_permissions.manage_messages = False

    return author


@pytest.fixture
def mock_guild():
    """Mock Discord guild/server."""
    guild = Mock()
    guild.id = 11111
    guild.name = "Test Guild"
    guild.me = Mock()
    guild.me.guild_permissions = Mock()
    guild.members = []
    guild.text_channels = []
    return guild


@pytest.fixture
def mock_channel():
    """Mock Discord text channel."""
    channel = Mock(spec=discord.TextChannel)
    channel.id = 22222
    channel.name = "test-channel"
    channel.mention = "<#22222>"
    channel.guild = Mock()
    channel.guild.id = 11111
    channel.guild.name = "Test Guild"
    channel.guild.me = Mock()

    # Permissions
    channel.permissions_for = Mock(return_value=Mock(
        send_messages=True,
        embed_links=True,
        add_reactions=True,
        view_channel=True,
        manage_messages=True
    ))

    # Methods
    channel.send = AsyncMock()
    channel.fetch_message = AsyncMock()
    channel.history = Mock()
    channel.typing = Mock()

    return channel


@pytest.fixture
def mock_context(mock_bot, mock_author, mock_guild, mock_channel):
    """Mock command context with all common properties."""
    ctx = AsyncMock()
    ctx.bot = mock_bot
    ctx.author = mock_author
    ctx.guild = mock_guild
    ctx.channel = mock_channel

    # Interaction (for slash commands)
    ctx.interaction = None  # Set to Mock() in tests that need it

    # Methods
    ctx.send = AsyncMock()
    ctx.defer = AsyncMock()
    ctx.reply = AsyncMock()

    # Command info
    ctx.command = Mock()
    ctx.command.name = "test_command"

    return ctx


@pytest.fixture
def mock_message(mock_author, mock_channel):
    """Mock Discord message."""
    message = Mock(spec=discord.Message)
    message.id = 99999
    message.author = mock_author
    message.channel = mock_channel
    message.guild = mock_channel.guild
    message.content = "Test message content"
    message.created_at = Mock()
    message.mentions = []
    message.reactions = []

    # Methods
    message.add_reaction = AsyncMock()
    message.edit = AsyncMock()
    message.delete = AsyncMock()

    return message


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic Claude client."""
    client = AsyncMock()

    # Mock messages.create response
    mock_response = Mock()
    mock_response.content = [Mock(text="This is a test response from Claude.")]
    client.messages.create = AsyncMock(return_value=mock_response)

    # Mock streaming response
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=None)

    async def text_stream_generator():
        words = ["This ", "is ", "a ", "test ", "response."]
        for word in words:
            yield word

    mock_stream.text_stream = text_stream_generator()
    client.messages.stream = Mock(return_value=mock_stream)

    return client
