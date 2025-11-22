#!/usr/bin/env python3
"""
Auto-generates proxy classes for the Query Builder from scraped API data.
Creates typed proxy classes for all RuneLite API classes with full IDE support.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple

# Python keywords that can't be used as method names
PYTHON_KEYWORDS = {
    "False",
    "None",
    "True",
    "and",
    "as",
    "assert",
    "async",
    "await",
    "break",
    "class",
    "continue",
    "def",
    "del",
    "elif",
    "else",
    "except",
    "finally",
    "for",
    "from",
    "global",
    "if",
    "import",
    "in",
    "is",
    "lambda",
    "nonlocal",
    "not",
    "or",
    "pass",
    "raise",
    "return",
    "try",
    "while",
    "with",
    "yield",
}


class ProxyGenerator:
    """Generates proxy classes from scraped RuneLite API data."""

    def __init__(self, api_data_path: str):
        """
        Initialize the proxy generator.

        Args:
            api_data_path: Path to the runelite_api_data.json file
        """
        with open(api_data_path) as f:
            self.api_data = json.load(f)

        self.methods = self.api_data.get("methods", {})
        self.classes = self.api_data.get("classes", [])
        self.enums = self.api_data.get("enums", {})
        self.inheritance = self.api_data.get("inheritance", {})  # Load inheritance data

        # Build class to methods mapping
        self.class_methods = self._buildClassMethodsMapping()

        # Add AWT classes that RuneLite uses
        self._addAwtClasses()

    def _addAwtClasses(self):
        """
        Add commonly-used AWT classes and RuneLite geometry classes to the class_methods mapping.
        These are discovered by analyzing RuneLite API return types.

        AWT and geometry classes don't need explicit method definitions - their public fields
        will be accessed via the __getattr__ fallback in the proxy, which calls
        QueryRef._field() to create field_get operations.

        We just need to ensure the proxy class exists, so we add them with empty
        method lists.
        """
        # Define AWT classes and RuneLite geometry classes
        # Empty lists means no explicit methods, but the proxy will still be generated
        # with __getattr__ for field access
        geometry_classes = [
            # Java AWT classes
            "java.awt.Point",
            "java.awt.Rectangle",
            "java.awt.Dimension",
            "java.awt.Color",
            "java.awt.image.BufferedImage",
            "java.awt.Shape",  # Shape is java.awt, not RuneLite API
            # RuneLite geometry classes (interfaces/abstract classes)
            "net.runelite.api.Polygon",
        ]

        # Add these to class_methods mapping with empty method lists
        # The proxy generator will create them with __getattr__ fallback
        for class_name in geometry_classes:
            if class_name not in self.class_methods:
                self.class_methods[class_name] = []

    def _buildClassMethodsMapping(self) -> Dict[str, List[Tuple[str, str, str, str, str, str]]]:
        """
        Build a mapping of class names to their methods.

        Returns:
            Dict mapping class name to list of (method_name, signature, return_type, generic_type, full_java_class, declaring_class)
        """
        class_methods = {}

        for method_name, signatures in self.methods.items():
            for sig_info in signatures:
                if isinstance(sig_info, list) and len(sig_info) >= 2:
                    class_name = sig_info[0].replace("/", ".")
                    signature = sig_info[1]
                    generic_type = sig_info[2] if len(sig_info) >= 3 else None

                    # Keep declaring_class in JNI format (with slashes) for C bridge
                    declaring_class_jni = sig_info[0]

                    # Extract return type from signature (JNI type)
                    jni_return_type = self._extractReturnType(signature)

                    # Extract full Java class path from signature for bridge communication
                    full_java_class = self._extractFullClassFromSignature(signature)

                    # Use generic type if available, otherwise use JNI-derived type
                    python_return_type = (
                        self._convertGenericToPythonType(generic_type)
                        if generic_type
                        else jni_return_type
                    )

                    if class_name not in class_methods:
                        class_methods[class_name] = []

                    class_methods[class_name].append(
                        (
                            method_name,
                            signature,
                            python_return_type,
                            generic_type,
                            full_java_class,
                            declaring_class_jni,
                        )
                    )

        return class_methods

    def _convertGenericToPythonType(self, generic_type: str) -> str:
        """
        Convert Java generic type to Python type hint with element info.

        Examples:
            "List<Player>" -> "List[Player]"
            "Tile[][]" -> "List[List[Tile]]"
            "int" -> "int"
            "void" -> "None"

        Args:
            generic_type: Java type with generics like "List<Player>" or "Tile[][]"

        Returns:
            Python-style type hint that preserves element type info
        """
        if not generic_type:
            return "Any"

        # Handle void return type
        if generic_type == "void":
            return "None"

        # Filter out invalid types (scraper errors)
        if generic_type in PYTHON_KEYWORDS or generic_type in (
            "return",
            "other",
            "extends",
            "implements",
        ):
            return "Any"

        # Handle arrays: Tile[][] -> List[List[Tile]]
        if "[]" in generic_type:
            # Count array dimensions
            dims = generic_type.count("[]")
            base_type = generic_type.replace("[]", "").strip()

            # Convert base type
            if base_type in ("int", "boolean", "long", "float", "double", "byte", "short", "char"):
                python_base = base_type
            else:
                # It's an object type - just use the simple name
                python_base = base_type.split(".")[-1] if "." in base_type else base_type
                # Filter out invalid names
                if python_base in PYTHON_KEYWORDS or python_base in (
                    "return",
                    "other",
                    "extends",
                    "implements",
                ):
                    return "Any"

            # Wrap in List[] for each dimension
            result = python_base
            for _ in range(dims):
                result = f"List[{result}]"
            return result

        # Handle generics: List<Player> -> List[Player]
        if "<" in generic_type and ">" in generic_type:
            # Extract base and generic part
            base = generic_type[: generic_type.index("<")]
            generic_part = generic_type[generic_type.index("<") + 1 : generic_type.rindex(">")]

            # Convert base type
            if base in ["List", "ArrayList", "LinkedList"]:
                base = "List"
            elif base in ["Set", "HashSet", "TreeSet"]:
                base = "Set"
            elif base in ["Map", "HashMap", "TreeMap"]:
                base = "Map"

            # Convert generic part (handle simple cases)
            element_type = generic_part.split(".")[-1] if "." in generic_part else generic_part
            # Filter out invalid names
            if element_type in PYTHON_KEYWORDS or element_type in (
                "return",
                "other",
                "extends",
                "implements",
            ):
                return "Any"

            return f"{base}[{element_type}]"

        # Check if it's a valid simple type
        simple_type = generic_type.split(".")[-1] if "." in generic_type else generic_type
        if simple_type in PYTHON_KEYWORDS or simple_type in (
            "return",
            "other",
            "extends",
            "implements",
        ):
            return "Any"

        # No generics or arrays - return as-is
        return generic_type

    def _extractReturnType(self, signature: str) -> str:
        """
        Extract the return type from a JNI signature.

        Args:
            signature: JNI signature like "(ILjava/lang/String;)Lnet/runelite/api/Player;"

        Returns:
            Return type string
        """
        # Find the return type (everything after the closing parenthesis)
        if ")" in signature:
            return_part = signature.split(")")[1]
            return self._jniToPythonType(return_part)
        return "Any"

    def _extractFullClassFromSignature(self, signature: str) -> str:
        """
        Extract the full Java class path from JNI signature return type.

        Args:
            signature: JNI signature like "(I)Lnet/runelite/api/widgets/Widget;"

        Returns:
            Full class path like "net.runelite.api.widgets.Widget" or None for primitives
        """
        if ")" not in signature:
            return None

        return_part = signature.split(")")[1]

        # Check if it's an object type
        if return_part.startswith("L") and return_part.endswith(";"):
            # Extract class path and convert / to .
            class_path = return_part[1:-1].replace("/", ".")
            return class_path

        # Primitive or void - no class
        return None

    def _jniToPythonType(self, jni_type: str) -> str:
        """
        Convert JNI type to Python type hint.

        Args:
            jni_type: JNI type like "I", "Z", "Ljava/lang/String;", etc.

        Returns:
            Python type hint string
        """
        if jni_type == "V":
            return "None"
        elif jni_type == "Z":
            return "bool"
        elif jni_type in ("B", "S", "I", "J"):
            return "int"
        elif jni_type in ("F", "D"):
            return "float"
        elif jni_type.startswith("L") and jni_type.endswith(";"):
            # Object type
            class_name = jni_type[1:-1].replace("/", ".")
            # Check if it's a string
            if class_name == "java.lang.String":
                return "str"
            # Check if it's one of our API classes or enums
            simple_name = class_name.split(".")[-1]

            # Check if it's an enum - enums should return QueryRef, not a proxy
            if simple_name in self.enums:
                return "QueryRef"  # Enums don't have proxy classes

            # Check if it's a class that should have a proxy
            if simple_name in self.classes:
                return f"'{simple_name}Proxy'"

            return "Any"
        elif jni_type.startswith("["):
            # Array type
            element_type = self._jniToPythonType(jni_type[1:])
            return f"List[{element_type}]"
        return "Any"

    def _extractParameters(self, signature: str) -> List[Tuple[str, str]]:
        """
        Extract parameter types from a JNI signature.

        Args:
            signature: JNI signature

        Returns:
            List of (param_name, param_type) tuples
        """
        if "(" not in signature or ")" not in signature:
            return []

        params_part = signature[signature.index("(") + 1 : signature.index(")")]
        if not params_part:
            return []

        params = []
        i = 0
        param_count = 0

        while i < len(params_part):
            param_count += 1
            if params_part[i] == "L":
                # Object type - find the semicolon
                end = params_part.index(";", i)
                param_type = self._jniToPythonType(params_part[i : end + 1])
                param_name = f"arg{param_count}"

                # Special handling for enums
                class_name = params_part[i + 1 : end].replace("/", ".")
                simple_name = class_name.split(".")[-1]
                if simple_name in self.enums:
                    param_type = f"Union[int, '{simple_name}Enum']"
                    param_name = simple_name.lower().replace("id", "_id")

                params.append((param_name, param_type))
                i = end + 1
            elif params_part[i] == "[":
                # Array type - find the end
                j = i + 1
                if params_part[j] == "L":
                    end = params_part.index(";", j)
                    param_type = self._jniToPythonType(params_part[i : end + 1])
                    i = end + 1
                else:
                    param_type = self._jniToPythonType(params_part[i : j + 1])
                    i = j + 1
                params.append((f"arg{param_count}", param_type))
            else:
                # Primitive type
                param_type = self._jniToPythonType(params_part[i])
                params.append((f"arg{param_count}", param_type))
                i += 1

        return params

    def _getAllMethodsIncludingInherited(
        self, class_name: str
    ) -> List[Tuple[str, str, str, str, str, str]]:
        """
        Get all methods for a class including inherited methods from parent classes.

        Args:
            class_name: Full or simple class name

        Returns:
            List of (method_name, signature, return_type, generic_type, full_java_class, declaring_class) tuples
        """
        all_methods = []
        seen_methods = set()  # Track (method_name, signature) to avoid duplicates

        # Get direct methods on this class
        if class_name in self.class_methods:
            for method_tuple in self.class_methods[class_name]:
                method_name = method_tuple[0]
                signature = method_tuple[1]
                key = (method_name, signature)
                if key not in seen_methods:
                    all_methods.append(method_tuple)
                    seen_methods.add(key)

        # Get parent class methods
        simple_name = class_name.split(".")[-1]
        if simple_name in self.inheritance:
            inheritance_info = self.inheritance[simple_name]
            if "extends" in inheritance_info:
                parent_simple_name = inheritance_info["extends"]
                # Handle multiple inheritance (take first parent)
                if "," in parent_simple_name:
                    parent_simple_name = parent_simple_name.split(",")[0].strip()

                # Find full class name for parent
                parent_full_name = None
                for full_name in self.class_methods.keys():
                    if (
                        full_name.endswith("." + parent_simple_name)
                        or full_name == parent_simple_name
                    ):
                        parent_full_name = full_name
                        break

                # Recursively get parent methods if parent is found
                if parent_full_name:
                    parent_methods = self._getAllMethodsIncludingInherited(parent_full_name)
                    for method_tuple in parent_methods:
                        method_name = method_tuple[0]
                        signature = method_tuple[1]
                        key = (method_name, signature)
                        if key not in seen_methods:
                            all_methods.append(method_tuple)
                            seen_methods.add(key)

        return all_methods

    def _generateProxyClass(
        self, class_name: str, methods: List[Tuple[str, str, str, str, str, str]]
    ) -> str:
        """
        Generate a proxy class for a RuneLite API class.

        Args:
            class_name: Name of the class to generate proxy for (can be full path like net.runelite.api.Player)
            methods: List of (method_name, signature, return_type, generic_type, full_java_class, declaring_class) tuples
        """
        # Extract simple class name (e.g., "Player" from "net.runelite.api.Player")
        simple_name = class_name.split(".")[-1]

        code = f"class {simple_name}Proxy:\n"
        code += '    """Auto-generated proxy for ' + simple_name + '"""\n\n'

        code += "    def __init__(self, query_ref):\n"
        code += "        self._ref = query_ref\n\n"

        code += "    def __getattr__(self, name):\n"
        code += '        """Fallback for field access (e.g., point.x returns field value)."""\n'
        code += "        # Use object.__getattribute__ to avoid recursion\n"
        code += "        ref = object.__getattribute__(self, '_ref')\n"
        code += "        \n"
        code += "        # Don't intercept QueryRef attributes - pass through directly\n"
        code += "        if name in ('query', 'ref_id', 'source_ref', 'return_type'):\n"
        code += "            return getattr(ref, name)\n"
        code += "        \n"
        code += "        # Assume it's a field access - use _field() method from QueryRef\n"
        code += "        return ref._field(name)\n\n"

        # Group methods by name (handle overloads)
        method_groups: Dict[str, List[Tuple[str, str, str, str, str]]] = {}
        for (
            method_name,
            signature,
            return_type,
            generic_type,
            full_java_class,
            declaring_class,
        ) in methods:
            if method_name not in method_groups:
                method_groups[method_name] = []
            method_groups[method_name].append(
                (signature, return_type, generic_type, full_java_class, declaring_class)
            )

        # Generate methods
        for method_name, signatures in sorted(method_groups.items()):
            # Skip Object methods
            if method_name in (
                "toString",
                "equals",
                "hashCode",
                "getClass",
                "notify",
                "notifyAll",
                "wait",
            ):
                continue

            # Skip Python keywords
            if method_name in PYTHON_KEYWORDS:
                continue

            # For overloaded methods, generate the most common one or handle multiple
            if len(signatures) == 1:
                signature, return_type, generic_type, full_java_class, declaring_class = signatures[
                    0
                ]
                params = self._extractParameters(signature)
                code += self._generateMethod(
                    method_name,
                    signature,
                    return_type,
                    generic_type,
                    full_java_class,
                    declaring_class,
                    params,
                )
            else:
                # Special handling for methods with both int and enum overloads
                int_sig = None
                enum_sig = None
                enumType = None

                for sig, ret_type, gen_type, full_cls, decl_cls in signatures:
                    if sig == "(I)" + sig.split(")")[1]:  # Integer parameter version
                        int_sig = (sig, ret_type, gen_type, full_cls, decl_cls)
                    elif "InventoryID" in sig or "Skill" in sig or "Prayer" in sig:
                        # This is an enum parameter version
                        enum_sig = (sig, ret_type, gen_type, full_cls, decl_cls)
                        # Extract enum type name
                        if "InventoryID" in sig:
                            enumType = "InventoryID"
                        elif "Skill" in sig:
                            enumType = "Skill"
                        elif "Prayer" in sig:
                            enumType = "Prayer"

                if int_sig and enum_sig and enumType:
                    # Generate special method that handles both int and enum
                    code += self._generateIntEnumMethod(method_name, int_sig, enum_sig, enumType)
                else:
                    # Handle overloaded methods - generate method with runtime dispatch
                    code += self._generateOverloadedMethod(method_name, signatures, class_name)

        return code

    def _generateOverloadedMethod(
        self, method_name: str, signatures: List[Tuple[str, str, str, str, str]], class_name: str
    ) -> str:
        """
        Generate a method that handles multiple overloads with runtime dispatch.

        Args:
            method_name: Name of the method
            signatures: List of (signature, return_type, generic_type, full_java_class, declaring_class) tuples
            class_name: Name of the class (for error messages)

        Returns:
            Method code as string
        """
        # Sort signatures by parameter count (simpler ones first)
        signatures.sort(key=lambda x: x[0].count(";") + x[0].count("I"))

        # Get return type from first signature (should be same for all overloads)
        _, return_type, _, full_java_class, _ = signatures[0]
        display_return_type = (
            full_java_class
            if full_java_class
            else (return_type if return_type != "Any" else "QueryRef")
        )

        # Sanitize return type (avoid Python keywords)
        if display_return_type and "." in display_return_type:
            parts = display_return_type.split(".")
            if parts[-1] in PYTHON_KEYWORDS:
                display_return_type = "int"  # Fallback for keyword conflicts

        # Check if return type needs wrapping
        needs_wrapping = False
        wrapped_class = None
        if return_type and return_type not in (
            "int",
            "long",
            "bool",
            "boolean",
            "float",
            "double",
            "str",
            "String",
            "java.lang.String",
            "None",
            "Any",
            "QueryRef",
        ):
            if "[" not in return_type and "]" not in return_type:
                if return_type not in self.enums:
                    wrapped_class = return_type
                    needs_wrapping = True

        # Generate method with *args
        # Use wrapped class name for return type if wrapping
        return_annotation = f"'{wrapped_class}Proxy'" if needs_wrapping else display_return_type
        code = f'''

    def {method_name}(self, *args) -> {return_annotation}:
        """Auto-generated method (overloaded)."""
        # Runtime dispatch based on argument count and types
        arg_count = len(args)
'''

        # Group signatures by parameter count
        by_param_count = {}
        for sig, ret_type, gen_type, full_cls, decl_cls in signatures:
            params = self._extractParameters(sig)
            param_count = len(params)
            if param_count not in by_param_count:
                by_param_count[param_count] = []
            by_param_count[param_count].append(
                (sig, ret_type, gen_type, full_cls, decl_cls, params)
            )

        # Generate if-elif chain for each parameter count
        for i, (param_count, sigs) in enumerate(sorted(by_param_count.items())):
            if_keyword = "if" if i == 0 else "elif"

            # For simplicity, just use the first signature for each param count
            # Type-based overload resolution is complex and rarely needed
            sig, ret_type, gen_type, full_cls, decl_cls, params = sigs[0]
            code += f'''        {if_keyword} arg_count == {param_count}:
            signature = "{sig}"
            declaring_class = "{decl_cls}"
            return_type = "{full_cls if full_cls else ret_type}"
'''

        # Add else clause for unsupported arg counts
        # Extract simple class name for error message
        simple_name = class_name.split("/")[-1]
        code += f'''        else:
            raise TypeError(f"{simple_name}.{method_name}() doesn't support {{arg_count}} arguments")

        ref = self._ref._createRef(
            "{method_name}",
            signature,
            *args,
            return_type=return_type,
            declaring_class=declaring_class
        )
'''

        # Add wrapping if needed
        if needs_wrapping:
            code += f"""        # Wrap as {wrapped_class}Proxy for method chaining
        return {wrapped_class}Proxy(ref)
