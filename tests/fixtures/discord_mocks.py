"""Helper functions for creating Discord mock objects."""
from unittest.mock import Mock, AsyncMock
import discord


def create_mock_embed(title=None, description=None, color=None):
    """Create a mock Discord embed."""
    embed = Mock(spec=discord.Embed)
    embed.title = title
    embed.description = description
    embed.color = color
    embed.fields = []
    embed.footer = Mock(text=None)
    embed.author = Mock(name=None)
    embed.add_field = Mock()
    embed.set_footer = Mock()
    embed.set_author = Mock()
    embed.set_thumbnail = Mock()
    return embed


def create_mock_thread(parent_channel, name="Test Thread", thread_id=88888):
    """Create a mock Discord thread."""
    thread = Mock(spec=discord.Thread)
    thread.id = thread_id
    thread.name = name
    thread.parent = parent_channel
    thread.guild = parent_channel.guild
    thread.owner_id = 67890
    thread.archived = False
    thread.locked = False
    thread.created_at = Mock()

    # Methods
    thread.send = AsyncMock()
    thread.edit = AsyncMock()
    thread.archive = AsyncMock()
    thread.unarchive = AsyncMock()

    return thread


def create_mock_reaction(emoji="👍", count=1):
    """Create a mock Discord reaction."""
    reaction = Mock()
    reaction.emoji = emoji
    reaction.count = count
    reaction.me = False
    return reaction


def create_admin_author(base_author):
    """Convert a mock author to have admin permissions."""
    base_author.guild_permissions.administrator = True
    return base_author


def assert_embed_sent(mock_ctx, title=None, description=None, color=None):
    """Assert that an embed was sent with specific properties."""
    assert mock_ctx.send.called, "Context.send was not called"

    call_args = mock_ctx.send.call_args
    if 'embed' in call_args[1]:
        embed = call_args[1]['embed']
        if title:
            assert embed.title == title, f"Expected title '{title}', got '{embed.title}'"
        if description:
            assert description in embed.description, \
                f"Expected description to contain '{description}', got '{embed.description}'"
        if color:
            assert embed.color == color, f"Expected color {color}, got {embed.color}"
        return embed
    else:
        raise AssertionError("No embed found in send call")


def assert_error_embed_sent(mock_ctx):
    """Assert that an error embed (red color) was sent."""
    assert mock_ctx.send.called
    call_args = mock_ctx.send.call_args
    embed = call_args[1]['embed']
    assert embed.color == 0xE02B2B, f"Expected error color 0xE02B2B, got {embed.color}"
    return embed
