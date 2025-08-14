"""Tests for file validation utilities."""

from app.utils.file_validation import get_safe_filename


class TestFileValidation:
    """Test file validation utilities."""

    def test_get_safe_filename_normal_filenames(self) -> None:
        """Test that normal filenames are preserved."""
        test_cases = [
            ("video.mp4", "video.mp4"),
            ("my_video.mp4", "my_video.mp4"),
            ("tennis-match.mp4", "tennis-match.mp4"),
            ("video_123.mp4", "video_123.mp4"),
        ]

        for original, expected in test_cases:
            result = get_safe_filename(original)
            assert result == expected, (
                f"Expected {expected}, got {result} for {original}"
            )

    def test_get_safe_filename_removes_dangerous_chars(self) -> None:
        """Test that dangerous characters are removed or replaced."""
        test_cases = [
            ("file with spaces.mp4", "file_with_spaces.mp4"),
            (
                "file!@#$%^&*().mp4",
                "file__________.mp4",
            ),  # Each special char becomes underscore
            ("file[].mp4", "file__.mp4"),
            ("file{}.mp4", "file__.mp4"),
            ("file().mp4", "file__.mp4"),
        ]

        for original, expected in test_cases:
            result = get_safe_filename(original)
            assert result == expected, (
                f"Expected {expected}, got {result} for {original}"
            )

    def test_get_safe_filename_removes_control_chars(self) -> None:
        """Test that control characters are removed."""
        # Test CR/LF injection attempt
        malicious_filename = "innocent.mp4\r\nSet-Cookie: session=stolen\r\n\r\n"
        result = get_safe_filename(malicious_filename)

        # Should remove control characters but keep the text (replacing unsafe chars with underscores)
        assert "\r" not in result
        assert "\n" not in result
        assert result == "innocent.mp4Set-Cookie__session_stolen"

    def test_get_safe_filename_removes_path_traversal(self) -> None:
        """Test that path traversal attempts are neutralized."""
        test_cases = [
            ("../../../etc/passwd", "passwd"),  # Only the filename part remains
            (
                "..\\..\\..\\windows\\system32\\config",
                "_._._windows_system32_config",
            ),  # Backslashes become underscores
            ("/etc/passwd", "passwd"),  # Only the filename part remains
            (
                "C:\\Windows\\System32\\config",
                "C__Windows_System32_config",
            ),  # Backslashes become underscores
        ]

        for original, expected in test_cases:
            result = get_safe_filename(original)
            assert result == expected, (
                f"Expected {expected}, got {result} for {original}"
            )

    def test_get_safe_filename_handles_unicode(self) -> None:
        """Test that Unicode characters are normalized."""
        test_cases = [
            ("vidéo.mp4", "vid_o.mp4"),  # Unicode chars become underscores
            ("file\u0000name.mp4", "filename.mp4"),  # Null byte removed
            ("file\u0001name.mp4", "filename.mp4"),  # Control char removed
        ]

        for original, expected in test_cases:
            result = get_safe_filename(original)
            assert result == expected, (
                f"Expected {expected}, got {result} for {original}"
            )

    def test_get_safe_filename_handles_empty_and_dots(self) -> None:
        """Test that empty filenames and dot-only filenames get fallback names."""
        # Empty filename should get random fallback
        result = get_safe_filename("")
        assert result.startswith("upload_")
        assert len(result) == 23  # "upload_" + 16 hex chars

        # Dot-only filename should get random fallback
        result = get_safe_filename(".")
        assert result.startswith("upload_")
        assert len(result) == 23

        # Multiple dots should be collapsed
        result = get_safe_filename("file..name.mp4")
        assert result == "file.name.mp4"

    def test_get_safe_filename_removes_leading_trailing_dots(self) -> None:
        """Test that leading and trailing dots are removed."""
        test_cases = [
            (".file.mp4", "file.mp4"),
            ("file.mp4.", "file.mp4"),
            ("..file.mp4..", "file.mp4"),
            ("   file.mp4   ", "___file.mp4___"),  # Spaces become underscores
        ]

        for original, expected in test_cases:
            result = get_safe_filename(original)
            assert result == expected, (
                f"Expected {expected}, got {result} for {original}"
            )

    def test_get_safe_filename_url_encoded_attack(self) -> None:
        """Test that URL-encoded attack attempts are neutralized."""
        # URL-encoded CR/LF
        malicious_filename = "file%0d%0aSet-Cookie:%20evil=value%0d%0a%0d%0a.mp4"
        result = get_safe_filename(malicious_filename)

        # Should remove the encoded control characters but keep the text
        assert "%" not in result
        assert result == "file_0d_0aSet-Cookie__20evil_value_0d_0a_0d_0a.mp4"
