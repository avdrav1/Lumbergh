"""Unit tests for Claude response formatting."""
import pytest
from cogs.claude import Claude


@pytest.fixture
def claude_cog(mock_bot):
    """Create a Claude cog instance for testing."""
    return Claude(mock_bot)


class TestFormatForDiscord:
    """Tests for _format_for_discord function."""

    def test_simple_text(self, claude_cog):
        """Test formatting simple text without special characters."""
        text = "This is a simple response."
        result = claude_cog._format_for_discord(text)
        assert result == "This is a simple response."

    def test_bullet_points_with_dash(self, claude_cog):
        """Test formatting bullet points with dashes."""
        text = "Here are some points:\n- Point 1\n- Point 2\n- Point 3"
        result = claude_cog._format_for_discord(text)

        # Bullet points should be indented with 2 spaces
        expected = "Here are some points:\n  - Point 1\n  - Point 2\n  - Point 3"
        assert result == expected

    def test_bullet_points_with_asterisk(self, claude_cog):
        """Test formatting bullet points with asterisks."""
        text = "Points:\n* First\n* Second\n* Third"
        result = claude_cog._format_for_discord(text)

        expected = "Points:\n  * First\n  * Second\n  * Third"
        assert result == expected

    def test_bullet_points_with_bullet_character(self, claude_cog):
        """Test formatting bullet points with bullet character (•)."""
        text = "Items:\n• Item A\n• Item B"
        result = claude_cog._format_for_discord(text)

        expected = "Items:\n  • Item A\n  • Item B"
        assert result == expected

    def test_numbered_list(self, claude_cog):
        """Test formatting numbered lists."""
        text = "Steps:\n1. First step\n2. Second step\n3. Third step"
        result = claude_cog._format_for_discord(text)

        # Numbered lists should not be indented
        assert result == text

    def test_numbered_list_with_parenthesis(self, claude_cog):
        """Test formatting numbered lists with parenthesis."""
        text = "Steps:\n1) First step\n2) Second step"
        result = claude_cog._format_for_discord(text)

        # Numbered lists with parenthesis should not be indented
        assert result == text

    def test_mixed_lists(self, claude_cog):
        """Test formatting with both numbered and bullet lists."""
        text = "Instructions:\n1. First step\n- Sub-point A\n- Sub-point B\n2. Second step"
        result = claude_cog._format_for_discord(text)

        # Numbers should not be indented, bullets should be
        expected = "Instructions:\n1. First step\n  - Sub-point A\n  - Sub-point B\n2. Second step"
        assert result == expected

    def test_empty_lines(self, claude_cog):
        """Test formatting with empty lines."""
        text = "Paragraph 1\n\nParagraph 2\n\n- Bullet"
        result = claude_cog._format_for_discord(text)

        expected = "Paragraph 1\n\nParagraph 2\n\n  - Bullet"
        assert result == expected

    def test_indented_bullets_already(self, claude_cog):
        """Test that already indented bullets get additional indentation."""
        text = "  - Already indented"
        result = claude_cog._format_for_discord(text)

        # Should add 2 more spaces
        assert result == "  - Already indented"

    def test_bullets_with_leading_whitespace(self, claude_cog):
        """Test bullets with various amounts of leading whitespace."""
        text = "- Normal\n  - Indented once\n    - Indented twice"
        result = claude_cog._format_for_discord(text)

        # All bullets should get the 2-space prefix
        expected = "  - Normal\n  - Indented once\n  - Indented twice"
        assert result == expected

    def test_code_blocks(self, claude_cog):
        """Test formatting with code block markers."""
        text = "```python\nprint('hello')\n```"
        result = claude_cog._format_for_discord(text)

        # Code blocks should be preserved as-is
        assert result == text

    def test_multiline_with_various_elements(self, claude_cog):
        """Test complex formatting with multiple element types."""
        text = """Here's my response:

1. First, do this
2. Then, do that

Some bullet points:
- Point A
- Point B

And a conclusion."""

        result = claude_cog._format_for_discord(text)

        expected = """Here's my response:

1. First, do this
2. Then, do that

Some bullet points:
  - Point A
  - Point B

And a conclusion."""

        assert result == expected

    def test_single_digit_numbers_only(self, claude_cog):
        """Test that only proper numbered lists are detected."""
        text = "Version 1.5 is great"
        result = claude_cog._format_for_discord(text)

        # "1.5" should not be treated as a numbered list
        assert result == text

    def test_numbers_without_space(self, claude_cog):
        """Test numbers without space after period."""
        text = "1.First item\n2.Second item"
        result = claude_cog._format_for_discord(text)

        # These should NOT be treated as numbered lists (no space)
        assert result == text

    def test_bullet_at_start_of_line_only(self, claude_cog):
        """Test that bullets in middle of line are not formatted."""
        text = "This is - not a bullet\nBut this is:\n- A bullet"
        result = claude_cog._format_for_discord(text)

        expected = "This is - not a bullet\nBut this is:\n  - A bullet"
        assert result == expected

    def test_large_numbered_list(self, claude_cog):
        """Test numbered lists with double-digit numbers."""
        text = "10. Tenth item\n11. Eleventh item\n99. Last item"
        result = claude_cog._format_for_discord(text)

        # Multi-digit numbers should also work
        assert result == text

    def test_nested_structure(self, claude_cog):
        """Test deeply nested list structure."""
        text = """Main points:
1. First level
- Second level dash
- Another second level
2. Back to first level
- More second level"""

        result = claude_cog._format_for_discord(text)

        expected = """Main points:
1. First level
  - Second level dash
  - Another second level
2. Back to first level
  - More second level"""

        assert result == expected

    def test_empty_string(self, claude_cog):
        """Test formatting empty string."""
        result = claude_cog._format_for_discord("")
        assert result == ""

    def test_only_whitespace(self, claude_cog):
        """Test formatting string with only whitespace."""
        text = "   \n  \n   "
        result = claude_cog._format_for_discord(text)
        # Should preserve whitespace structure
        assert result == text

    def test_unicode_bullets(self, claude_cog):
        """Test various unicode bullet characters."""
        text = "• Bullet 1\n▪ Bullet 2\n‣ Bullet 3"
        result = claude_cog._format_for_discord(text)

        # Only • is specifically handled
        expected = "  • Bullet 1\n▪ Bullet 2\n‣ Bullet 3"
        assert result == expected