"""
        else:
            code += """        return ref
"""

        return code

    def _generateIntEnumMethod(
        self,
        method_name: str,
        int_sig: Tuple[str, str, str, str, str],
        enum_sig: Tuple[str, str, str, str, str],
        enum_type: str,
    ) -> str:
        """
        Generate a method that can handle both integer and enum arguments.

        Args:
            method_name: Name of the method
            int_sig: (signature, return_type, generic_type, full_java_class, declaring_class) for integer version
            enum_sig: (signature, return_type, generic_type, full_java_class, declaring_class) for enum version
            enum_type: Name of the enum type (e.g., "InventoryID")

        Returns:
            Method code as string
        """
        int_signature, int_return_type, int_generic, int_full_java_class, int_declaring_class = (
            int_sig
        )
        (
            enum_signature,
            enum_return_type,
            enum_generic,
            enum_full_java_class,
            enum_declaring_class,
        ) = enum_sig

        # Use generic type if available, otherwise use return_type
        return_type = int_return_type  # Both should return the same type
        display_return_type = return_type if return_type != "Any" else "QueryRef"

        # Pass full_java_class as return_type if available, otherwise use return_type
        actual_return_type = int_full_java_class if int_full_java_class else return_type

        # Check if return type needs wrapping (same logic as _generate_method)
        needs_wrapping = False
        wrapped_class = None

        if return_type and return_type not in (
            "int",
            "long",
            "bool",
            "boolean",
            "float",
            "double",
            "str",
            "String",
            "java.lang.String",
            "None",
            "Any",
            "QueryRef",
        ):
            # Check if it contains brackets (generic types)
            if "[" not in return_type and "]" not in return_type:
                # Check if it's an enum - enums should not be wrapped
                if return_type not in self.enums:
                    wrapped_class = return_type
                    needs_wrapping = True

        # Generate the method with runtime type checking
        if needs_wrapping:
            code = f'''

    def {method_name}(self, arg1) -> '{wrapped_class}Proxy':
        """Auto-generated method (overloaded).
        Accepts either an integer ID or an {enum_type} enum."""
        # Determine signature and declaring_class based on argument type
        if isinstance(arg1, int):
            signature = "{int_signature}"
            declaring_class = "{int_declaring_class}"
        else:
            # It's an enum (EnumValue object)
            signature = "{enum_signature}"
            declaring_class = "{enum_declaring_class}"

        ref = self._ref._createRef(
            "{method_name}",
            signature,
            arg1,
            return_type="{actual_return_type}",
            declaring_class=declaring_class
        )
        # Wrap as {wrapped_class}Proxy for method chaining
        return {wrapped_class}Proxy(ref)'''
        else:
            code = f'''

    def {method_name}(self, arg1) -> {display_return_type}:
        """Auto-generated method (overloaded).
        Accepts either an integer ID or an {enum_type} enum."""
        # Determine signature and declaring_class based on argument type
        if isinstance(arg1, int):
            signature = "{int_signature}"
            declaring_class = "{int_declaring_class}"
        else:
            # It's an enum (EnumValue object)
            signature = "{enum_signature}"
            declaring_class = "{enum_declaring_class}"

        return self._ref._createRef(
            "{method_name}",
            signature,
            arg1,
            return_type="{actual_return_type}",
            declaring_class=declaring_class
        )'''

        return code

    def _generateMethod(
        self,
        method_name: str,
        signature: str,
        return_type: str,
        generic_type: str,
        full_java_class: str,
        declaring_class: str,
        params: List[Tuple[str, str]],
        is_overloaded: bool = False,
    ) -> str:
        """
        Generate a single method for a proxy class.

        Args:
            method_name: Name of the method
            signature: JNI signature
            return_type: Python return type (converted from generic_type if available)
            generic_type: Original Java generic type (e.g., "List<Player>", "Tile[][]")
            full_java_class: Full Java class path for the return type (e.g., "net.runelite.api.widgets.Widget")
            declaring_class: JNI class where method is declared (e.g., "net/runelite/api/Actor")
            params: List of (param_name, param_type) tuples
            is_overloaded: Whether this method is overloaded

        Returns:
            Method code as string
        """
        # Build parameter list
        if params:
            param_str = ", ".join(f"{name}: {ptype}" for name, ptype in params)
            param_names = ", ".join(name for name, _ in params)
        else:
            param_str = ""
            param_names = ""

        # Check if return type is a proxy class that needs wrapping
        needs_wrapping = False
        wrapped_class = None

        # Check if return_type is a simple class name that has a proxy
        # Don't wrap primitives, Any, QueryRef, generic types (List[...], etc), or enums
        if return_type and return_type not in (
            "int",
            "long",
            "bool",
            "boolean",
            "float",
            "double",
            "str",
            "String",
            "java.lang.String",
            "None",
            "Any",
            "QueryRef",
        ):
            # Check if it contains brackets (generic types like List[...], Deque[...])
            if "[" not in return_type and "]" not in return_type:
                # Check if it's an enum - enums should not be wrapped
                if return_type not in self.enums:
                    # It's a simple class name like "Player", "Tile", etc.
                    wrapped_class = return_type
                    needs_wrapping = True

        # Use the return_type for the annotation
        display_return_type = return_type if return_type != "Any" else "QueryRef"

        # Pass full_java_class as return_type if available
        # For arrays, extract JNI type from signature for proper element type resolution
        actual_return_type = full_java_class if full_java_class else return_type

        # Special handling for array types: extract JNI format from signature
        # This ensures forEach can properly resolve element types
        if not full_java_class and signature and ")" in signature:
            jni_return = signature.split(")")[1]
            # If it's an array type (starts with '['), use JNI format instead of Python type
            if jni_return.startswith("["):
                actual_return_type = jni_return  # Keep JNI format like "[Lnet/runelite/api/Item;"

        # Build method - directly call the underlying QueryRef's _create_ref
        if needs_wrapping:
            # Wrap the result as a proxy
            code = f'''

    def {method_name}(self{", " + param_str if param_str else ""}) -> '{wrapped_class}Proxy':
        """Auto-generated method{" (overloaded)" if is_overloaded else ""}."""
        ref = self._ref._createRef(
            "{method_name}",
            "{signature}",
            {param_names + "," if param_names else ""}
            return_type="{actual_return_type}",
            declaring_class="{declaring_class}"
        )
        # Wrap as {wrapped_class}Proxy for method chaining
        return {wrapped_class}Proxy(ref)'''
        else:
            # Return the QueryRef directly
            code = f'''

    def {method_name}(self{", " + param_str if param_str else ""}) -> {display_return_type}:
        """Auto-generated method{" (overloaded)" if is_overloaded else ""}."""
        return self._ref._createRef(
            "{method_name}",
            "{signature}",
            {param_names + "," if param_names else ""}
            return_type="{actual_return_type}",
            declaring_class="{declaring_class}"
        )'''

        return code

    def generateAllProxies(self) -> str:
        """
        Generate all proxy classes.

        Returns:
            Complete Python code for all proxy classes
        """
        # Header
        code = '''"""
