#!/usr/bin/env python3
"""
Local RuneLite API Scraper
Processes locally downloaded RuneLite API files to generate comprehensive API database
"""

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class MethodInfo:
    """Simplified method info"""

    name: str
    signature: str
    return_type: str
    generic_return_type: Optional[str] = None  # Full generic type like "List<Player>"
    params: List[str] = field(default_factory=list)


@dataclass
class EnumInfo:
    """Enum with values"""

    name: str
    values: List[str] = field(default_factory=list)
    value_map: Dict[str, Any] = field(default_factory=dict)


class EfficientRuneLiteScraper:
    """
    Local scraper for RuneLite API files
    """

    def __init__(self):
        self.methods: Dict[
            str, List[Tuple[str, str, Optional[str]]]
        ] = {}  # method_name -> [(class, signature, generic_type)]
        self.enums: Dict[str, EnumInfo] = {}
        self.classes: Set[str] = set()
        self.constants: Dict[str, Dict[str, Any]] = {}  # class -> {constant: value}
        self.inheritance: Dict[
            str, Dict[str, Any]
        ] = {}  # class -> {extends: str, implements: List[str]}
        self.class_packages: Dict[str, str] = {}  # class_name -> full_package_path
        self.all_class_files: List[
            Tuple[Path, str, str]
        ] = []  # [(file_path, class_name, package_path)]
        self.interface_ids: Dict[str, Any] = {}  # InterfaceID structure with nested classes

        # JNI type mappings
        self.type_map = {
            "int": "I",
            "long": "J",
            "boolean": "Z",
            "byte": "B",
            "char": "C",
            "short": "S",
            "float": "F",
            "double": "D",
            "void": "V",
            "String": "Ljava/lang/String;",
            "Object": "Ljava/lang/Object;",
        }

    def scrapeLocalDirectory(self, api_path: str):
        """
        Scrape all Java files from local RuneLite API directory
        """
        print("🚀 Local file scraping starting...")
        print(f"📁 Scanning directory: {api_path}")
        start_time = time.time()

        api_path = Path(api_path)

        # Get all Java files
        java_files = list(api_path.rglob("*.java"))
        print(f"📊 Found {len(java_files)} Java files to process")

        # PASS 1: Build class-to-package mapping first
        print("  Pass 1: Building class-to-package mapping...")
        for file_path in java_files:
            class_name = file_path.stem  # filename without extension

            # Determine the package path from file location
            rel_path = file_path.relative_to(api_path)
            package_parts = list(rel_path.parts[:-1])  # Remove filename

            # Build full package path (e.g., "net/runelite/api/widgets")
            if package_parts:
                package_path = "net/runelite/api/" + "/".join(package_parts)
            else:
                package_path = "net/runelite/api"

            # Store ALL files, even duplicates
            self.all_class_files.append((file_path, class_name, package_path))

            # For simple lookups, prefer base package for duplicates
            if class_name not in self.class_packages:
                self.class_packages[class_name] = package_path
            elif package_path == "net/runelite/api":
                # Base package takes precedence for duplicates
                self.class_packages[class_name] = package_path

        print(f"  Built mappings for {len(self.class_packages)} classes")

        # PASS 2: Process files with complete package knowledge
        print("  Pass 2: Processing files with complete package knowledge...")
        for idx, (file_path, class_name, package_path) in enumerate(self.all_class_files, 1):
            try:
                # Read the file content
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()

                # For duplicates, use full path as key
                if sum(1 for _, cn, _ in self.all_class_files if cn == class_name) > 1:
                    # Duplicate name - use package-qualified name
                    full_class_key = f"{package_path.replace('/', '.')}.{class_name}"
                else:
                    full_class_key = class_name

                # Determine file type and parse
                if "enum " + class_name in content:
                    self._parseEnum(content, class_name, package_path, full_class_key)
                else:
                    self._parseClass(content, class_name, package_path, full_class_key)

                self.classes.add(full_class_key)

                # Progress indicator
                if idx % 50 == 0:
                    print(f"  Progress: {idx}/{len(java_files)} files processed...")

            except Exception as e:
                print(f"  ❌ Error processing {file_path.name}: {e}")

        elapsed = time.time() - start_time
        print(f"✅ Processed all {len(java_files)} files in {elapsed:.1f} seconds")
        self._printSummary(elapsed)

        # Parse InterfaceID file if it exists
        self._parseInterfaceIds(api_path)

        # Parse VarClientID file if it exists
        self._parseVarclientIds(api_path)

        # Parse gameval ItemID file if it exists (comprehensive item IDs)
        self._parseItemIds(api_path)

    def _parseInterfaceIds(self, api_path: Path):
        """
        Parse the InterfaceID.java file from gameval directory.
        This file contains widget group IDs and nested classes with packed widget IDs.
        """
        interface_id_path = api_path / "gameval" / "InterfaceID.java"

        if not interface_id_path.exists():
            print("\n⚠️  InterfaceID.java not found, skipping interface ID parsing")
            return

        print("\n🎨 Parsing InterfaceID.java for widget constants...")

        try:
            with open(interface_id_path, encoding="utf-8") as f:
                content = f.read()

            # Structure: { 'groups': { 'GROUP_NAME': id }, 'nested': { 'ClassName': { 'CONST': value } } }
            self.interface_ids = {
                "groups": {},  # Top-level group IDs (e.g., SEASLUG_BOAT_TRAVEL = 461)
                "nested": {},  # Nested classes with packed IDs (e.g., SeaslugBoatTravel.SEASLUG_BOAT_WITCHAVEN_TO_FISHPIER)
            }

            # Parse top-level constants (group IDs)
            # Pattern: public static final int NAME = value;
            top_level_pattern = (
                r"^\s*public\s+static\s+final\s+int\s+([A-Z_][A-Z0-9_]*)\s*=\s*([0-9]+);"
            )
            for match in re.finditer(top_level_pattern, content, re.MULTILINE):
                const_name = match.group(1)
                const_value = int(match.group(2))
                self.interface_ids["groups"][const_name] = const_value

            # Parse nested static classes
            # Pattern: public static final class ClassName { ... }
            nested_class_pattern = r"public\s+static\s+final\s+class\s+([A-Za-z0-9_]+)\s*\{([^}]+(?:\}(?![\s]*public\s+static\s+final\s+class)[^}]*)*)\}"

            for match in re.finditer(nested_class_pattern, content, re.DOTALL):
                class_name = match.group(1)
                class_body = match.group(2)

                # Parse constants within the nested class
                # Pattern: public static final int NAME = 0x01cd_0002;
                nested_constants = {}
                const_pattern = r"public\s+static\s+final\s+int\s+([A-Z_][A-Z0-9_]*)\s*=\s*(0x[0-9a-fA-F_]+|[0-9]+);"

                for const_match in re.finditer(const_pattern, class_body):
                    const_name = const_match.group(1)
                    const_value_str = const_match.group(2).replace(
                        "_", ""
                    )  # Remove underscores from hex

                    # Parse as int (handles both hex and decimal)
                    if const_value_str.startswith("0x"):
                        const_value = int(const_value_str, 16)
                    else:
                        const_value = int(const_value_str)

                    nested_constants[const_name] = const_value

                if nested_constants:
                    self.interface_ids["nested"][class_name] = nested_constants

            print(f"   ✅ Found {len(self.interface_ids['groups'])} group IDs")
            print(f"   ✅ Found {len(self.interface_ids['nested'])} nested widget classes")
            total_widgets = sum(len(v) for v in self.interface_ids["nested"].values())
            print(f"   ✅ Total widget constants: {total_widgets}")

        except Exception as e:
            print(f"   ❌ Error parsing InterfaceID.java: {e}")
            import traceback

            traceback.print_exc()

    def _parseVarclientIds(self, api_path: Path):
        """
        Parse the VarClientID.java file from gameval directory.
        This file contains simple VarClient ID constants.
        """
        varclient_id_path = api_path / "gameval" / "VarClientID.java"

        if not varclient_id_path.exists():
            print("\n⚠️  VarClientID.java not found, skipping VarClientID parsing")
            return

        print("\n🎮 Parsing VarClientID.java for VarClient constants...")

        try:
            with open(varclient_id_path, encoding="utf-8") as f:
                content = f.read()

            # Parse constants: public static final int NAME = value;
            pattern = r"public\s+static\s+final\s+int\s+([A-Z_][A-Z0-9_]*)\s*=\s*([0-9]+);"

            varclient_constants = {}
            for match in re.finditer(pattern, content):
                const_name = match.group(1)
                const_value = int(match.group(2))
                varclient_constants[const_name] = const_value

            # Store in constants dictionary with a special key
            if "VarClientID" not in self.constants:
                self.constants["VarClientID"] = {}

            self.constants["VarClientID"] = varclient_constants

            print(f"   ✅ Found {len(varclient_constants)} VarClientID constants")

        except Exception as e:
            print(f"   ❌ Error parsing VarClientID.java: {e}")
            import traceback

            traceback.print_exc()

    def _parseItemIds(self, api_path: Path):
        """
        Parse the gameval ItemID.java file which includes nested Cert and Placeholder classes.
        This provides comprehensive item IDs including noted and placeholder variants.

        Note: Java's "Cert" class is mapped to Python's "Noted" class for clarity.
        """
        item_id_path = api_path / "gameval" / "ItemID.java"

        if not item_id_path.exists():
            print("\n⚠️  gameval ItemID.java not found, falling back to regular ItemID")
            return

        print("\n📦 Parsing gameval ItemID.java for comprehensive item constants...")

        try:
            with open(item_id_path, encoding="utf-8") as f:
                content = f.read()

            # Structure: { 'main': { 'DRAGON_SCIMITAR': 4587 }, 'Noted': { ... }, 'Placeholder': { ... } }
            item_ids = {
                "main": {},  # Top-level item IDs
                "Noted": {},  # Noted items
                "Placeholder": {},  # Placeholder items
            }

            # Parse top-level constants (main item IDs) up until first nested class
            # Split content to avoid matching nested class constants
            main_content = content
            nested_class_start = re.search(
                r"public\s+static\s+final\s+class\s+(Cert|Placeholder)", content
            )
            if nested_class_start:
                main_content = content[: nested_class_start.start()]

            # Pattern: public static final int NAME = value;
            top_level_pattern = (
                r"^\s*public\s+static\s+final\s+int\s+([A-Z_][A-Z0-9_]*)\s*=\s*([0-9]+);"
            )
            for match in re.finditer(top_level_pattern, main_content, re.MULTILINE):
                const_name = match.group(1)
                const_value = int(match.group(2))
                item_ids["main"][const_name] = const_value

            # Parse nested static classes (Cert and Placeholder)
            # Pattern: public static final class ClassName { ... }
            nested_class_pattern = r"public\s+static\s+final\s+class\s+(Cert|Placeholder)\s*\{(.*?)(?=\n\s*public\s+static\s+final\s+class|\n\s*\}[\s]*$)"

            for match in re.finditer(nested_class_pattern, content, re.DOTALL):
                class_name = match.group(1)
                class_body = match.group(2)

                # Map Java class name to Python class name (Cert -> Noted)
                python_class_name = "Noted" if class_name == "Cert" else class_name

                # Parse constants within the nested class
                const_pattern = (
                    r"public\s+static\s+final\s+int\s+([A-Z_][A-Z0-9_]*)\s*=\s*([0-9]+);"
                )

                for const_match in re.finditer(const_pattern, class_body):
                    const_name = const_match.group(1)
                    const_value = int(const_match.group(2))
                    item_ids[python_class_name][const_name] = const_value

            # Store as net.runelite.api.gameval.ItemID to distinguish from regular ItemID
            self.constants["net.runelite.api.gameval.ItemID"] = item_ids

            print(f"   ✅ Found {len(item_ids['main'])} main item IDs")
            print(f"   ✅ Found {len(item_ids['Noted'])} noted item IDs")
            print(f"   ✅ Found {len(item_ids['Placeholder'])} placeholder item IDs")
            total_items = sum(len(v) for v in item_ids.values())
            print(f"   ✅ Total item constants: {total_items:,}")

        except Exception as e:
            print(f"   ❌ Error parsing gameval ItemID.java: {e}")
            import traceback

            traceback.print_exc()

    def _parseClass(
        self,
        content: str,
        class_name: str,
        package_path: str = "net/runelite/api",
        storage_key: str = None,
    ):
        if storage_key is None:
            storage_key = class_name
        """
        Parse a class or interface file
        """
        # Check for Lombok annotations that generate getters
        has_lombok_value = "@Value" in content
        has_lombok_data = "@Data" in content
        has_lombok_getter = "@Getter" in content
        has_lombok_accessors = has_lombok_value or has_lombok_data or has_lombok_getter

        # Extract inheritance information
        inheritance_info = {}

        # Find class/interface declaration with extends and implements
        class_pattern = (
            r"(?:public\s+)?(?:abstract\s+)?(?:class|interface)\s+"
            + re.escape(class_name)
            + r"(?:<[^>]+>)?\s*(?:extends\s+([A-Za-z0-9_<>,\s]+))?\s*(?:implements\s+([A-Za-z0-9_<>,\s]+))?"
        )
        class_match = re.search(class_pattern, content)

        if class_match:
            extends = class_match.group(1)
            implements = class_match.group(2)

            if extends:
                # Clean up the extends class name
                extends = extends.strip()
                # Remove generics for cleaner name
                if "<" in extends:
                    extends = extends[: extends.index("<")]
                inheritance_info["extends"] = extends

            if implements:
                # Parse multiple interfaces
                interfaces = []
                for interface in implements.split(","):
                    interface = interface.strip()
                    # Remove generics
                    if "<" in interface:
                        interface = interface[: interface.index("<")]
                    interfaces.append(interface)
                inheritance_info["implements"] = interfaces

        # Determine if it's an interface
        if "interface " + class_name in content:
            inheritance_info["is_interface"] = True

        if inheritance_info:
            self.inheritance[storage_key] = inheritance_info

        # Extract static constants
        constants = {}
        const_pattern = r"static\s+final\s+(\w+)\s+([A-Z_][A-Z0-9_]*)\s*=\s*([^;]+);"
        for match in re.finditer(const_pattern, content):
            const_type, const_name, const_value = match.groups()
            const_value = const_value.strip()

            # Parse value based on type
            if const_type == "int":
                try:
                    if const_value.startswith("0x"):
                        constants[const_name] = int(const_value, 16)
                    elif const_value.isdigit() or (
                        const_value[0] == "-" and const_value[1:].isdigit()
                    ):
                        constants[const_name] = int(const_value)
                    else:
                        constants[const_name] = const_value
                except:
                    constants[const_name] = const_value
            elif (
                const_type == "String" and const_value.startswith('"') and const_value.endswith('"')
            ):
                constants[const_name] = const_value[1:-1]
            else:
                constants[const_name] = const_value

        if constants:
            self.constants[storage_key] = constants

        # Extract methods - improved regex
        method_pattern = r"""
            (?:^\s*|\n\s*)                           # Start of line
            (?:(?:public|protected|private)\s+)?     # Access modifier
            (?:static\s+)?(?:final\s+)?(?:default\s+)?(?:abstract\s+)?  # Other modifiers
            (?:synchronized\s+)?(?:native\s+)?
            (?:<[^>]+>\s+)?                          # Generic method
            ([A-Za-z0-9_\[\]<>,.\s]+?)\s+            # Return type
            ([a-z][a-zA-Z0-9_]*)\s*                  # Method name
            \(([^)]*)\)                               # Parameters
            (?:\s+throws\s+[^{;]+)?                  # Throws clause
            \s*[{;]                                   # Method body or semicolon
        """

        for match in re.finditer(method_pattern, content, re.VERBOSE | re.MULTILINE):
            return_type = match.group(1).strip()
            method_name = match.group(2).strip()
            params = match.group(3).strip()

            # Skip constructors and invalid matches
            if method_name == class_name or not return_type or " " in method_name:
                continue

            # Store the full generic return type (e.g., "List<Player>", "Tile[][]")
            generic_return_type = return_type

            # Build JNI signature (strips generics)
            signature = self._buildSignature(params, return_type)

            # Store method with generic type info
            if method_name not in self.methods:
                self.methods[method_name] = []

            self.methods[method_name].append(
                (f"{package_path}/{class_name}", signature, generic_return_type)
            )

        # Handle Lombok-generated getters for @Value, @Data, or @Getter annotations
        if has_lombok_accessors:
            # Extract class body first (to avoid matching fields inside methods)
            class_body_pattern = (
                r"(?:public\s+)?(?:class|interface)\s+" + re.escape(class_name) + r"[^{]*\{(.*)"
            )
            class_body_match = re.search(class_body_pattern, content, re.DOTALL)

            if not class_body_match:
                return  # Can't find class body

            class_body = class_body_match.group(1)

            # Find the first method or nested class/interface to know where fields end
            # Fields are typically declared before methods
            first_method_or_class = re.search(
                r"(?:public|private|protected)?\s*(?:static)?\s*(?:class|interface|enum|\w+\s+\w+\s*\()",
                class_body,
            )
            if first_method_or_class:
                # Only look for fields before the first method
                fields_section = class_body[: first_method_or_class.start()]
            else:
                # No methods found, use whole body
                fields_section = class_body

            # Extract fields to generate getters for - simpler pattern for class-level fields
            field_pattern = r"^\s*(?:private|protected|public)?\s*(?:final)?\s*([A-Za-z0-9_\[\]<>,\.]+)\s+([a-z][a-zA-Z0-9_]*)\s*(?:=\s*[^;]+)?;"

            for match in re.finditer(field_pattern, fields_section, re.MULTILINE):
                field_type = match.group(1).strip()
                field_name = match.group(2).strip()

                # Clean up field type - remove any lingering modifiers
                field_type = re.sub(
                    r"^(private|public|protected|final|static|volatile|transient)\s+",
                    "",
                    field_type,
                ).strip()
                # Do it again in case there are multiple modifiers
                field_type = re.sub(
                    r"^(private|public|protected|final|static|volatile|transient)\s+",
                    "",
                    field_type,
                ).strip()

                # Skip if we matched on static fields (check original match)
                if "static" in match.group(0):
                    continue

                # Generate getter name (standard Java bean convention)
                getter_name = "get" + field_name[0].upper() + field_name[1:]
                # Special case for boolean fields
                if field_type in ["boolean", "Boolean"]:
                    # Also generate isXxx getter for booleans
                    is_getter_name = "is" + field_name[0].upper() + field_name[1:]
                    if is_getter_name not in self.methods:
                        self.methods[is_getter_name] = []
                    signature = self._buildSignature("", field_type)
                    self.methods[is_getter_name].append(
                        (f"{package_path}/{class_name}", signature, field_type)
                    )

                # Generate the standard getter
                if getter_name not in self.methods:
                    self.methods[getter_name] = []

                # Build JNI signature for getter (no params, returns field type)
                signature = self._buildSignature("", field_type)
                # Store with generic type info
                self.methods[getter_name].append(
                    (f"{package_path}/{class_name}", signature, field_type)
                )

    def _parseEnum(
        self,
        content: str,
        enum_name: str,
        package_path: str = "net/runelite/api",
        storage_key: str = None,
    ):
        """
        Parse an enum file
        """
        if storage_key is None:
            storage_key = enum_name
        enum = EnumInfo(name=enum_name)

        # Find enum body
        enum_match = re.search(
            r"enum\s+" + re.escape(enum_name) + r"\s*\{([^}]+)\}", content, re.DOTALL
        )
        if not enum_match:
            return

        body = enum_match.group(1)

        # Extract enum values with optional parameters
        # Pattern: CONSTANT_NAME or CONSTANT_NAME(args)
        value_pattern = r"^\s*([A-Z_][A-Z0-9_]*)\s*(?:\(([^)]*)\))?"

        for match in re.finditer(value_pattern, body, re.MULTILINE):
            const_name = match.group(1)
            const_args = match.group(2)

            if const_name and not const_name.startswith("//"):
                enum.values.append(const_name)

                # Parse arguments if present
                if const_args:
                    const_args = const_args.strip()
                    # Try to parse as int
                    if const_args.isdigit() or (const_args[0] == "-" and const_args[1:].isdigit()):
                        enum.value_map[const_name] = int(const_args)
                    # Parse as string
                    elif const_args.startswith('"') and const_args.endswith('"'):
                        enum.value_map[const_name] = const_args[1:-1]
                    else:
                        enum.value_map[const_name] = const_args

        if enum.values:
            # For InventoryID specifically, check package to store correctly
            if enum_name == "InventoryID":
                if package_path == "net/runelite/api":
                    # This is the real enum
                    self.enums["InventoryID"] = enum
                else:
                    # This is the gameval constants class - skip it as an enum
                    # It's actually a class with static ints, not an enum
                    pass
            else:
                self.enums[storage_key] = enum

    def _buildSignature(self, params: str, return_type: str) -> str:
        """
        Build JNI signature from Java types
        """
        # Build parameter signature
        param_sig = ""
        if params:
            # Split parameters (handle generics)
            param_list = self._splitParams(params)
            for param in param_list:
                param = param.strip()
                if param:
                    # Extract type (everything except last word which is param name)
                    type_match = re.match(r"(.+?)\s+\w+$", param)
                    if type_match:
                        java_type = type_match.group(1)
                    else:
                        java_type = param  # No name, just type

                    param_sig += self._typeToJni(java_type)

        # Build return signature
        return_sig = self._typeToJni(return_type)

        return f"({param_sig}){return_sig}"

    def _splitParams(self, params: str) -> List[str]:
        """
        Split parameters handling generics and annotations
        """
        result = []
        current = []
        depth = 0

        for char in params:
            if char in "<([":
                depth += 1
                current.append(char)
            elif char in ">)]":
                depth -= 1
                current.append(char)
            elif char == "," and depth == 0:
                param = "".join(current).strip()
                if param:
                    result.append(param)
                current = []
            else:
                current.append(char)

        # Add last parameter
        param = "".join(current).strip()
        if param:
            result.append(param)

        return result

    def _typeToJni(self, java_type: str) -> str:
        """
        Convert Java type to JNI signature
        """
        # Clean up type
        java_type = java_type.strip()

        # Remove annotations
        java_type = re.sub(r"@[A-Za-z0-9_.]+", "", java_type).strip()

        # Handle arrays
        array_count = java_type.count("[]")
        base_type = java_type.replace("[]", "").strip()

        # Handle varargs
        if "..." in base_type:
            base_type = base_type.replace("...", "").strip()
            array_count = 1

        # Remove generics for JNI
        if "<" in base_type:
            base_type = base_type[: base_type.index("<")].strip()

        # Get base JNI type
        if base_type in self.type_map:
            jni = self.type_map[base_type]
        elif "." in base_type:
            # Full package name
            jni = "L" + base_type.replace(".", "/") + ";"
        else:
            # IMPORTANT: Check RuneLite API classes FIRST before defaulting to standard Java/AWT types
            # This allows RuneLite's own Point, Shape, etc. to take precedence over java.awt versions
            if base_type in self.class_packages:
                # Use the known package for this class (likely a RuneLite class)
                jni = "L" + self.class_packages[base_type] + "/" + base_type + ";"
            # Check common Java types
            elif base_type in [
                "Integer",
                "Long",
                "Double",
                "Float",
                "Boolean",
                "Byte",
                "Short",
                "Character",
            ]:
                jni = "Ljava/lang/" + base_type + ";"
            elif (
                base_type in ["List", "ArrayList", "LinkedList"]
                or base_type in ["Map", "HashMap", "TreeMap"]
                or base_type in ["Set", "HashSet", "TreeSet"]
                or base_type in ["Collection", "Iterator"]
            ):
                jni = "Ljava/util/" + base_type + ";"
            elif base_type == "BufferedImage":
                jni = "Ljava/awt/image/BufferedImage;"
            elif base_type == "Graphics2D":
                jni = "Ljava/awt/Graphics2D;"
            elif base_type == "Color":
                jni = "Ljava/awt/Color;"
            elif base_type == "Point":
                jni = "Ljava/awt/Point;"
            elif base_type == "Rectangle":
                jni = "Ljava/awt/Rectangle;"
            elif base_type == "Dimension":
                jni = "Ljava/awt/Dimension;"
            elif base_type == "Font":
                jni = "Ljava/awt/Font;"
            elif base_type == "Image":
                jni = "Ljava/awt/Image;"
            elif base_type == "Shape":
                jni = "Ljava/awt/Shape;"
            else:
                # Default to base API package if unknown
                jni = "Lnet/runelite/api/" + base_type + ";"

        # Add array notation
        return "[" * array_count + jni

    def _printSummary(self, elapsed: float):
        """
        Print scraping summary
        """
        print("\n" + "=" * 60)
        print("📊 SCRAPING COMPLETE")
        print("=" * 60)
        print(f"⏱️  Time elapsed: {elapsed:.1f} seconds")
        print(f"📦 Classes scraped: {len(self.classes)}")
        print(f"🔧 Unique methods: {len(self.methods)}")
        print(f"📝 Enums found: {len(self.enums)}")
        print(f"📌 Constants found: {sum(len(c) for c in self.constants.values())}")

        # Show method distribution
        total_implementations = sum(len(impls) for impls in self.methods.values())
        print(f"📈 Total method implementations: {total_implementations}")

        # Top methods by implementation count
        print("\n🏆 Most implemented methods:")
        top_methods = sorted(self.methods.items(), key=lambda x: len(x[1]), reverse=True)[:10]
        for method, impls in top_methods:
            print(f"   {method}: {len(impls)} implementations")

        # Show important enums
        print("\n📝 Important enums found:")
        important = [
            "InventoryID",
            "Skill",
            "Prayer",
            "MenuAction",
            "GameState",
            "WidgetType",
            "ItemID",
            "NpcID",
            "ObjectID",
            "AnimationID",
        ]
        for enum_name in important:
            if enum_name in self.enums:
                enum = self.enums[enum_name]
                print(f"   {enum_name}: {len(enum.values)} values")

        print("=" * 60)

    def _buildTypeConversionDatabase(self) -> Dict[str, Any]:
        """
        Build a perfect type conversion database from scraped data
        """
        db = {
            "primitives": {},
            "enums": {},
            "objects": {},
            "arrays": {},
            "java_types": {},
            "all_types": {},  # Quick lookup for any type
        }

        # 1. Add primitives with exact conversion instructions
        primitives_map = {
            "I": {"bridge_type": "int", "python_converter": "int", "c_type": "jint"},
            "J": {"bridge_type": "long", "python_converter": "int", "c_type": "jlong"},
            "Z": {"bridge_type": "boolean", "python_converter": "bool", "c_type": "jboolean"},
            "F": {"bridge_type": "float", "python_converter": "float", "c_type": "jfloat"},
            "D": {"bridge_type": "double", "python_converter": "float", "c_type": "jdouble"},
            "B": {"bridge_type": "byte", "python_converter": "int", "c_type": "jbyte"},
            "C": {"bridge_type": "char", "python_converter": "str", "c_type": "jchar"},
            "S": {"bridge_type": "short", "python_converter": "int", "c_type": "jshort"},
            "V": {"bridge_type": "void", "python_converter": None, "c_type": "void"},
        }

        for jni_type, info in primitives_map.items():
            db["primitives"][jni_type] = info
            db["all_types"][jni_type] = {**info, "category": "primitive"}

        # 2. Add enums with ordinal mapping
        for enum_name, enum_info in self.enums.items():
            # Use the correct package path for the enum
            if enum_name in self.class_packages:
                jni_sig = f"L{self.class_packages[enum_name]}/{enum_name};"
            else:
                jni_sig = f"Lnet/runelite/api/{enum_name};"
            enum_data = {
                "bridge_type": enum_name,
                "is_enum": True,
                "values": enum_info.values,
                "name_to_ordinal": {v: i for i, v in enumerate(enum_info.values)},
                "ordinal_to_name": {i: v for i, v in enumerate(enum_info.values)},
                "python_converter": "enum_to_ordinal",
            }
            db["enums"][jni_sig] = enum_data
            db["all_types"][jni_sig] = {**enum_data, "category": "enum"}

        # 3. Process all method signatures to find all types
        seen_types = set()
        for method_name, implementations in self.methods.items():
            for class_name, signature, generic_type in implementations:
                # Extract parameter and return types
                params, ret = self._parseJniSignature(signature)
                for param_type in params:
                    seen_types.add(param_type)
                if ret:
                    seen_types.add(ret)

        # 4. Categorize all seen types
        for jni_type in seen_types:
            if jni_type in db["all_types"]:
                continue  # Already processed

            if jni_type.startswith("["):
                # Array type
                element_type = jni_type[1:]
                array_data = {
                    "bridge_type": "array",
                    "element_type": element_type,
                    "python_converter": "list",
                    "is_array": True,
                }
                db["arrays"][jni_type] = array_data
                db["all_types"][jni_type] = {**array_data, "category": "array"}

            elif jni_type.startswith("Ljava/"):
                # Java standard library type
                class_name = jni_type[1:-1].replace("/", ".")
                java_data = {
                    "bridge_type": self._getBridgeTypeForJava(class_name),
                    "java_class": class_name,
                    "python_converter": self._getPythonConverterForJava(class_name),
                }
                db["java_types"][jni_type] = java_data
                db["all_types"][jni_type] = {**java_data, "category": "java"}

            elif jni_type.startswith("Lnet/runelite/"):
                # RuneLite object (not enum)
                class_name = jni_type[1:-1].replace("/", ".")
                simple_name = class_name.split(".")[-1]

                if jni_type not in db["enums"]:  # Not already processed as enum
                    object_data = {
                        "bridge_type": "object",
                        "class_name": class_name,
                        "simple_name": simple_name,
                        "python_converter": "object_reference",
                        "is_object": True,
                    }
                    db["objects"][jni_type] = object_data
                    db["all_types"][jni_type] = {**object_data, "category": "object"}

        # 5. Add quick conversion lookup
        db["conversion_lookup"] = self._buildConversionLookup(db)

        return db

    def _parseJniSignature(self, signature: str) -> Tuple[List[str], str]:
        """
        Parse JNI signature to extract parameter and return types
        """
        match = re.match(r"\((.*?)\)(.+)", signature)
        if not match:
            return [], None

        params_str, return_type = match.groups()

        # Parse parameter types
        params = []
        i = 0
        while i < len(params_str):
            if params_str[i] == "L":
                # Object type
                end = params_str.index(";", i)
                params.append(params_str[i : end + 1])
                i = end + 1
            elif params_str[i] == "[":
                # Array type
                j = i
                while j < len(params_str) and params_str[j] == "[":
                    j += 1
                if j < len(params_str) and params_str[j] == "L":
                    end = params_str.index(";", j)
                    params.append(params_str[i : end + 1])
                    i = end + 1
                else:
                    params.append(params_str[i : j + 1])
                    i = j + 1
            else:
                # Primitive
                params.append(params_str[i])
                i += 1

        return params, return_type

    def _getBridgeTypeForJava(self, class_name: str) -> str:
        """
        Get bridge type for Java standard library class
        """
        if class_name == "java.lang.String":
            return "String"
        elif class_name == "java.lang.Integer":
            return "Integer"
        elif class_name == "java.lang.Boolean":
            return "Boolean"
        elif class_name == "java.lang.Long":
            return "Long"
        elif class_name == "java.lang.Double":
            return "Double"
        elif class_name == "java.lang.Float":
            return "Float"
        elif class_name in ["java.util.List", "java.util.ArrayList", "java.util.LinkedList"]:
            return "List"
        elif class_name in ["java.util.Map", "java.util.HashMap"]:
            return "Map"
        elif class_name == "java.lang.Object":
            return "Object"
        else:
            return "object"

    def _getPythonConverterForJava(self, class_name: str) -> str:
        """
        Get Python converter for Java standard library class
        """
        if class_name == "java.lang.String":
            return "str"
        elif class_name in ["java.lang.Integer", "java.lang.Long"]:
            return "int"
        elif class_name == "java.lang.Boolean":
            return "bool"
        elif class_name in ["java.lang.Double", "java.lang.Float"]:
            return "float"
        elif class_name.startswith("java.util."):
            return "collection"
        else:
            return "object"

    def _buildConversionLookup(self, db: Dict) -> Dict:
        """
        Build a quick lookup for Python value to bridge type conversion
        """
        return {
            "instructions": {
                "enum": "Convert name to ordinal using name_to_ordinal map",
                "primitive": "Direct conversion using python_converter",
                "object": "Use object reference ID (obj_xxx)",
                "array": "Convert list/tuple to appropriate array type",
                "java": "Convert to Java wrapper type",
            },
            "type_count": len(db["all_types"]),
            "categories": {
                "primitives": len(db["primitives"]),
                "enums": len(db["enums"]),
                "objects": len(db["objects"]),
                "arrays": len(db["arrays"]),
                "java_types": len(db["java_types"]),
            },
        }

    def _buildInheritanceTree(self) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
        """
        Build parent and children mappings from inheritance data.

        Returns:
            Tuple of (child_to_parent, parent_to_children) dictionaries
        """
        child_to_parent = {}  # class_name -> parent_name
        parent_to_children = {}  # parent_name -> [child1, child2, ...]

        for class_name, info in self.inheritance.items():
            if "extends" in info:
                parent = info["extends"]
                # Handle multiple inheritance (take first parent)
                if "," in parent:
                    parent = parent.split(",")[0].strip()

                child_to_parent[class_name] = parent

                if parent not in parent_to_children:
                    parent_to_children[parent] = []
                parent_to_children[parent].append(class_name)

        return child_to_parent, parent_to_children

    def _getFullClassPath(self, simple_name: str) -> Optional[str]:
        """
        Convert simple class name to full JNI path.

        Args:
            simple_name: Simple class name (e.g., "GameObject")

        Returns:
            Full JNI path (e.g., "net/runelite/api/GameObject") or None
        """
        # Check if it's already a full path
        if "/" in simple_name:
            return simple_name

        # Look up in class_packages
        if simple_name in self.class_packages:
            return self.class_packages[simple_name]

        # Try to find it in methods data
        for method_name, signatures in self.methods.items():
            for sig_info in signatures:
                if isinstance(sig_info, list) and len(sig_info) >= 1:
                    class_path = sig_info[0]
                    if class_path.endswith("/" + simple_name):
                        return class_path

        return None

    def _resolveDeclaringClasses(self):
        """
        Post-process methods to set correct declaring_class based on inheritance.

        For each method signature, find the topmost class in the hierarchy that
        declares it. This ensures that inherited methods point to the correct
        declaring class.

        IMPORTANT: Methods with the same signature in UNRELATED classes (different
        inheritance trees) must be kept separate!

        IMPORTANT: Sibling classes that BOTH declare the same method must also be
        kept separate! E.g., GameObject and DecorativeObject both declare getConvexHull()
        independently.

        Example:
            TileObject declares getId()
            GameObject extends TileObject
            -> getId() on GameObject should declare TileObject

            ItemComposition (unrelated) also declares getId()
            -> getId() on ItemComposition stays ItemComposition
            -> Final result: TWO getId entries, one for each tree

            GameObject declares getConvexHull()
            DecorativeObject (sibling) also declares getConvexHull()
            -> Final result: TWO getConvexHull entries, one for each sibling
        """
        print("\n🔍 Resolving declaring classes from inheritance hierarchy...")

        # Build inheritance mappings
        child_to_parent, parent_to_children = self._buildInheritanceTree()

        # For each method, group by signature and resolve declaring class
        resolved_methods = {}
        resolution_stats = {
            "updated": 0,
            "unchanged": 0,
            "total": 0,
            "skipped": 0,
            "trees_found": 0,
        }

        for method_name, signatures in self.methods.items():
            # Skip empty signature lists
            if not signatures:
                resolved_methods[method_name] = []
                continue

            # Group signatures by their JNI signature (to handle overloads separately)
            sig_groups = {}
            invalid_signatures = []

            for sig_info in signatures:
                # Validate signature format (can be tuple or list)
                if not isinstance(sig_info, (list, tuple)) or len(sig_info) < 2:
                    resolution_stats["skipped"] += 1
                    invalid_signatures.append(sig_info)
                    continue

                class_path = sig_info[0]  # e.g., "net/runelite/api/GameObject"
                jni_signature = sig_info[1]  # e.g., "()I"
                generic_type = sig_info[2] if len(sig_info) >= 3 else None

                if jni_signature not in sig_groups:
                    sig_groups[jni_signature] = []

                sig_groups[jni_signature].append((class_path, generic_type))

            # For each unique signature, split into inheritance trees and resolve each separately
            resolved_signatures = []

            for jni_signature, class_list in sig_groups.items():
                resolution_stats["total"] += len(class_list)

                # Split class_list into separate inheritance trees
                inheritance_trees = self._splitIntoInheritanceTrees(class_list, child_to_parent)
                resolution_stats["trees_found"] += len(inheritance_trees)

                # Resolve declaring class for EACH tree separately
                for tree_classes in inheritance_trees:
                    # NEW: Check if we have sibling classes that both declare the method
                    # If so, split them into separate entries instead of consolidating
                    sibling_groups = self._splitSiblingDeclarations(tree_classes, child_to_parent)

                    for sibling_group in sibling_groups:
                        declaring_class = self._findDeclaringClass(sibling_group, child_to_parent)

                        # Check if we actually changed anything
                        original_classes = [c[0] for c in sibling_group]
                        if (
                            declaring_class not in original_classes
                            or len(set(original_classes)) > 1
                        ):
                            resolution_stats["updated"] += len(sibling_group)
                        else:
                            resolution_stats["unchanged"] += len(sibling_group)

                        # Get generic type (should be same for all, take first non-None)
                        generic_type = next((gt for _, gt in sibling_group if gt), None)

                        # Store resolved signature as tuple (one entry per inheritance subtree)
                        resolved_signatures.append((declaring_class, jni_signature, generic_type))

            # Add back any invalid signatures (preserve original data)
            resolved_signatures.extend(invalid_signatures)

            resolved_methods[method_name] = resolved_signatures

        # Replace methods with resolved version
        self.methods = resolved_methods

        print(f"   ✅ Resolved {resolution_stats['total']} method declarations")
        print(
            f"   📝 Updated: {resolution_stats['updated']}, Unchanged: {resolution_stats['unchanged']}"
        )
        print(f"   🌳 Found {resolution_stats['trees_found']} inheritance trees")
        if resolution_stats["skipped"] > 0:
            print(f"   ⚠️  Skipped: {resolution_stats['skipped']} invalid signatures")

    def _splitIntoInheritanceTrees(
        self, class_list: List[Tuple[str, Any]], child_to_parent: Dict[str, str]
    ) -> List[List[Tuple[str, Any]]]:
        """
        Split a list of classes into separate inheritance trees.

        Classes that share ancestors are in the same tree.
        Classes with no relation are in separate trees.

        Args:
            class_list: List of (class_path, generic_type) tuples
            child_to_parent: Mapping of child class names to parent class names

        Returns:
            List of trees, where each tree is a list of (class_path, generic_type) tuples
        """
        if len(class_list) == 1:
            return [class_list]

        # Extract simple names
        class_info = []
        for class_path, generic_type in class_list:
            simple_name = class_path.split("/")[-1]
            class_info.append((class_path, simple_name, generic_type))

        # Build ancestor sets for each class
        def getAllAncestors(class_name: str) -> Set[str]:
            """Get all ancestors including the class itself"""
            ancestors = {class_name}
            current = class_name
            seen = set()

            while current in child_to_parent and current not in seen:
                seen.add(current)
                parent = child_to_parent[current]
                ancestors.add(parent)
                current = parent

            return ancestors

        # Group classes that share any ancestor
        trees = []
        assigned = set()

        for i, (path_i, name_i, gen_i) in enumerate(class_info):
            if i in assigned:
                continue

            # Start a new tree with this class
            tree = [(path_i, gen_i)]
            assigned.add(i)
            ancestors_i = getAllAncestors(name_i)

            # Find all other classes that share ancestors with this tree
            for j, (path_j, name_j, gen_j) in enumerate(class_info):
                if j in assigned:
                    continue

                ancestors_j = getAllAncestors(name_j)

                # If they share any ancestor, they're in the same tree
                if ancestors_i & ancestors_j:
                    tree.append((path_j, gen_j))
                    assigned.add(j)
                    # Expand the ancestor set to include this new class's ancestors
                    ancestors_i |= ancestors_j

            trees.append(tree)

        return trees

    def _splitSiblingDeclarations(
        self, class_list: List[Tuple[str, Any]], child_to_parent: Dict[str, str]
    ) -> List[List[Tuple[str, Any]]]:
        """
        Split sibling classes that both declare the same method into separate groups.

        When multiple classes in a tree are siblings (share a parent but neither is
        ancestor of the other), and ALL of them declare the method (not just inherit),
        they should be kept as separate declaring_class entries.

        Example:
            GameObject and DecorativeObject both extend TileObject
            Both declare getConvexHull() independently
            -> Should return [[GameObject], [DecorativeObject]]

            GameObject declares getId()
            WallObject extends TileObject but doesn't override getId()
            -> Should return [[GameObject, WallObject]] (consolidated)

        Args:
            class_list: List of (class_path, generic_type) tuples in same inheritance tree
            child_to_parent: Mapping of child class names to parent class names

        Returns:
            List of groups, where each group should be consolidated to one declaring_class
        """
        if len(class_list) <= 1:
            return [class_list]

        # Extract simple names
        simple_names = {path: path.split("/")[-1] for path, _ in class_list}

        # Build relationships: which classes are ancestors of which
        def isAncestorOf(potential_ancestor: str, potential_descendant: str) -> bool:
            """Check if potential_ancestor is in the ancestor chain of potential_descendant"""
            current = potential_descendant
            seen = set()
            while current in child_to_parent and current not in seen:
                seen.add(current)
                parent = child_to_parent[current]
                if parent == potential_ancestor:
                    return True
                current = parent
            return False

        # Group classes into parent-child chains
        # Classes that are neither ancestors nor descendants of each other are siblings
        groups = []
        assigned = set()

        for i, (path_i, gen_i) in enumerate(class_list):
            if i in assigned:
                continue

            simple_i = simple_names[path_i]

            # Start a new group with this class
            group = [(path_i, gen_i)]
            assigned.add(i)

            # Find all descendants of this class
            for j, (path_j, gen_j) in enumerate(class_list):
                if j in assigned:
                    continue

                simple_j = simple_names[path_j]

                # If path_i is ancestor of path_j, add to this group
                if isAncestorOf(simple_i, simple_j):
                    group.append((path_j, gen_j))
                    assigned.add(j)

            groups.append(group)

        return groups

    def _findDeclaringClass(
        self, class_list: List[Tuple[str, Any]], child_to_parent: Dict[str, str]
    ) -> str:
        """
        Find the topmost class in the hierarchy that declares this method.

        Args:
            class_list: List of (class_path, generic_type) tuples that declare this method
            child_to_parent: Mapping of child class names to parent class names

        Returns:
            The class_path of the declaring class (topmost in hierarchy)
        """
        # Extract class paths and convert to simple names
        class_paths = [c[0] for c in class_list]

        # If only one class, it's the declaring class
        if len(class_paths) == 1:
            return class_paths[0]

        # Extract simple names from full paths
        simple_names = {path: path.split("/")[-1] for path in class_paths}

        # Build hierarchy for these classes
        # Find which classes are ancestors of others
        def getAncestors(class_name: str) -> List[str]:
            """Get all ancestors of a class in order (parent, grandparent, ...)"""
            ancestors = []
            current = class_name
            seen = set()  # Prevent infinite loops

            while current in child_to_parent and current not in seen:
                seen.add(current)
                parent = child_to_parent[current]
                ancestors.append(parent)
                current = parent

            return ancestors

        # For each class, get its ancestors
        class_hierarchies = {}
        for path, simple_name in simple_names.items():
            ancestors = getAncestors(simple_name)
            class_hierarchies[simple_name] = ancestors

        # Find the topmost class (the one that is an ancestor of all others)
        # or has no parent among the classes in our list
        for path, simple_name in simple_names.items():
            # Check if this class is an ancestor of all other classes
            other_classes = [sn for sn in simple_names.values() if sn != simple_name]

            # If this class appears in the ancestor list of all others, it's the declaring class
            is_ancestor_of_all = all(
                simple_name in class_hierarchies.get(other, []) for other in other_classes
            )

            if is_ancestor_of_all:
                return path

        # If no clear ancestor found, return the first one (shouldn't happen with good data)
        # This handles cases where multiple unrelated classes declare the same method
        return class_paths[0]

    def save(self, filename: str = "runelite_api_data.json"):
        """
        Save scraped data to JSON file with perfect type conversion mapping
        """
        # Resolve declaring classes based on inheritance hierarchy
        self._resolveDeclaringClasses()

        # Build the perfect type conversion database
        type_conversion_db = self._buildTypeConversionDatabase()

        # Save the JSON format with type conversion built-in
        perfect_data = {
            "methods": self.methods,
            "enums": {
                name: {"values": enum.values, "value_map": enum.value_map}
                for name, enum in self.enums.items()
            },
            "classes": sorted(list(self.classes)),
            "constants": self.constants,
            "inheritance": self.inheritance,  # Add inheritance data
            "class_packages": self.class_packages,  # Add class-to-package mapping
            "type_conversion": type_conversion_db,
            "interface_ids": self.interface_ids,  # Add InterfaceID widget constants
        }

        with open(filename, "w") as f:
            json.dump(perfect_data, f, indent=2)

        # Save JSON summary
        summary_file = filename.replace(".json", "_summary.json")
        summary = {
            "stats": {
                "total_classes": len(self.classes),
                "total_methods": len(self.methods),
                "total_implementations": sum(len(impls) for impls in self.methods.values()),
                "total_enums": len(self.enums),
                "total_constants": sum(len(c) for c in self.constants.values()),
                "total_types": len(type_conversion_db["all_types"]),
                "total_inheritance": len(self.inheritance),
            },
            "classes": sorted(list(self.classes))[:50],
            "enums": {
                name: {
                    "count": len(enum.values),
                    "sample": enum.values[:10] if len(enum.values) > 10 else enum.values,
                }
                for name, enum in self.enums.items()
            },
            "top_methods": {
                method: len(impls)
                for method, impls in sorted(
                    self.methods.items(), key=lambda x: len(x[1]), reverse=True
                )[:30]
            },
            "type_categories": {
                "primitives": len(type_conversion_db["primitives"]),
                "enums": len(type_conversion_db["enums"]),
                "objects": len(type_conversion_db["objects"]),
                "arrays": len(type_conversion_db["arrays"]),
                "java_types": len(type_conversion_db["java_types"]),
            },
            "inheritance_sample": dict(
                list(self.inheritance.items())[:10]
            ),  # Sample of inheritance
        }

        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\n📾 Saved to {filename} and {summary_file}")
        print(
            f"📊 Type conversion database: {len(type_conversion_db['all_types'])} types with perfect mapping!"
        )

    def getSignature(self, method_name: str, class_hint: Optional[str] = None) -> Optional[str]:
        """
        Get JNI signature for a method
        """
        if method_name not in self.methods:
            return None

        impls = self.methods[method_name]

        if class_hint:
            # Try to find in specific class
            for class_name, sig, generic_type in impls:
                if class_hint in class_name:
                    return sig

        # Return first found
        return impls[0][1] if impls else None


