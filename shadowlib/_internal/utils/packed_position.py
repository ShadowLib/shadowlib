"""
Packed position utilities for OSRS coordinates.

Positions are stored as packed 32-bit integers:
- Bits [31-30]: Plane (2 bits, 0-3)
- Bits [29-15]: X coordinate (15 bits, 0-32767)
- Bits [14-0]: Y coordinate (15 bits, 0-32767)
"""


def pack_position(x: int, y: int, plane: int) -> int:
    """
    Pack (x, y, plane) into a 32-bit unsigned integer.

    Args:
        x: X coordinate (0-32767)
        y: Y coordinate (0-32767)
        plane: Plane level (0-3)

    Returns:
        Packed position as unsigned 32-bit integer

    Example:
        >>> pack_position(3200, 3200, 0)
        419430400
    """
    return (plane << 30) | (x << 15) | y


def pack_position_signed(x: int, y: int, plane: int) -> int:
    """
    Pack (x, y, plane) into a 32-bit SIGNED integer for SQLite compatibility.

    Planes 2-3 will result in negative numbers due to sign bit.

    Args:
        x: X coordinate (0-32767)
        y: Y coordinate (0-32767)
        plane: Plane level (0-3)

    Returns:
        Packed position as signed 32-bit integer

    Example:
        >>> pack_position_signed(3200, 3200, 0)
        419430400
        >>> pack_position_signed(3200, 3200, 2)
        -1207959552  # Negative due to plane 2 setting bit 30
    """
    packed = pack_position(x, y, plane)
    # Convert to signed 32-bit
    if packed >= 2**31:
        return packed - 2**32
    return packed


def unpack_position(packed: int) -> tuple[int, int, int]:
    """
    Unpack a 32-bit integer into (x, y, plane).

    Args:
        packed: Packed position (signed or unsigned)

    Returns:
        Tuple of (x, y, plane)

    Example:
        >>> unpack_position(419430400)
        (3200, 3200, 0)
        >>> unpack_position(-1207959552)
        (3200, 3200, 2)
    """
    # Convert signed to unsigned for bit operations
    if packed < 0:
        packed = packed + 2**32

    plane = (packed >> 30) & 0x3  # 2 bits
    x = (packed >> 15) & 0x7FFF  # 15 bits
    y = packed & 0x7FFF  # 15 bits

    return (x, y, plane)
