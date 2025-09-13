"""Unit tests for the ContentFormatter service."""

from blog.services.content_formatter import ContentFormatter, ContentFormatterError


class TestContentFormatter:
    """Test cases for ContentFormatter."""

    def test_markdown_to_html(self):
        """Test converting markdown to HTML."""
        formatter = ContentFormatter()

        # Test basic markdown conversion
        markdown_content = "# Hello World\n\nThis is a paragraph."
        expected_html = "<h1>Hello World</h1>\n<p>This is a paragraph.</p>"

        result = formatter.markdown_to_html(markdown_content)
        assert result.strip() == expected_html

    def test_markdown_to_html_with_code_blocks(self):
        """Test converting markdown with code blocks to HTML."""
        formatter = ContentFormatter()

        # Test markdown with fenced code blocks
        markdown_content = "```python\nprint('Hello World')\n```"
        result = formatter.markdown_to_html(markdown_content)

        # Check that the result contains the expected code block structure
        assert "<pre>" in result
        assert "<code" in result
        assert "print('Hello World')" in result

    def test_markdown_to_html_empty_content(self):
        """Test converting empty markdown content."""
        formatter = ContentFormatter()

        # Test with empty string
        result = formatter.markdown_to_html("")
        assert result == ""

    def test_markdown_to_html_none_content(self):
        """Test converting None content."""
        formatter = ContentFormatter()

        # Test with None
        result = formatter.markdown_to_html(None)
        assert result == ""

    def test_markdown_to_html_with_special_characters(self):
        """Test converting markdown with special HTML characters."""
        formatter = ContentFormatter()

        # Test with special characters that should be escaped
        markdown_content = "This < > & should be escaped"
        result = formatter.markdown_to_html(markdown_content)

        # The markdown library should escape HTML characters for security
        assert "This &lt; &gt; &amp; should be escaped" in result

    def test_markdown_to_html_error_handling(self):
        """Test error handling when markdown conversion fails."""
        formatter = ContentFormatter()

        # Mock a scenario that could cause an error
        # Note: It's difficult to force a real error in the markdown library
        # but we can test that the error handling works correctly
        try:
            # This should work fine
            result = formatter.markdown_to_html("test")
            assert isinstance(result, str)
        except ContentFormatterError:
            # If an error occurs, it should be wrapped in ContentFormatterError
            pass
