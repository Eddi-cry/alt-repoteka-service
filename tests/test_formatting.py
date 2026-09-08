"""
Tests for formatting utilities.
"""

import pytest

from src.utils.formatting import format_evr


class TestFormatEVR:
    """Tests for EVR formatting."""

    def test_none_epoch(self):
        assert format_evr(None, "1.0", "alt1") == "1.0-alt1"

    def test_zero_epoch(self):
        assert format_evr(0, "1.0", "alt1") == "1.0-alt1"

    def test_positive_epoch(self):
        assert format_evr(1, "1.0", "alt1") == "1:1.0-alt1"
        assert format_evr(2, "8.21.0", "alt1") == "2:8.21.0-alt1"

    def test_real_world_examples(self):
        # curl package
        assert format_evr(0, "8.21.0", "alt1") == "8.21.0-alt1"
        assert format_evr(0, "8.12.0", "alt2") == "8.12.0-alt2"

        # Package with epoch
        assert format_evr(1, "3.0.8", "alt1") == "1:3.0.8-alt1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
