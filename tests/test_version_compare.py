"""
Tests for version comparison utilities.

These tests verify RPM version comparison semantics:
- Epoch comparison takes precedence
- Numeric segments > alphabetic segments
- Proper handling of mixed types
- Edge cases: empty versions, missing epochs, etc.
"""

import pytest

from src.utils.version_compare import _compare_segment, _parse_version, compare_evr


class TestParseVersion:
    """Tests for version string parsing."""

    def test_simple_numeric_version(self):
        assert _parse_version("1.2.3") == [1, ".", 2, ".", 3]

    def test_version_with_letters(self):
        assert _parse_version("1alpha2") == [1, "alpha", 2]

    def test_version_with_rc(self):
        result = _parse_version("2.0rc1")
        assert 2 in result
        assert "rc" in result
        assert 1 in result

    def test_empty_version(self):
        assert _parse_version("") == []

    def test_complex_version(self):
        result = _parse_version("1.2.3beta4")
        assert 1 in result and 2 in result and 3 in result
        assert "beta" in result
        assert 4 in result


class TestCompareSegment:
    """Tests for individual segment comparison."""

    def test_two_integers(self):
        assert _compare_segment(1, 2) == -1
        assert _compare_segment(2, 1) == 1
        assert _compare_segment(5, 5) == 0

    def test_two_strings(self):
        assert _compare_segment("alpha", "beta") == -1
        assert _compare_segment("beta", "alpha") == 1
        assert _compare_segment("rc", "rc") == 0

    def test_int_vs_string_int_wins(self):
        # Numbers are always "newer" than strings in RPM
        assert _compare_segment(1, "alpha") == 1
        assert _compare_segment("alpha", 1) == -1

    def test_zero_vs_string(self):
        assert _compare_segment(0, "rc") == 1
        assert _compare_segment("rc", 0) == -1


class TestCompareEVR:
    """Tests for full EVR comparison."""

    # === Epoch tests ===
    def test_different_epochs(self):
        assert compare_evr(1, "1.0", "alt1", 0, "2.0", "alt1") == 1
        assert compare_evr(0, "2.0", "alt1", 1, "1.0", "alt1") == -1

    def test_none_epoch_treated_as_zero(self):
        assert compare_evr(None, "1.0", "alt1", 0, "1.0", "alt1") == 0
        assert compare_evr(0, "1.0", "alt1", None, "1.0", "alt1") == 0

    # === Version tests ===
    def test_simple_version_comparison(self):
        assert compare_evr(0, "1.0", "alt1", 0, "2.0", "alt1") == -1
        assert compare_evr(0, "2.0", "alt1", 0, "1.0", "alt1") == 1
        assert compare_evr(0, "1.5", "alt1", 0, "1.5", "alt1") == 0

    def test_multipart_version(self):
        assert compare_evr(0, "1.2.3", "alt1", 0, "1.2.4", "alt1") == -1
        assert compare_evr(0, "1.2.10", "alt1", 0, "1.2.9", "alt1") == 1

    def test_version_with_alpha_suffix(self):
        # "1.0" > "1.0alpha" because missing segment > empty
        # Actually, numbers > strings, so "1.0" (ends with number) > "1.0alpha"
        assert compare_evr(0, "1.0", "alt1", 0, "1.0alpha", "alt1") == 1
        assert compare_evr(0, "1.0alpha", "alt1", 0, "1.0", "alt1") == -1

    def test_version_alpha_vs_beta(self):
        assert compare_evr(0, "1.0alpha", "alt1", 0, "1.0beta", "alt1") == -1
        assert compare_evr(0, "1.0beta", "alt1", 0, "1.0alpha", "alt1") == 1

    def test_version_rc_vs_release(self):
        # "1.0" (numeric end) > "1.0rc1" (has letters)
        assert compare_evr(0, "1.0rc1", "alt1", 0, "1.0", "alt1") == -1

    # === Release tests ===
    def test_release_comparison(self):
        assert compare_evr(0, "1.0", "alt1", 0, "1.0", "alt2") == -1
        assert compare_evr(0, "1.0", "alt2", 0, "1.0", "alt1") == 1

    def test_release_with_numbers(self):
        assert compare_evr(0, "1.0", "alt10", 0, "1.0", "alt2") == 1
        assert compare_evr(0, "1.0", "alt2", 0, "1.0", "alt10") == -1

    # === Real-world examples ===
    def test_curl_versions(self):
        # curl 8.21.0-alt1 > curl 8.12.0-alt2
        assert compare_evr(0, "8.21.0", "alt1", 0, "8.12.0", "alt2") == 1

    def test_openssl_versions(self):
        # openssl 3.0.8-alt1 > openssl 3.0.7-alt2
        assert compare_evr(0, "3.0.8", "alt1", 0, "3.0.7", "alt2") == 1

    def test_kernel_versions(self):
        # kernel 6.1.10-alt1 > kernel 6.1.9-alt1
        assert compare_evr(0, "6.1.10", "alt1", 0, "6.1.9", "alt1") == 1

    # === Edge cases ===
    def test_identical_evr(self):
        assert compare_evr(0, "1.0", "alt1", 0, "1.0", "alt1") == 0
        assert compare_evr(None, "1.0", "alt1", None, "1.0", "alt1") == 0

    def test_empty_version_strings(self):
        # This is a pathological case, but should not crash
        result = compare_evr(0, "", "alt1", 0, "", "alt1")
        assert result == 0

    def test_very_long_version(self):
        long_ver = "1.2.3.4.5.6.7.8.9.10"
        assert compare_evr(0, long_ver, "alt1", 0, long_ver, "alt1") == 0


class TestRegressions:
    """Tests for previously reported bugs."""

    def test_int_str_comparison_no_crash(self):
        # This used to crash with TypeError in Python 3
        result = compare_evr(0, "1alpha", "alt1", 0, "1", "alt1")
        assert result == -1  # "1alpha" < "1" because alpha < nothing

    def test_epoch_zero_vs_none(self):
        # epoch=0 and epoch=None should be treated identically
        assert compare_evr(0, "1.0", "alt1", None, "1.0", "alt1") == 0
        assert compare_evr(None, "1.0", "alt1", 0, "1.0", "alt1") == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
