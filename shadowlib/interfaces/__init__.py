"""Overlay windows - bank, GE, shop, dialogue, etc."""

from shadowlib.client import client
from shadowlib.interfaces.bank import Bank, bank

# Lazy-loaded reverse lookup: group_id -> name
_interface_id_to_name: dict[int, str] | None = None


def _getInterfaceIdToNameMap() -> dict[int, str]:
    """
    Build and cache a reverse lookup map from interface group ID to name.

    Lazily loads the InterfaceID class and builds the map once.

    Returns:
        Dict mapping group ID (int) to interface name (str)
    """
    global _interface_id_to_name

    if _interface_id_to_name is not None:
        return _interface_id_to_name

    _interface_id_to_name = {}

    try:
        from shadowlib.generated.constants.interface_id import InterfaceID

        # Iterate over class attributes that are integers (group IDs)
        for name in dir(InterfaceID):
            if name.startswith("_") and not name.startswith("__"):
                # Handle names like _100GUIDE_EGGS_OVERLAY (start with underscore + digit)
                value = getattr(InterfaceID, name)
                if isinstance(value, int):
                    # Remove leading underscore for display
                    _interface_id_to_name[value] = name[1:]
            elif not name.startswith("_") and name.isupper():
                value = getattr(InterfaceID, name)
                if isinstance(value, int):
                    _interface_id_to_name[value] = name
    except ImportError:
        pass

    return _interface_id_to_name


def getInterfaceName(group_id: int) -> str | None:
    """
    Get the interface name for a group ID.

    Args:
        group_id: The interface group ID

    Returns:
        Interface name string or None if not found

    Example:
        >>> getInterfaceName(12)
        'BANKMAIN'
    """
    return _getInterfaceIdToNameMap().get(group_id)


class Interfaces:
    """
    Namespace for overlay interfaces - returns singleton instances.

    Example:
        from shadowlib.client import client

        client.interfaces.bank.depositAll()
        # Or directly:
        from shadowlib.interfaces.bank import bank
        bank.depositAll()
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def bank(self) -> Bank:
        """Get bank interface singleton."""
        return bank

    def getOpenInterfaces(self) -> list[int]:
        """
        Get a list of currently open interface IDs.

        Returns:
            List of open interface IDs

        Example:
            >>> from shadowlib.client import client
            >>> open_interfaces = client.interfaces.getOpenInterfaces()
            >>> print(open_interfaces)  # e.g., [12, 15, 162]
        """
        return list(client.cache.getOpenWidgets().keys())

    def getOpenInterfaceNames(self) -> list[str]:
        """
        Get a list of currently open interface names.

        Returns:
            List of open interface names (unknown IDs are formatted as "UNKNOWN_123")

        Example:
            >>> from shadowlib.client import client
            >>> open_interfaces = client.interfaces.getOpenInterfaceNames()
            >>> print(open_interfaces)  # e.g., ['BANKMAIN', 'BANKSIDE', 'TOPLEVEL']
        """
        names = []
        for group_id in self.getOpenInterfaces():
            name = getInterfaceName(group_id)
            if name:
                names.append(name)
            else:
                names.append(f"UNKNOWN_{group_id}")
        return names


# Module-level singleton instance
interfaces = Interfaces()


__all__ = ["Interfaces", "interfaces", "Bank", "bank", "getInterfaceName"]