Auto-generated proxy classes for RuneLite API Query Builder.
Generated from scraped API data - DO NOT EDIT MANUALLY.
"""

from __future__ import annotations
from typing import Any, List, Union, Optional, TYPE_CHECKING
from .._internal.query_builder import QueryRef

if TYPE_CHECKING:
    from .._internal.query_builder import Query


class ProxyBase(QueryRef):
    """Base class for all proxies with helper methods."""

    def _wrap_as_proxy(self, ref: QueryRef, proxy_class: type) -> Any:
        """
        Wrap a QueryRef as a specific proxy class for chaining.

        Args:
            ref: The QueryRef to wrap
            proxy_class: The proxy class to wrap as

        Returns:
            Instance of proxy_class
        """
        proxy = proxy_class.__new__(proxy_class)
        proxy.query = ref.query
        proxy.ref_id = ref.ref_id
        proxy.source_ref = ref.source_ref
        proxy.return_type = ref.return_type
        return proxy


# Static method proxies - allow calling static methods like: q.Perspective.localToCanvas(...)
class StaticMethodProxy:
    """Proxy for calling static methods on a class."""

    def __init__(self, query, class_name: str):
        self._query = query
        self._class_name = class_name

    def __getattr__(self, method_name: str):
        """Return a callable that creates a static method call."""
        def static_method_caller(*args, **kwargs):
            # Extract signature from kwargs if provided, otherwise None
            signature = kwargs.pop('_signature', None)
            return_type = kwargs.pop('_return_type', None)

            # Create the static method call operation
            return self._query.callStatic(
                self._class_name,
                method_name,
                *args,
                _signature=signature,
                _return_type=return_type
            )
        return static_method_caller


# Constructor proxy - allow calling constructors like: q.WorldPoint(x, y, z)
class ConstructorProxy:
    """Proxy for calling constructors."""

    def __init__(self, query, class_name: str, signature: str = None):
        self._query = query
        self._class_name = class_name
        self._signature = signature

    def __call__(self, *args, **kwargs):
        """Create an instance using the constructor."""
        signature = kwargs.pop('_signature', self._signature)
        return self._query.construct(self._class_name, *args, _signature=signature)

'''

        # Build dependency graph for inheritance ordering
        def getDependencies(class_name: str) -> List[str]:
            """Get parent classes that need to be generated first."""
            deps = []
            simple_name = class_name.split(".")[-1]
            if simple_name in self.inheritance:
                inheritance_info = self.inheritance[simple_name]
                if "extends" in inheritance_info:
                    parent_class = inheritance_info["extends"]
                    # Handle multiple inheritance (e.g., "OAuthApi, GameEngine")
                    if "," in parent_class:
                        parent_class = parent_class.split(",")[0].strip()
                    # Only add if it's a class we know about
                    if parent_class in self.classes:
                        deps.append(parent_class)
            return deps

        # Sort classes by inheritance hierarchy
        sorted_classes = []
        remaining_classes = list(self.class_methods.keys())
        generated_set = set()

        # First pass: add classes with no dependencies
        while remaining_classes:
            made_progress = False
            for class_name in remaining_classes[:]:
                simple_name = class_name.split(".")[-1]
                deps = getDependencies(class_name)

                # Check if all dependencies are already generated
                if all(dep in generated_set for dep in deps):
                    sorted_classes.append(class_name)
                    generated_set.add(simple_name)
                    remaining_classes.remove(class_name)
                    made_progress = True

            # If we didn't make progress, add remaining classes anyway (circular deps?)
            if not made_progress and remaining_classes:
                sorted_classes.extend(remaining_classes)
                break

        # Generate proxy for each class (including AWT classes with no methods)
        generated_classes = set()

        for class_name in sorted_classes:
            methods = self._getAllMethodsIncludingInherited(class_name)
            simple_name = class_name.split(".")[-1]

            # Skip duplicate generations
            if simple_name in generated_classes:
                continue

            # Generate proxy even for empty method lists (e.g., AWT classes with only fields)
            generated_classes.add(simple_name)

            # Generate the proxy class
            class_code = self._generateProxyClass(class_name, methods)
            code += class_code + "\n\n"

        # Add helper functions for constructors and static methods
        code += '''

# Helper class for static method access on Query
class QueryClassAccessor:
    """Provides dot-notation access to constructors and static methods."""

    def __init__(self, query):
        self._query = query

    def __getattr__(self, class_name: str):
        """
        Access a class for constructors or static methods.

        Usage:
            q.WorldPoint(x, y, z)  # Constructor
            q.Perspective.localToCanvas(...)  # Static method
        """
        # Return a class accessor that can be called (constructor) or accessed (static methods)
        return ClassAccessor(self._query, class_name)


class ClassAccessor:
    """Allows both constructor calls and static method access."""

    def __init__(self, query, class_name: str):
        self._query = query
        self._class_name = class_name

    def __call__(self, *args, **kwargs):
        """Call as constructor: q.WorldPoint(x, y, z)"""
        return self._query.construct(self._class_name, *args, **kwargs)

    def __getattr__(self, method_name: str):
        """Access static method: q.Perspective.localToCanvas(...)"""
        def static_caller(*args, **kwargs):
            return self._query.callStatic(self._class_name, method_name, *args, **kwargs)
        return static_caller

'''

        # Add a registry at the end
        code += """
