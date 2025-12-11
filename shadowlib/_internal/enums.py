#!/usr/bin/env python3
"""
RuneLite Enum Classes - Auto-generated from scraped API data
Provides type-safe enum objects that prevent int/enum confusion
"""

import json
from typing import Any, Dict, Type


class EnumValue:
    """
    Represents a RuneLite enum value with type information.
    This is NOT an integer - it's a distinct type that carries enum metadata.
    """

    def __init__(self, enum_name: str, value_name: str, ordinal: int):
        self._enum_name = enum_name
        self._value_name = value_name
        self._ordinal = ordinal

    def __repr__(self):
        return f"{self._enum_name}.{self._value_name}"

    def __str__(self):
        return self._value_name

    def __int__(self):
        """Allow conversion to int when explicitly needed"""
        return self._ordinal

    def __eq__(self, other):
        if isinstance(other, EnumValue):
            return self._enum_name == other._enum_name and self._ordinal == other._ordinal
        return False

    def __hash__(self):
        return hash((self._enum_name, self._ordinal))

    @property
    def ordinal(self):
        """Get the ordinal value"""
        return self._ordinal

    @property
    def name(self):
        """Get the value name"""
        return self._value_name

    @property
    def enumType(self):
        """Get the enum type name"""
        return self._enum_name


class EnumMeta(type):
    """
    Metaclass for enum classes to provide iteration and lookup capabilities
    """

    def __iter__(cls):
        """Allow iterating over enum values"""
        for name in cls._values:
            yield getattr(cls, name)

    def __len__(cls):
        """Get number of enum values"""
        return len(cls._values)

    def __contains__(cls, item):
        """Check if value exists in enum"""
        if isinstance(item, str):
            return item in cls._values
        elif isinstance(item, EnumValue):
            return item._enum_name == cls.__name__ and item._value_name in cls._values
        elif isinstance(item, int):
            return 0 <= item < len(cls._values)
        return False

    def __getitem__(cls, key):
        """Allow lookup by ordinal or name"""
        if isinstance(key, int):
            # Lookup by ordinal
            for name in cls._values:
                val = getattr(cls, name)
                if val._ordinal == key:
                    return val
            raise KeyError(f"No {cls.__name__} with ordinal {key}")
        elif isinstance(key, str):
            # Lookup by name
            if hasattr(cls, key):
                return getattr(cls, key)
            # Try uppercase
            key_upper = key.upper()
            if hasattr(cls, key_upper):
                return getattr(cls, key_upper)
            raise KeyError(f"No {cls.__name__} named {key}")
        else:
            raise TypeError(f"Invalid key type: {type(key)}")


def createEnumClass(enum_name: str, values: list, value_map: Dict | None = None) -> Type:
    """
    Create a single enum class from scraped data
    """
    # Build class attributes
    class_attrs = {
        "__module__": "runelite_enums",
        "__qualname__": enum_name,
        "_enum_name": enum_name,
        "_values": [],
        "_ordinal_map": {},
        "_name_map": {},
    }

    # Add class methods
    class_attrs["from_ordinal"] = classmethod(lambda cls, ordinal: cls._ordinal_map.get(ordinal))
    class_attrs["from_name"] = classmethod(
        lambda cls, name: cls._name_map.get(name.upper() if name else None)
    )
    class_attrs["values"] = classmethod(lambda cls: [getattr(cls, name) for name in cls._values])
    class_attrs["names"] = classmethod(lambda cls: cls._values[:])

    # Create EnumValue for each enum constant
    for ordinal, value_name in enumerate(values):
        if not value_name or value_name.startswith("//"):
            continue  # Skip empty or comment lines

        # Create the EnumValue instance
        enum_value = EnumValue(enum_name, value_name, ordinal)

        # Add to class
        class_attrs[value_name] = enum_value
        class_attrs["_values"].append(value_name)
        class_attrs["_ordinal_map"][ordinal] = enum_value
        class_attrs["_name_map"][value_name.upper()] = enum_value

    # Create the enum class with metaclass
    enum_class = EnumMeta(enum_name, (), class_attrs)

    return enum_class


def generateAllEnumClasses(api_data: Dict) -> Dict[str, Type]:
    """
    Generate all enum classes from the scraped API data
    """
    enum_classes = {}

    # Check if we have enum data
    if "enums" not in api_data:
        print("⚠️  No enum data found in API data")
        return enum_classes

    # Generate each enum class
    for enum_name, enum_info in api_data["enums"].items():
        # Get values list
        if isinstance(enum_info, dict):
            values = enum_info.get("values", [])
            value_map = enum_info.get("value_map", {})
        else:
            # Handle old format where enum_info might be a list
            values = enum_info if isinstance(enum_info, list) else []
            value_map = {}

        if values:
            enum_class = createEnumClass(enum_name, values, value_map)
            enum_classes[enum_name] = enum_class

    return enum_classes


def loadEnumsFromFile(api_data_file: str | None = None) -> Dict[str, Type]:
    """
    Load enum classes from the API data file
    """
    # Default to the standard location in data/api directory
    if api_data_file is None:
        # Look for data file in cache directory
        from .cache_manager import getCacheManager

        cache_manager = getCacheManager()
        api_data_file = str(cache_manager.getDataPath("api") / "runelite_api_data.json")

    # Load the API data
    try:
        with open(api_data_file) as f:
            api_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ API data file not found: {api_data_file}")
        print("   Run 'python3 runelite_api_scraper.py' to generate it")
        return {}
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing API data: {e}")
        return {}

    # Generate enum classes
    enum_classes = generateAllEnumClasses(api_data)

    print(f"✅ Generated {len(enum_classes)} enum classes from API data")

    return enum_classes


# Auto-generate enums on module import
_enum_classes = loadEnumsFromFile()

# Export all enum classes to module namespace
for _name, _cls in _enum_classes.items():
    globals()[_name] = _cls

# Export commonly used enums for easy access
__all__ = [
    "EnumValue",
    "EnumMeta",
    "create_enum_class",
    "generate_all_enum_classes",
    "load_enums_from_file",
] + list(_enum_classes.keys())


# Provide convenient access to common enums (if they exist)
def getEnum(enum_name: str) -> Type | None:
    """Get an enum class by name"""
    return _enum_classes.get(enum_name)


def listAllEnums() -> list:
    """List all available enum names"""
    return sorted(_enum_classes.keys())


def enumInfo(enum_name: str) -> Dict[str, Any]:
    """Get information about an enum"""
    enum_class = _enum_classes.get(enum_name)
    if not enum_class:
        return {}

    return {
        "name": enum_name,
        "values": enum_class._values,
        "count": len(enum_class._values),
        "ordinals": {v: getattr(enum_class, v)._ordinal for v in enum_class._values},
    }
