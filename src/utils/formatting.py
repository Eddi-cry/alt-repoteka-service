"""
Formatting utilities for package metadata.
"""

from typing import Optional


def format_evr(epoch: Optional[int], version: str, release: str) -> str:
    """
    Format EVR (Epoch-Version-Release) following RPM conventions.

    Epoch is shown only when it is greater than zero.

    Args:
        epoch: Package epoch (None or int)
        version: Package version string
        release: Package release string

    Returns:
        Formatted EVR string

    Examples:
        >>> format_evr(None, "1.0", "alt1")
        '1.0-alt1'
        >>> format_evr(0, "1.0", "alt1")
        '1.0-alt1'
        >>> format_evr(1, "1.0", "alt1")
        '1:1.0-alt1'
        >>> format_evr(2, "8.21.0", "alt1")
        '2:8.21.0-alt1'
    """
    # Normalize epoch: None is treated as 0
    epoch_val = int(epoch) if epoch is not None else 0

    # Show epoch only when it's greater than zero
    if epoch_val > 0:
        return f"{epoch_val}:{version}-{release}"
    else:
        return f"{version}-{release}"