# Proxy class registry
PROXY_CLASSES = {"""

        for class_name in sorted(generated_classes):
            code += f'''
    "{class_name}": {class_name}Proxy,'''

        code += '''
}


def get_proxy_class(class_name: str) -> type:
    """
    Get a proxy class by name.
    
    Args:
        class_name: Simple class name (e.g., "Client", "Player")
        
    Returns:
        Proxy class or QueryRef if not found
    """
    return PROXY_CLASSES.get(class_name, QueryRef)
'''

        return code

    def saveProxies(self, output_path: str):
        """
        Generate and save proxy classes to a file.

        Args:
            output_path: Path to save the generated Python file
        """
        code = self.generateAllProxies()

        with open(output_path, "w") as f:
            f.write(code)

        print(f"✅ Generated {len(self.class_methods)} proxy classes")
        print(f"   Saved to: {output_path}")

    def generateConstants(self) -> str:
        """
        Generate constant classes for ItemID, AnimationID, ObjectID, etc.

        Returns:
            Python code with constant classes
        """
        constants = self.api_data.get("constants", {})

        code = []
        code.append('"""')
        code.append("Auto-generated RuneLite API Constants")
        code.append("Generated from runelite_api_data.json")
        code.append("")
        code.append("Provides constants for ItemID, AnimationID, ObjectID, NpcID, etc.")
        code.append("Use these for type-safe, autocomplete-friendly constant access.")
        code.append("")
        code.append("Example:")
        code.append("    from src.generated.constants import ItemID")
        code.append("    inventory.contains(ItemID.CANNONBALL)")
        code.append('"""')
        code.append("")

        # Track which constant classes to generate
        # Skip internal/utility classes and focus on game content
        important_constants = {
            "net.runelite.api.ItemID": "ItemID",
            "net.runelite.api.ObjectID": "ObjectID",
            "net.runelite.api.AnimationID": "AnimationID",
            "net.runelite.api.NpcID": "NpcID",
            "NullItemID": "NullItemID",
            "NullObjectID": "NullObjectID",
            "NullNpcID": "NullNpcID",
            "Varbits": "Varbits",
            "VarPlayer": "VarPlayer",
            "VarClientInt": "VarClientInt",
            "VarClientStr": "VarClientStr",
            "net.runelite.api.SpriteID": "SpriteID",
            "HitsplatID": "HitsplatID",
            "GraphicID": "GraphicID",
            "ParamID": "ParamID",
            "StructID": "StructID",
        }

        # Generate a class for each important constant set
        for full_class_name, simple_name in important_constants.items():
            if full_class_name not in constants:
                continue

            class_constants = constants[full_class_name]

            code.append(f"class {simple_name}:")
            code.append('    """')
            code.append(f"    {simple_name} constants from RuneLite API.")
            code.append(f"    Total: {len(class_constants)} constants")
            code.append('    """')

            # Sort constants by name for better readability
            sorted_constants = sorted(class_constants.items(), key=lambda x: x[0])

            if not sorted_constants:
                code.append("    pass")
            else:
                for const_name, const_value in sorted_constants:
                    # Handle different value types
                    if isinstance(const_value, str):
                        # Escape strings properly
                        escaped_value = const_value.replace("\\", "\\\\").replace('"', '\\"')
                        code.append(f'    {const_name} = "{escaped_value}"')
                    elif isinstance(const_value, (int, float)):
                        code.append(f"    {const_name} = {const_value}")
                    else:
                        # For complex values, use repr
                        code.append(f"    {const_name} = {repr(const_value)}")

            code.append("")
            code.append("")

        # Generate InterfaceID class with nested widget classes
        interface_ids = self.api_data.get("interface_ids", {})
        if interface_ids:
            code.append("class InterfaceID:")
            code.append('    """')
            code.append("    Widget interface IDs from RuneLite API.")
            code.append("    ")
            code.append("    Structure:")
            code.append(
                "    - Top-level constants: Widget group IDs (e.g., InterfaceID.BANKMAIN = 12)"
            )
            code.append(
                "    - Nested classes: Individual widget IDs with packed format (groupID << 16 | childID)"
            )
            code.append("    ")
            code.append("    Example:")
            code.append("        # Access group ID")
            code.append("        group_id = InterfaceID.SEASLUG_BOAT_TRAVEL  # 461")
            code.append("        ")
            code.append("        # Access specific widget (packed ID)")
            code.append(
                "        widget_id = InterfaceID.SeaslugBoatTravel.SEASLUG_BOAT_WITCHAVEN_TO_FISHPIER  # 0x01cd0002"
            )
            code.append("        ")
            code.append("        # Unpack widget ID to get group and child")
            code.append("        group = widget_id >> 16  # 461")
            code.append("        child = widget_id & 0xFFFF  # 2")
            code.append('    """')
            code.append("")

            # Add top-level group constants
            groups = interface_ids.get("groups", {})
            if groups:
                code.append("    # Widget Group IDs")
                sorted_groups = sorted(groups.items(), key=lambda x: x[1])  # Sort by value
                for group_name, group_id in sorted_groups:
                    code.append(f"    {group_name} = {group_id}")
                code.append("")

            # Add nested widget classes
            nested = interface_ids.get("nested", {})
            if nested:
                code.append("    # Nested Widget Classes (packed IDs: groupID << 16 | childID)")
                for class_name, widgets in sorted(nested.items()):
                    code.append(f"    class {class_name}:")
                    code.append(f'        """Widget constants for {class_name}."""')

                    # Sort by value for better organization
                    sorted_widgets = sorted(widgets.items(), key=lambda x: x[1])
                    for widget_name, widget_id in sorted_widgets:
                        # Format as hex for readability
                        code.append(f"        {widget_name} = 0x{widget_id:08x}")

                    code.append("")

            code.append("")

        return "\n".join(code)

    def _generateAndSaveConstantFile(
        self, full_class_name: str, simple_name: str, output_path: Path
    ) -> bool:
        """Generate a single constant class file."""
        constants = self.api_data.get("constants", {})
        if full_class_name not in constants:
            return False

        class_constants = constants[full_class_name]
        code = []
        code.append('"""')
        code.append(f"Auto-generated {simple_name} constants from RuneLite API")
        code.append("DO NOT EDIT MANUALLY")
        code.append('"""')
        code.append("")
        code.append(f"class {simple_name}:")
        code.append('    """')
        code.append(f"    {simple_name} constants from RuneLite API.")
        code.append(f"    Total: {len(class_constants):,} constants")
        code.append('    """')

        sorted_constants = sorted(class_constants.items(), key=lambda x: x[0])

        if not sorted_constants:
            code.append("    pass")
        else:
            for const_name, const_value in sorted_constants:
                if isinstance(const_value, str):
                    escaped_value = const_value.replace("\\", "\\\\").replace('"', '\\"')
                    code.append(f'    {const_name} = "{escaped_value}"')
                elif isinstance(const_value, (int, float)):
                    code.append(f"    {const_name} = {const_value}")
                else:
                    code.append(f"    {const_name} = {repr(const_value)}")

        with open(output_path, "w") as f:
            f.write("\n".join(code))

        return True

    def _generateVarbitConstants(self) -> str:
        """Generate VarClient constants (only VarClientInt and VarClientStr)."""
        constants = self.api_data.get("constants", {})
        code = []
        code.append('"""')
        code.append("Auto-generated VarClient constants from RuneLite API")
        code.append("DO NOT EDIT MANUALLY")
        code.append('"""')
        code.append("")

        # Only generate VarClientInt and VarClientStr (removed Varbits and VarPlayer)
        varbit_classes = ["VarClientInt", "VarClientStr"]

        found_any = False
        for class_name in varbit_classes:
            if class_name not in constants:
                continue

            found_any = True
            class_constants = constants[class_name]
            code.append(f"class {class_name}:")
            code.append(f'    """{class_name} constants from RuneLite API."""')

            sorted_constants = sorted(class_constants.items(), key=lambda x: x[0])
            if not sorted_constants:
                code.append("    pass")
            else:
                for const_name, const_value in sorted_constants:
                    if isinstance(const_value, (int, float)):
                        code.append(f"    {const_name} = {const_value}")
                    else:
                        code.append(f"    {const_name} = {repr(const_value)}")

            code.append("")
            code.append("")

        return "\n".join(code) if found_any else None

    def _generateOtherConstants(self) -> str:
        """Generate other miscellaneous constants - ONLY the ones we actually want."""
        constants = self.api_data.get("constants", {})
        code = []
        code.append('"""')
        code.append("Auto-generated miscellaneous constants from RuneLite API")
        code.append("DO NOT EDIT MANUALLY")
        code.append('"""')
        code.append("")

        # ONLY generate these specific classes - no more bloat!
        other_classes = {
            "NullItemID": "NullItemID",
            "NullObjectID": "NullObjectID",
            "NullNpcID": "NullNpcID",
        }

        found_any = False
        for class_key, class_name in other_classes.items():
            if class_key not in constants:
                continue

            found_any = True
            class_constants = constants[class_key]
            code.append(f"class {class_name}:")
            code.append(f'    """{class_name} constants from RuneLite API."""')

            sorted_constants = sorted(class_constants.items(), key=lambda x: x[0])
            if not sorted_constants:
                code.append("    pass")
            else:
                for const_name, const_value in sorted_constants:
                    if isinstance(const_value, (int, float)):
                        code.append(f"    {const_name} = {const_value}")
                    else:
                        code.append(f"    {const_name} = {repr(const_value)}")

            code.append("")
            code.append("")

        return "\n".join(code) if found_any else None

    def _generateItemIdConstants(self) -> str:
        """
        Generate ItemID constants with nested Noted and Placeholder classes.

        Note: Java's "Cert" class is mapped to Python's "Noted" class for clarity.
        """
        # Check for gameval ItemID first (comprehensive)
        item_ids = self.api_data.get("constants", {}).get("net.runelite.api.gameval.ItemID")

        if not item_ids:
            # Fallback to regular ItemID if gameval not available
            return None

        code = []
        code.append('"""')
        code.append("Auto-generated ItemID constants from RuneLite API (gameval)")
        code.append("DO NOT EDIT MANUALLY")
        code.append("")
        code.append("Comprehensive item IDs including noted and placeholder variants")
        code.append('"""')
        code.append("")
        code.append("class ItemID:")
        code.append('    """')
        code.append("    Item IDs from RuneLite API.")
        code.append("    ")
        code.append("    Structure:")
        code.append(
            "    - Top-level constants: Regular item IDs (e.g., ItemID.DRAGON_SCIMITAR = 4587)"
        )
        code.append("    - ItemID.Noted: Noted items (e.g., ItemID.Noted.DRAGON_SCIMITAR = 4588)")
        code.append(
            "    - ItemID.Placeholder: Placeholder items (e.g., ItemID.Placeholder.DRAGON_SCIMITAR = ...)"
        )
        code.append("    ")
        code.append("    Example:")
        code.append("        # Regular item")
        code.append("        item_id = ItemID.DRAGON_SCIMITAR  # 4587")
        code.append("        ")
        code.append("        # Noted item")
        code.append("        noted_id = ItemID.Noted.DRAGON_SCIMITAR  # 4588")
        code.append("        ")
        code.append("        # Placeholder item")
        code.append("        placeholder_id = ItemID.Placeholder.DRAGON_SCIMITAR")
        code.append('    """')
        code.append("")

        # Add main item constants
        main_items = item_ids.get("main", {})
        if main_items:
            code.append("    # Regular Item IDs")
            sorted_items = sorted(main_items.items(), key=lambda x: x[0])
            for item_name, item_id in sorted_items:
                code.append(f"    {item_name} = {item_id}")
            code.append("")

        # Add Noted nested class
        noted_items = item_ids.get("Noted", {})
        if noted_items:
            code.append("    class Noted:")
            code.append('        """Noted item IDs."""')
            sorted_noted = sorted(noted_items.items(), key=lambda x: x[0])
            for item_name, item_id in sorted_noted:
                code.append(f"        {item_name} = {item_id}")
            code.append("")

        # Add Placeholder nested class
        placeholder_items = item_ids.get("Placeholder", {})
        if placeholder_items:
            code.append("    class Placeholder:")
            code.append('        """Placeholder item IDs."""')
            sorted_placeholder = sorted(placeholder_items.items(), key=lambda x: x[0])
            for item_name, item_id in sorted_placeholder:
                code.append(f"        {item_name} = {item_id}")
            code.append("")

        return "\n".join(code)

    def _generateInterfaceIdConstants(self) -> str:
        """Generate InterfaceID constants in a separate file."""
        interface_ids = self.api_data.get("interface_ids", {})
        if not interface_ids:
            return None

        code = []
        code.append('"""')
        code.append("Auto-generated InterfaceID constants from RuneLite API")
        code.append("DO NOT EDIT MANUALLY")
        code.append("")
        code.append("Widget Interface IDs with packed format (groupID << 16 | childID)")
        code.append('"""')
        code.append("")
        code.append("class InterfaceID:")
        code.append('    """')
        code.append("    Widget interface IDs from RuneLite API.")
        code.append("    ")
        code.append("    Structure:")
        code.append("    - Top-level constants: Widget group IDs (e.g., InterfaceID.BANKMAIN = 12)")
        code.append(
            "    - Nested classes: Individual widget IDs with packed format (groupID << 16 | childID)"
        )
        code.append("    ")
        code.append("    Example:")
        code.append("        # Access group ID")
        code.append("        group_id = InterfaceID.TOPLEVEL  # 548")
        code.append("        ")
        code.append("        # Access specific widget (packed ID)")
        code.append("        widget_id = InterfaceID.Toplevel.MAINMODAL  # 0x02240029")
        code.append("        ")
        code.append("        # Unpack widget ID to get group and child")
        code.append("        group = widget_id >> 16  # 548")
        code.append("        child = widget_id & 0xFFFF  # 41")
        code.append('    """')
        code.append("")

        # Add top-level group constants
        groups = interface_ids.get("groups", {})
        if groups:
            code.append("    # Widget Group IDs")
            sorted_groups = sorted(groups.items(), key=lambda x: x[1])
            for group_name, group_id in sorted_groups:
                code.append(f"    {group_name} = {group_id}")
            code.append("")

        # Add nested widget classes
        nested = interface_ids.get("nested", {})
        if nested:
            code.append("    # Nested Widget Classes (packed IDs: groupID << 16 | childID)")
            for class_name, widgets in sorted(nested.items()):
                code.append(f"    class {class_name}:")
                code.append(f'        """Widget constants for {class_name}."""')

                sorted_widgets = sorted(widgets.items(), key=lambda x: x[1])
                for widget_name, widget_id in sorted_widgets:
                    code.append(f"        {widget_name} = 0x{widget_id:08x}")

                code.append("")

        return "\n".join(code)

    def _generateConstantsInit(self, files_created: list) -> str:
        """Generate __init__.py for constants package."""
        code = []
        code.append('"""')
        code.append("RuneLite API Constants Package")
        code.append("")
        code.append("All constants are auto-generated from RuneLite API data.")
        code.append("DO NOT EDIT MANUALLY")
        code.append('"""')
        code.append("")

        # Import all classes
        if "ItemID" in files_created:
            code.append("from .item_id import ItemID")
        if "ObjectID" in files_created:
            code.append("from .object_id import ObjectID")
        if "NpcID" in files_created:
            code.append("from .npc_id import NpcID")
        if "AnimationID" in files_created:
            code.append("from .animation_id import AnimationID")
        if "VarClient" in files_created:
            code.append("from .varclient import VarClientInt, VarClientStr")
        if "VarClientID" in files_created:
            code.append("from .varclient_id import VarClientID")
        if "InterfaceID" in files_created:
            code.append("from .interface_id import InterfaceID")

        code.append("")
        code.append("__all__ = [")
        for module in files_created:
            if module not in ("VarClient",):
                code.append(f'    "{module}",')
        if "VarClient" in files_created:
            code.append('    "VarClientInt",')
            code.append('    "VarClientStr",')
        code.append("]")

        return "\n".join(code)

    def _generateConstantsWrapper(self) -> str:
        """Generate wrapper file for backward compatibility."""
        code = []
        code.append('"""')
        code.append("RuneLite API Constants Wrapper")
        code.append("")
        code.append("This file provides backward compatibility by re-exporting all constants.")
        code.append(
            "The actual constants are organized into separate files in the constants/ directory."
        )
        code.append("")
        code.append("Usage:")
        code.append("    from src.generated.constants import ItemID, InterfaceID, ObjectID")
        code.append("    ")
        code.append("    # Or import from submodules directly")
        code.append("    from src.generated.constants.item_id import ItemID")
        code.append('"""')
        code.append("")
        code.append("# Re-export all constants from the constants package")
        code.append("from .constants import *")
        code.append("")
        code.append("# Explicit exports for better IDE support")
        code.append("__all__ = [")
        code.append('    "ItemID",')
        code.append('    "ObjectID",')
        code.append('    "NpcID",')
        code.append('    "AnimationID",')
        code.append('    "InterfaceID",')
        code.append('    "VarClientInt",')
        code.append('    "VarClientStr",')
        code.append('    "VarClientID",')
        code.append("]")

        return "\n".join(code)

    def saveConstants(self, output_path: str):
        """
        Generate and save constants to separate Python files.
        Creates individual files for each constant type and a wrapper.

        Args:
            output_path: Path to the constants directory (will create subdirectory)
        """
        print("\n🔢 Generating constants files...")

        output_dir = Path(output_path).parent / "constants"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate each constant file separately
        files_created = []

        # 1. Generate ItemID (use gameval version with nested classes if available)
        item_id_code = self._generateItemIdConstants()
        if item_id_code:
            with open(output_dir / "item_id.py", "w") as f:
                f.write(item_id_code)
            files_created.append("ItemID")
        elif self._generateAndSaveConstantFile(
            "net.runelite.api.ItemID", "ItemID", output_dir / "item_id.py"
        ):
            # Fallback to regular ItemID if gameval not available
            files_created.append("ItemID")

        # 2. Generate ObjectID
        if self._generateAndSaveConstantFile(
            "net.runelite.api.ObjectID", "ObjectID", output_dir / "object_id.py"
        ):
            files_created.append("ObjectID")

        # 3. Generate NpcID
        if self._generateAndSaveConstantFile(
            "net.runelite.api.NpcID", "NpcID", output_dir / "npc_id.py"
        ):
            files_created.append("NpcID")

        # 4. Generate AnimationID
        if self._generateAndSaveConstantFile(
            "net.runelite.api.AnimationID", "AnimationID", output_dir / "animation_id.py"
        ):
            files_created.append("AnimationID")

        # 5. Generate VarClient constants (VarClientInt, VarClientStr, VarClientID)
        varclient_code = self._generateVarbitConstants()
        if varclient_code:
            with open(output_dir / "varclient.py", "w") as f:
                f.write(varclient_code)
            files_created.append("VarClient")

        # 6. Generate VarClientID from gameval
        if self._generateAndSaveConstantFile(
            "VarClientID", "VarClientID", output_dir / "varclient_id.py"
        ):
            files_created.append("VarClientID")

        # 7. Generate InterfaceID (special handling)
        interface_code = self._generateInterfaceIdConstants()
        if interface_code:
            with open(output_dir / "interface_id.py", "w") as f:
                f.write(interface_code)
            files_created.append("InterfaceID")

        # Note: We skip NullItemID, NullObjectID, NullNpcID etc. - they're huge bloat (50k+ lines)

        # 9. Create __init__.py for the constants package
        init_code = self._generateConstantsInit(files_created)
        with open(output_dir / "__init__.py", "w") as f:
            f.write(init_code)

        # 10. Create wrapper file at original location for backward compatibility
        wrapper_code = self._generateConstantsWrapper()
        with open(output_path, "w") as f:
            f.write(wrapper_code)

        total_size = sum(f.stat().st_size for f in output_dir.glob("*.py")) / 1024
        print(f"✅ Generated {len(files_created)} constant modules ({total_size:.1f} KB total)")
        print(f"   Files: {', '.join(files_created)}")
        print(f"✅ Created wrapper at {output_path}")


def main():
    """Generate proxy classes and constants from API data."""
    # Get paths - this file is in shadowlib/_internal/scraper/
    # parent.parent.parent gets us to project root
    project_root = Path(__file__).parent.parent.parent.parent
    api_data_path = project_root / "data" / "api" / "runelite_api_data.json"

    # Generated files go in shadowlib/generated/
    generated_dir = project_root / "shadowlib" / "generated"
    proxies_output_path = generated_dir / "query_proxies.py"
    constants_output_path = generated_dir / "constants.py"

    # Ensure output directory exists
    generated_dir.mkdir(parents=True, exist_ok=True)

    # Generate proxies
    generator = ProxyGenerator(str(api_data_path))
    generator.saveProxies(str(proxies_output_path))

    # Generate constants
    generator.saveConstants(str(constants_output_path))

    # Show stats
    print("\n📊 Generation Statistics:")
    print(f"   Total methods: {len(generator.methods)}")
    print(f"   Total classes: {len(generator.classes)}")
    print(f"   Classes with methods: {len(generator.class_methods)}")

    # Show some example classes
    examples = list(generator.class_methods.keys())[:5]
    print("\n📝 Example classes generated:")
    for ex in examples:
        method_count = len(generator.class_methods[ex])
        print(f"   - {ex}: {method_count} methods")

    # Show constants stats
    constants = generator.api_data.get("constants", {})
    total_constants = sum(len(v) for v in constants.values())
    print("\n🔢 Constants Statistics:")
    print(f"   Total constant values: {total_constants}")
    print("   Constant classes generated: ItemID, ObjectID, AnimationID, NpcID, and more")


if __name__ == "__main__":
    main()