def main():
    """
    Main function to run the local scraper
    """
    # Path to the extracted RuneLite API
    api_path = "/tmp/runelite-master/runelite-api/src/main/java/net/runelite/api"

    if not Path(api_path).exists():
        print("❌ RuneLite API not found at", api_path)
        print("Please download and extract it first:")
        print("  wget https://github.com/runelite/runelite/archive/refs/heads/master.zip")
        print("  unzip master.zip 'runelite-master/runelite-api/*'")
        return

    # Create scraper and run
    scraper = EfficientRuneLiteScraper()
    scraper.scrapeLocalDirectory(api_path)

    # Save the results - go up to project root
    output_dir = Path(__file__).parent.parent.parent.parent / "data" / "api"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "runelite_api_data.json"
    scraper.save(str(output_file))

    print(f"\n✅ Saved complete API data to {output_file}")
    print("📊 Final stats:")
    print(f"  - Classes: {len(scraper.classes)}")
    print(f"  - Methods: {len(scraper.methods)}")
    print(f"  - Enums: {len(scraper.enums)}")

    # Check specifically for WorldPoint methods
    worldpoint_methods = []
    for method_name, impls in scraper.methods.items():
        for cls, sig, generic_type in impls:
            if "WorldPoint" in cls:
                worldpoint_methods.append(f"{method_name}: {sig}")

    if worldpoint_methods:
        print(f"\n✅ Found {len(worldpoint_methods)} WorldPoint methods:")
        for method in worldpoint_methods[:5]:
            print(f"  - {method}")
        if len(worldpoint_methods) > 5:
            print(f"  ... and {len(worldpoint_methods) - 5} more")
    else:
        print("\n⚠️ No WorldPoint methods found")

    # Test retrieval
    print("\n🧪 Testing data retrieval:")

    # Test some methods
    test_methods = ["getLocalPlayer", "getItemContainer", "getTickCount", "getWidget"]
    for method in test_methods:
        sig = scraper.getSignature(method)
        if sig:
            print(f"  {method}: {sig}")

    # Test enum access
    if "InventoryID" in scraper.enums:
        inv = scraper.enums["InventoryID"]
        print(f"\n  InventoryID has {len(inv.values)} values")
        print(f"    Sample: {inv.values[:5]}")

    # Auto-run proxy generator after successful scraping
    print("\n🔄 Running proxy generator to update Python proxy classes and constants...")
    try:
        # Import the proxy generator from same directory
        # Import proxy generator from same package
        from .proxy_generator import ProxyGenerator

        # Get paths for proxy generation
        # This file is in shadowlib/_internal/scraper/, so .parent.parent.parent.parent = project root
        project_root = Path(__file__).parent.parent.parent.parent
        api_data_path = project_root / "data" / "api" / "runelite_api_data.json"

        # Generated files go in shadowlib/generated/
        generated_dir = project_root / "shadowlib" / "generated"
        proxy_output_path = generated_dir / "query_proxies.py"
        constants_output_path = generated_dir / "constants.py"

        # Ensure output directory exists
        generated_dir.mkdir(parents=True, exist_ok=True)

        # Generate proxies and constants
        generator = ProxyGenerator(str(api_data_path))
        generator.saveProxies(str(proxy_output_path))
        generator.saveConstants(str(constants_output_path))

        print(f"✅ Successfully updated proxy classes at {proxy_output_path}")
        print(f"   Generated {len(generator.class_methods)} proxy classes")
        print(f"✅ Successfully updated constants at {constants_output_path}")

    except Exception as e:
        print(f"⚠️ Failed to run proxy generator: {e}")
        print("   You may need to run it manually:")
        print("   python3 -m src.scraper.proxy_generator")


if __name__ == "__main__":
    main()
