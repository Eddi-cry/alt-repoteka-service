"""
RPM version comparison utilities.

This module implements version comparison following RPM semantics:
- Epochs are compared numerically first
- Versions and releases are split into alternating sequences of digits and letters
- Numeric segments are compared as integers
- Alphabetic segments are compared lexicographically
- Numbers are always "newer" than strings (1 > alpha)
- Missing segments are considered less than present ones
"""

import re
from typing import List, Optional, Union


def _parse_version(version_str: str) -> List[Union[int, str]]:
    """
    Parse a version or release string into alternating numeric and alphabetic segments.

    Examples:
        "1.2.3" -> [1, '.', 2, '.', 3]
        "1alpha2" -> [1, 'alpha', 2]
        "2.0rc1" -> [2, '.', 0, 'rc', 1]
    """
    if not version_str:
        return []

    parts: List[Union[int, str]] = []
    segments = re.split(r"(\d+)", version_str)

    for segment in segments:
        if not segment:
            continue
        if segment.isdigit():
            parts.append(int(segment))
        else:
            parts.append(segment)

    return parts


def _compare_segment(a: Union[int, str], b: Union[int, str]) -> int:
    """
    Compare two version segments following RPM rules:
    - If both are ints: numeric comparison
    - If both are strings: lexicographic comparison
    - If types differ: numbers are always "newer" (int > str)

    Returns:
        -1 if a < b
         0 if a == b
         1 if a > b
    """
    # Handle type mismatches: numbers > strings in RPM semantics
    if isinstance(a, int) and isinstance(b, str):
        return 1  # Numbers are always newer than strings
    if isinstance(a, str) and isinstance(b, int):
        return -1  # Strings are always older than numbers

    # Same types: direct comparison
    if a < b:  # type: ignore[operator]
        return -1
    elif a > b:  # type: ignore[operator]
        return 1
    else:
        return 0


def _compare_parts(parts1: List[Union[int, str]], parts2: List[Union[int, str]]) -> int:
    """
    Compare two lists of version parts segment by segment.

    RPM semantics for missing segments:
    - Missing numeric segment < present numeric segment (1.0 < 1.0.1)
    - Missing string segment > present string segment (1.0 > 1.0alpha)

    This makes sense because string suffixes like "alpha", "beta", "rc"
    represent pre-release versions, which are older than the final release.

    Returns:
        -1 if parts1 < parts2
         0 if parts1 == parts2
         1 if parts1 > parts2
    """
    max_len = max(len(parts1), len(parts2))

    for i in range(max_len):
        # Check if segments exist
        has_seg1 = i < len(parts1)
        has_seg2 = i < len(parts2)

        # Both missing - continue
        if not has_seg1 and not has_seg2:
            continue

        # One missing - handle based on the type of the present segment
        if not has_seg1:
            # parts1 is shorter
            seg2 = parts2[i]
            # If the present segment is a string, the missing one is "newer"
            # (1.0 > 1.0alpha because alpha is a pre-release marker)
            if isinstance(seg2, str):
                return 1
            # If the present segment is numeric, the missing one is "older"
            # (1.0 < 1.0.1 because .1 is an additional version)
            else:
                return -1

        if not has_seg2:
            # parts2 is shorter
            seg1 = parts1[i]
            # If the present segment is a string, the missing one is "newer"
            if isinstance(seg1, str):
                return -1
            # If the present segment is numeric, the missing one is "older"
            else:
                return 1

        # Both segments present - compare normally
        result = _compare_segment(parts1[i], parts2[i])
        if result != 0:
            return result

    return 0


def compare_evr(
    epoch1: Optional[int], ver1: str, rel1: str, epoch2: Optional[int], ver2: str, rel2: str
) -> int:
    """
    Compare two EVR (Epoch-Version-Release) tuples following RPM semantics.

    Args:
        epoch1: First epoch (None or int)
        ver1: First version string
        rel1: First release string
        epoch2: Second epoch (None or int)
        ver2: Second version string
        rel2: Second release string

    Returns:
        -1 if EVR1 < EVR2
         0 if EVR1 == EVR2
         1 if EVR1 > EVR2

    Examples:
        >>> compare_evr(0, "1.0", "alt1", 0, "1.0", "alt2")
        -1
        >>> compare_evr(1, "1.0", "alt1", 0, "2.0", "alt1")
        1
        >>> compare_evr(None, "1.0alpha", "alt1", None, "1.0", "alt1")
        -1
    """
    # Normalize epochs: None or 0 are treated as 0
    e1 = int(epoch1) if epoch1 is not None else 0
    e2 = int(epoch2) if epoch2 is not None else 0

    # Compare epochs first
    if e1 != e2:
        return -1 if e1 < e2 else 1

    # Parse and compare versions
    v1_parts = _parse_version(ver1)
    v2_parts = _parse_version(ver2)
    result = _compare_parts(v1_parts, v2_parts)
    if result != 0:
        return result

    # Parse and compare releases
    r1_parts = _parse_version(rel1)
    r2_parts = _parse_version(rel2)
    return _compare_parts(r1_parts, r2_parts)
