"""
Query Builder for RuneLite API - Batch execution system
Allows chaining multiple API calls and executing them in a single invokeLater call
With optimization for large batches including dead code elimination and deduplication
Now with Pythonic extensions for forEach, filter, map, and conditionals
"""

import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Union

if TYPE_CHECKING:
    from .api import RuneLiteAPI

# Lazy-load generated proxies to avoid circular imports
_query_proxies = None
_proxies_loaded = False


def _loadProxies():
    """Lazy-load generated proxy classes from cache."""
    global \
        _query_proxies, \
        _proxies_loaded, \
        ClientProxy, \
        LocalPointProxy, \
        PerspectiveProxy, \
        WorldPointProxy

    if _proxies_loaded:
        return _query_proxies

    from .cache_manager import ensureGeneratedFiles, loadGeneratedModule

    # Ensure generated files exist
    ensureGeneratedFiles()

    # Import from cache
    _query_proxies = loadGeneratedModule("query_proxies")
    if _query_proxies is None:
        raise ImportError("Failed to load generated query_proxies module from cache")

    # Extract commonly used classes
    ClientProxy = _query_proxies.ClientProxy
    LocalPointProxy = _query_proxies.LocalPointProxy
    PerspectiveProxy = _query_proxies.PerspectiveProxy
    WorldPointProxy = _query_proxies.WorldPointProxy

    _proxies_loaded = True
    return _query_proxies


# Initialize proxy references as None (will be loaded on first use)
ClientProxy = None
LocalPointProxy = None
PerspectiveProxy = None
WorldPointProxy = None


def convertQueryArgs(args: tuple) -> List[Any]:
    """
    Convert Python arguments to JSON-serializable format.
    Handles QueryRefs, EnumValues, sets, etc.

    Args:
        args: Tuple of arguments to convert

    Returns:
        List of converted arguments
    """
    converted = []
    for arg in args:
        # Import QueryRef here to avoid circular import
        if hasattr(arg, "__class__") and arg.__class__.__name__ == "QueryRef":
            # Reference to another QueryRef
            converted.append({"$ref": arg.ref_id})
        elif hasattr(arg, "_enum_name") and hasattr(arg, "_ordinal"):
            # It's an EnumValue object
            converted.append({"$enum": {"class": arg._enum_name, "ordinal": arg._ordinal}})
        elif isinstance(arg, set):
            # Convert Python set to list (Java Set will be created on bridge side)
            converted.append(list(arg))
        else:
            # Primitive or string
            converted.append(arg)
    return converted

    # Constructor/static method accessor classes
    class _WorldPointConstructor:
        def __call__(self, *args: Any, **kwargs: Any) -> WorldPointProxy: ...
        def fromLocalInstance(
            self, client: ClientProxy, localPoint: LocalPointProxy
        ) -> WorldPointProxy: ...
        def __getattr__(self, name: str) -> Any: ...

    class _LocalPointConstructor:
        def __call__(self, *args: Any, **kwargs: Any) -> LocalPointProxy: ...
        def fromWorld(
            self, client: ClientProxy, worldPoint: WorldPointProxy
        ) -> LocalPointProxy: ...
        def __getattr__(self, name: str) -> Any: ...

    class _PerspectiveConstructor:
        def __call__(self, *args: Any, **kwargs: Any) -> PerspectiveProxy: ...
        def localToCanvas(self, *args: Any) -> Any: ...
        def __getattr__(self, name: str) -> Any: ...

    class _GenericConstructor:
        def __call__(self, *args: Any, **kwargs: Any) -> Any: ...
        def __getattr__(self, name: str) -> Any: ...


# We'll import generated proxies later to avoid circular import
GeneratedClientProxy = None
GeneratedPlayerProxy = None
PROXY_CLASSES = {}
_USE_GENERATED_PROXIES = False  # Will be set to True if import succeeds


class BridgeHelpersAccessor:
    """
    Accessor for BridgeHelpers methods. Provides direct access to bridge helper functions.

    Usage:
        q.bridge.getBankItemIds()
        q.bridge.getTickCount()

    Available methods are called directly on BridgeHelpers without needing a plugin reference.
    """

    def __init__(self, query: "Query"):
        """
        Initialize the BridgeHelpers accessor.

        Args:
            query: Parent Query object
        """
        self.query = query

    def __getattr__(self, method_name: str) -> Callable:
        """
        Get a BridgeHelpers method by name.

        Args:
            method_name: Name of the method (e.g., 'getBankItemIds', 'getTickCount')

        Returns:
            Callable that creates the BridgeHelpers operation
        """

        def bridgeMethod(*args, signature: str = None, **kwargs):
            """
            Call a BridgeHelpers method.

            Args:
                *args: Method arguments
                signature: JNI signature (required)
                **kwargs: Additional keyword arguments

            Returns:
                QueryRef for the result
            """
            if signature is None:
                raise ValueError(f"signature parameter is required for BridgeHelpers.{method_name}")

            # Create a new ref for this operation
            ref_id = f"r{self.query.ref_counter}"
            self.query.ref_counter += 1

            # Convert args (handle enums, QueryRefs, etc.)
            converted_args = convertQueryArgs(args)

            # Create the operation
            operation = {
                "ref": ref_id,
                "target": "BridgeHelpers",
                "method": method_name,
                "signature": signature,
                "args": converted_args,
            }

            self.query.operations.append(operation)

            # Create QueryRef for the result
            result_ref = QueryRef(self.query, ref_id, None, "BridgeHelpers")
            self.query.refs[ref_id] = result_ref

            return result_ref

        return bridge_method


class PluginAccessor:
    """
    Accessor for RuneLite plugins. Provides dynamic access to loaded plugins.

    Usage:
        q.plugin.shortestPath  # Access ShortestPathPlugin

    Available plugins (dynamically loaded):
        - shortestPath: ShortestPathPlugin - Pathfinding and navigation

    Note: Attributes are created dynamically via __getattr__, so IDE autocomplete
    may not work. Use the plugin name in camelCase (e.g., 'shortestPath').
    """

    def __init__(self, query: "Query"):
        """
        Initialize the plugin accessor.

        Args:
            query: Parent Query object
        """
        self.query = query

    def __getattr__(self, plugin_name: str) -> "PluginProxy":
        """
        Get a plugin by name. This creates a PluginProxy that will:
        1. First query pluginManager.getPlugins() with a filter
        2. Cache the plugin reference
        3. Allow method calls on the plugin

        Args:
            plugin_name: Name of the plugin (e.g., 'shortestPath' for ShortestPathPlugin)

        Returns:
            PluginProxy for the requested plugin
        """
        # Convert camelCase to class name (e.g., shortestPath -> ShortestPathPlugin)
        class_name = plugin_name[0].upper() + plugin_name[1:] + "Plugin"

        return PluginProxy(self.query, class_name, plugin_name)


class PluginProxy:
    """
    Proxy for a specific RuneLite plugin. Handles querying the plugin and calling its methods.
    """

    def __init__(self, query: "Query", class_name: str, plugin_name: str):
        """
        Initialize a plugin proxy.

        Args:
            query: Parent Query object
            class_name: Full class name (e.g., "ShortestPathPlugin")
            plugin_name: Short name for caching (e.g., "shortestPath")
        """
        self.query = query
        self.class_name = class_name
        self.plugin_name = plugin_name
        self._plugin_ref: QueryRef | None = None

    def _getPluginRef(self) -> "QueryRef":
        """
        Get or create the plugin reference by querying pluginManager.

        Returns:
            QueryRef for the plugin instance
        """
        if self._plugin_ref is not None:
            return self._plugin_ref

        # Create a ref that fetches the plugin from pluginManager
        # The ref name uses dots for cache/filter identification
        ref_id = f"shortestpath.{self.class_name}"

        # Check if we've already created this ref
        if ref_id in self.query.refs:
            self._plugin_ref = self.query.refs[ref_id]
            return self._plugin_ref

        # Create the operation to get the plugin
        # This uses the special filter syntax to get a specific plugin
        operation = {
            "ref": ref_id,
            "target": "pluginManager",
            "method": "getPlugins",
            "declaring_class": "net/runelite/client/plugins/PluginManager",
            "signature": "()Ljava/util/Collection;",
            "args": [],
        }

        self.query.operations.append(operation)

        # Create a QueryRef for the plugin
        # The return type uses slashes (Java class path format)
        plugin_ref = QueryRef(self.query, ref_id, None, f"shortestpath/{self.class_name}")
        self.query.refs[ref_id] = plugin_ref
        self._plugin_ref = plugin_ref

        return plugin_ref

    def __getattr__(self, method_name: str):
        """
        Handle method calls on the plugin.

        Args:
            method_name: Name of the method to call

        Returns:
            Callable that creates a method call when invoked
        """
        # Don't intercept private attributes
        if method_name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{method_name}'")

        # Get the plugin ref
        plugin_ref = self._getPluginRef()

        # Return a callable that will create a method call on the plugin
        def dynamicMethod(*args, **kwargs):
            # Look up the method signature from plugin API data
            if hasattr(self.query.api, "plugin_data") and self.query.api.plugin_data:
                plugin_methods = self.query.api.plugin_data.get("methods", {})
                if method_name in plugin_methods:
                    # Find the matching signature
                    for class_path, signature, _return_type in plugin_methods[method_name]:
                        if self.class_name in class_path:
                            # Found it! Create the method call with slashes in declaring_class
                            declaring_class = class_path  # Keep slashes as-is
                            return plugin_ref._createRef(
                                method_name,
                                signature,
                                *args,
                                declaring_class=declaring_class,
                                **kwargs,
                            )

            # Fallback: try to infer signature (won't work without plugin data)
            raise AttributeError(
                f"Method '{method_name}' not found for plugin '{self.class_name}'. "
                f"Make sure plugin API data is loaded."
            )

        return dynamic_method


class QueryRef:
    """
    Represents a future reference to a Java object in a query chain.
    Each QueryRef tracks its method calls to build up a chain of operations.
    """

    def __init__(
        self,
        query: "Query",
        ref_id: str,
        source_ref: Optional["QueryRef"] = None,
        return_type: str | None = None,
    ):
        """
        Initialize a QueryRef.

        Args:
            query: Parent Query object
            ref_id: Unique identifier for this reference
            source_ref: The QueryRef this was called on (None for root)
            return_type: Java type that this ref will resolve to
        """
        self.query = query
        self.ref_id = ref_id
        self.source_ref = source_ref
        self.return_type = return_type
        self._is_selected = False
        self._field_cache = {}  # Cache for field accesses to avoid duplicates

    def _createRef(
        self,
        method_name: str,
        signature: str,
        *args,
        return_type: str = None,
        declaring_class: str = None,
    ) -> "QueryRef":
        """
        Create a new reference from a method call.
        With optimization, this will detect and reuse duplicate operations.

        Args:
            method_name: Name of the method to call
            signature: JNI signature of the method
            args: Arguments to pass to the method
            return_type: Java type that this method returns
            declaring_class: The class where this method is declared (e.g., "net/runelite/api/Actor")
                           If provided, skips runtime lookup for better performance

        Returns:
            New QueryRef representing the result of this method call
        """
        # Convert arguments to serializable format
        converted_args = self._convertArgs(args)

        # Check for duplicate operations if optimization is enabled
        if self.query.optimize:
            # Create a cache key from the operation details
            cache_key = json.dumps(
                {
                    "target": self.ref_id,
                    "method": method_name,
                    "signature": signature,
                    "args": converted_args,
                },
                sort_keys=True,
            )

            # Check if we've seen this exact operation before
            if cache_key in self.query.operation_cache:
                existing_ref_id = self.query.operation_cache[cache_key]
                # Return the existing reference instead of creating a duplicate
                return self.query.refs[existing_ref_id]

        # Generate unique ref ID
        new_ref_id = f"r{self.query.ref_counter}"
        self.query.ref_counter += 1

        # Record the operation
        operation = {
            "ref": new_ref_id,
            "target": self.ref_id,
            "method": method_name,
            "signature": signature,
            "args": converted_args,
        }

        # CRITICAL: Include declaring_class so bridge knows exactly where to find the method
        # This eliminates the need for blind interface searching in C
        if declaring_class:
            # Use pre-computed declaring_class from proxy generator (fast path)
            operation["declaring_class"] = declaring_class
        elif hasattr(self.query, "api") and method_name in self.query.api.api_data["methods"]:
            # Fallback: Look up declaring_class at runtime using type information
            # Use get_method_info with return_type from the QueryRef to find correct declaring_class
            target_class = (
                self.return_type if hasattr(self, "return_type") and self.return_type else None
            )

            # Convert return_type to proper format for lookup
            if target_class:
                # Handle simple names like "WorldPoint"
                if "/" not in target_class and "." not in target_class:
                    # Look up full path from class_packages
                    if "class_packages" in self.query.api.api_data:
                        package_path = self.query.api.api_data["class_packages"].get(target_class)
                        if package_path:
                            target_class = f"{package_path}/{target_class}"
                        else:
                            # Fallback to base package
                            target_class = f"net/runelite/api/{target_class}"

            method_info = self.query.api.getMethodInfo(
                method_name, list(args), target_class=target_class
            )
            if method_info:
                operation["declaring_class"] = method_info["declaring_class"]
            else:
                # Last resort: take first match
                import sys

                print(
                    f"⚠️  WARNING: Could not resolve declaring_class for '{method_name}' on type '{target_class}'",
                    file=sys.stderr,
                )
                for entry in self.query.api.api_data["methods"][method_name]:
                    if entry[1] == signature:
                        if len(entry) > 0:
                            operation["declaring_class"] = entry[0]
                        break

        # CRITICAL: Validate that declaring_class is set before sending to bridge
        if "declaring_class" not in operation or operation["declaring_class"] is None:
            import sys

            print(
                f"❌ CRITICAL ERROR: declaring_class is missing for method '{method_name}'",
                file=sys.stderr,
            )
            print("   This will cause the JNI bridge to crash.", file=sys.stderr)
            print(f"   Operation: {operation}", file=sys.stderr)
            raise RuntimeError(
                f"Cannot create operation for method '{method_name}': declaring_class is required. "
                f"This indicates a bug in the query builder or missing API data."
            )

        self.query.operations.append(operation)

        # Update dependency graph if optimization is enabled
        if self.query.optimize:
            deps = set()
            if self.ref_id != "client":
                deps.add(self.ref_id)
                # Add transitive dependencies
                if self.ref_id in self.query.dependency_graph:
                    deps.update(self.query.dependency_graph[self.ref_id])
            self.query.dependency_graph[new_ref_id] = deps

            # Cache this operation
            cache_key = json.dumps(
                {
                    "target": self.ref_id,
                    "method": method_name,
                    "signature": signature,
                    "args": converted_args,
                },
                sort_keys=True,
            )
            self.query.operation_cache[cache_key] = new_ref_id

        # Extract return type from signature if not provided or refine generic types
        # IMPORTANT: Even if return_type is set (e.g., "java.util.List"), we should refine
        # it to extract generic parameters (e.g., "List<NPC>" -> "net/runelite/api/NPC")
        has_generic = False
        if hasattr(self.query, "api") and method_name in self.query.api.api_data["methods"]:
            for entry in self.query.api.api_data["methods"][method_name]:
                if entry[1] == signature:
                    # Found matching signature - check for generic return type
                    if len(entry) > 2 and entry[2]:
                        generic_type = entry[2]
                        # Parse generic types like "List<NPC>" -> "net/runelite/api/NPC"
                        if "<" in generic_type and ">" in generic_type:
                            has_generic = True
                            start = generic_type.index("<") + 1
                            end = generic_type.index(">")
                            inner_type = generic_type[start:end]
                            # Convert short name to full JNI path
                            if "/" not in inner_type:
                                # Simple name - assume it's in net/runelite/api
                                return_type = f"net/runelite/api/{inner_type}"
                            else:
                                return_type = inner_type
                    break

        # ALWAYS extract full path from JNI signature (unless we extracted a generic parameter)
        # This fixes the bug where simplified names like "Shape" were used instead of "java/awt/Shape"
        if signature and not has_generic:
            paren_end = signature.rfind(")")
            if paren_end >= 0:
                ret_sig = signature[paren_end + 1 :]
                if ret_sig.startswith("L") and ret_sig.endswith(";"):
                    # Extract full path: Ljava/awt/Shape; -> java/awt/Shape
                    # Use slash format (both slash and dot formats work correctly)
                    return_type = ret_sig[1:-1]
                elif ret_sig.startswith("["):
                    # Array type: keep JNI format for arrays
                    # e.g., [Lnet/runelite/api/GameObject; or [[Lnet/runelite/api/Tile;
                    return_type = ret_sig

        # Create and return new QueryRef
        new_ref = QueryRef(self.query, new_ref_id, self, return_type)
        self.query.refs[new_ref_id] = new_ref
        return new_ref

    def _convertArgs(self, args: tuple) -> List[Any]:
        """
        Convert Python arguments to JSON-serializable format.

        Args:
            args: Tuple of arguments to convert

        Returns:
            List of converted arguments
        """
        converted = []
        for arg in args:
            if isinstance(arg, QueryRef):
                # Reference to another QueryRef
                converted.append({"$ref": arg.ref_id})
            elif hasattr(arg, "_enum_name") and hasattr(arg, "_ordinal"):
                # It's an EnumValue object
                converted.append({"$enum": {"class": arg._enum_name, "ordinal": arg._ordinal}})
            elif isinstance(arg, set):
                # Convert Python set to list (Java Set will be created on bridge side)
                converted.append(list(arg))
            else:
                # Primitive or string
                converted.append(arg)
        return converted

    def __getitem__(self, key: Union[int, slice, tuple, "QueryRef"]) -> "QueryRef":
        """
        Support array indexing, slicing, and multi-dimensional access.

        Examples:
            players[5]                    # Single index
            players[10:20]                # Slice
            players[-1]                   # Negative index
            tiles[50, 50, 2]              # Multi-dimensional
            tiles[40:60, 40:60, plane]    # Mixed slice and dynamic index

        Args:
            key: Can be:
                - int: Single index
                - slice: Range slice (start:stop:step)
                - tuple: Multi-dimensional access
                - QueryRef: Dynamic index from another query

        Returns:
            New QueryRef representing the result
        """
        # Handle slice objects: arr[10:20]
        if isinstance(key, slice):
            return self._handleSlice(key)

        # Handle tuple for multi-dimensional: arr[x, y, z]
        elif isinstance(key, tuple):
            return self._handleMultidim(key)

        # Handle QueryRef as dynamic index: arr[dynamic_ref]
        elif isinstance(key, QueryRef):
            return self._handleDynamicIndex(key)

        # Handle integer index (including negative)
        elif isinstance(key, int):
            if key < 0:
                return self._handleNegativeIndex(key)
            else:
                return self._handleStaticIndex(key)

        else:
            raise TypeError(
                f"Invalid index type: {type(key)}. Expected int, slice, tuple, or QueryRef"
            )

    def _handleStaticIndex(self, index: int) -> "QueryRef":
        """Handle static integer index: arr[5] - uses sliceArray with index dimension"""
        new_ref_id = f"r{self.query.ref_counter}"
        self.query.ref_counter += 1

        # Build dimension descriptor for single index
        dimension = {"type": "index", "value": index}

        operation = {
            "type": "sliceArray",
            "ref": new_ref_id,
            "target": self.ref_id,
            "dimensions": [dimension],
        }
        self.query.operations.append(operation)

        # Get element type (one dimension unwrapped)
        element_type = self._getElementType()
        new_ref = QueryRef(self.query, new_ref_id, self, element_type)
        self.query.refs[new_ref_id] = new_ref

        # Wrap as appropriate proxy if type known
        if element_type:
            proxy_class = self._getProxyClassForType(element_type)
            if proxy_class and proxy_class != QueryRef:
                # Create proxy and set _ref attribute (proxies expect this)
                proxy = proxy_class(new_ref)
                return proxy

        return new_ref

    def _handleNegativeIndex(self, index: int) -> "QueryRef":
        """
        Handle negative index: arr[-1] (last element) - uses sliceArray with negative index dimension
        """
        new_ref_id = f"r{self.query.ref_counter}"
        self.query.ref_counter += 1

        # Build dimension descriptor for negative index
        dimension = {
            "type": "index",
            "value": index,  # Negative value
        }

        operation = {
            "type": "sliceArray",
            "ref": new_ref_id,
            "target": self.ref_id,
            "dimensions": [dimension],
        }
        self.query.operations.append(operation)

        element_type = self._getElementType()
        new_ref = QueryRef(self.query, new_ref_id, self, element_type)
        self.query.refs[new_ref_id] = new_ref

        return new_ref

    def _handleSlice(self, s: slice) -> "QueryRef":
        """
        Handle slice object: arr[10:20], arr[:10], arr[10:], arr[::2]

        Creates a sliceArray operation with a single dimension.
        """
        new_ref_id = f"r{self.query.ref_counter}"
        self.query.ref_counter += 1

        # Build dimension descriptor
        dimension = {
            "type": "range",
            "start": s.start if s.start is not None else 0,
            "stop": s.stop,  # Can be None for open-ended
        }
        # Only include step if it's not the default value of 1
        step = s.step if s.step is not None else 1
        if step != 1:
            dimension["step"] = step

        operation = {
            "type": "sliceArray",
            "ref": new_ref_id,
            "target": self.ref_id,
            "dimensions": [dimension],
        }
        self.query.operations.append(operation)

        # Result is still an array (one dimension sliced)
        return_type = self.return_type  # Keep same type (still array)
        new_ref = QueryRef(self.query, new_ref_id, self, return_type)
        self.query.refs[new_ref_id] = new_ref

        return new_ref

    def _handleDynamicIndex(self, index_ref: "QueryRef") -> "QueryRef":
        """
        Handle QueryRef as index: arr[dynamic_ref]

        The index value will be resolved at query execution time.
        """
        new_ref_id = f"r{self.query.ref_counter}"
        self.query.ref_counter += 1

        operation = {
            "type": "arrayIndex",
            "ref": new_ref_id,
            "target": self.ref_id,
            "index": index_ref.ref_id,  # Reference to dynamic value
            "dynamic": True,
        }
        self.query.operations.append(operation)

        # Track dependency
        if new_ref_id not in self.query.dependency_graph:
            self.query.dependency_graph[new_ref_id] = set()
        self.query.dependency_graph[new_ref_id].add(self.ref_id)
        self.query.dependency_graph[new_ref_id].add(index_ref.ref_id)

        element_type = self._getElementType()
        new_ref = QueryRef(self.query, new_ref_id, self, element_type)
        self.query.refs[new_ref_id] = new_ref

        return new_ref

    def _handleMultidim(self, keys: tuple) -> "QueryRef":
        """
        Handle multi-dimensional access: arr[x, y, z]

        Each element in the tuple can be:
        - int: Static index
        - slice: Range
        - QueryRef: Dynamic index

        Examples:
            arr[50, 50, 2]              # All static
            arr[40:60, 40:60, plane]    # Mixed slice and dynamic
            arr[:, :, 2]                # Full slices with static index
        """
        new_ref_id = f"r{self.query.ref_counter}"
        self.query.ref_counter += 1

        # Process each dimension
        dimensions = []
        dependencies = {self.ref_id}

        for key in keys:
            if isinstance(key, slice):
                # Range dimension
                dimension = {
                    "type": "range",
                    "start": key.start if key.start is not None else 0,
                    "stop": key.stop,
                }
                # Only include step if it's not the default value of 1
                step = key.step if key.step is not None else 1
                if step != 1:
                    dimension["step"] = step
                dimensions.append(dimension)
            elif isinstance(key, int):
                if key < 0:
                    # Negative index
                    dimensions.append({"type": "index", "value": key, "negative": True})
                else:
                    # Static index
                    dimensions.append({"type": "index", "value": key})
            elif isinstance(key, QueryRef):
                # Dynamic index (reference to another query result)
                dimensions.append({"type": "index", "value": key.ref_id, "dynamic": True})
                dependencies.add(key.ref_id)
            else:
                raise TypeError(f"Invalid dimension type: {type(key)}")

        operation = {
            "type": "sliceArray",
            "ref": new_ref_id,
            "target": self.ref_id,
            "dimensions": dimensions,
        }
        self.query.operations.append(operation)

        # Update dependency graph
        if new_ref_id not in self.query.dependency_graph:
            self.query.dependency_graph[new_ref_id] = set()
        self.query.dependency_graph[new_ref_id].update(dependencies)

        # Determine return type based on how many dimensions were sliced vs indexed
        # For now, keep as generic - C side will handle properly
        return_type = self._calculateResultType(dimensions)
        new_ref = QueryRef(self.query, new_ref_id, self, return_type)
        self.query.refs[new_ref_id] = new_ref

        return new_ref

    def _calculateResultType(self, dimensions: List[Dict]) -> str | None:
        """
        Calculate the return type based on dimension operations.

        - If all dimensions are indices: returns element type
        - If any dimension is a range: returns array type
        """
        has_range = any(d["type"] == "range" for d in dimensions)

        if not has_range:
            # All indices - returns single element
            return self._getFinalElementType(len(dimensions))
        else:
            # Has ranges - returns array (possibly lower dimensional)
            # For now, keep original type - C will handle dimension reduction
            return self.return_type

    def _getFinalElementType(self, dimensions: int) -> str | None:
        """
        Get the element type after indexing N dimensions.

        E.g., for Tile[][][]:
        - 1 dimension indexed: Tile[][]
        - 2 dimensions indexed: Tile[]
        - 3 dimensions indexed: Tile
        """
        if not self.return_type:
            return None

        # Strip dimensions from array type
        type_str = self.return_type
        for _ in range(dimensions):
            if type_str.endswith("[]"):
                type_str = type_str[:-2]
            elif type_str.startswith("["):
                # JNI style - more complex
                if type_str.startswith("[L"):
                    return type_str[2:-1].replace("/", ".")
                else:
                    # Primitive array
                    return type_str[1:]

        return type_str if type_str != self.return_type else None

    def _getElementType(self) -> str | None:
        """
        Extract element type from array type (one dimension).
        E.g., "net.runelite.api.Player[]" -> "net.runelite.api.Player"
        E.g., "List[Player]" -> "Player"
        E.g., "List['WidgetProxy']" -> "Widget"
        """
        if self.return_type:
            # Check for List[...] pattern from generated proxies
            if self.return_type.startswith("List["):
                # Extract type from various formats:
                # List[Player] -> Player
                # List['PlayerProxy'] -> Player
                # List[List[Tile]] -> List[Tile]
                import re

                # Try quoted proxy format: List['TypeProxy']
                match = re.match(r"List\['(\w+)Proxy'\]", self.return_type)
                if match:
                    return match.group(1)  # Return just the class name

                # Try unquoted format: List[Type]
                match = re.match(r"List\[(\w+)\]", self.return_type)
                if match:
                    return match.group(1)  # Return the class name

                # Try nested format: List[List[...]]
                match = re.match(r"List\[(List\[.+\])\]", self.return_type)
                if match:
                    return match.group(1)  # Return the inner List type

            # Check for Java-style array notation
            elif self.return_type.endswith("[]"):
                return self.return_type[:-2]  # Remove the []
            elif self.return_type.startswith("["):
                # JNI style array type (handle multi-dimensional arrays)
                # Check for multi-dimensional FIRST (before single-dimensional)
                if self.return_type.startswith("[["):
                    # Multi-dimensional array: [[Lnet/runelite/api/Tile; -> [Lnet/runelite/api/Tile;
                    # Remove one level of brackets
                    return self.return_type[1:]
                elif self.return_type.startswith("[L"):
                    # Single-dimensional object array: [Lnet/runelite/api/Player; -> net.runelite.api.Player
                    return self.return_type[2:-1].replace("/", ".")
                elif self.return_type == "[Z":
                    return "boolean"
                elif self.return_type == "[I":
                    return "int"
                # Add more primitive types as needed
        return None

    def _getProxyClassForType(self, type_name: str):
        """
        Get the proxy class for a given Java type.
        E.g., "net.runelite.api.Player" -> PlayerProxy
        """
        # Try to get from generated proxies
        if _USE_GENERATED_PROXIES and PROXY_CLASSES:
            # Extract just the class name from full path
            class_name = type_name.split(".")[-1] if "." in type_name else type_name

            # Look for the proxy class (keys in PROXY_CLASSES don't have "Proxy" suffix)
            return PROXY_CLASSES.get(class_name)

        # Fallback to manual proxies
        if type_name == "net.runelite.api.Player" or type_name == "Player":
            return PlayerProxy
        elif type_name == "net.runelite.api.widgets.Widget" or type_name == "Widget":
            # Note: Some signatures incorrectly have Widget without widgets package
            return None  # Would need WidgetProxy import
        elif type_name == "net.runelite.api.coords.WorldPoint" or type_name == "WorldPoint":
            return WorldPointProxy

        return None

    def default(self, default_value: Any) -> "QueryRef":
        """
        Provide a default value if this reference is null.
        Implements null coalescing for safe navigation.

        Args:
            default_value: Value to use if this reference is null

        Returns:
            New QueryRef that will have the default value if original is null
        """
        # Create a coalesce operation
        new_ref_id = f"r{self.query.ref_counter}"
        self.query.ref_counter += 1

        # Convert default value to proper format
        if isinstance(default_value, QueryRef):
            default_ref = default_value.ref_id
        else:
            default_ref = {"$literal": default_value}

        # Record the coalesce operation
        operation = {
            "ref": new_ref_id,
            "type": "coalesce",
            "source": self.ref_id,
            "default": default_ref,
        }
        self.query.operations.append(operation)

        # Create and return new QueryRef
        new_ref = QueryRef(self.query, new_ref_id, self, self.return_type)
        self.query.refs[new_ref_id] = new_ref
        return new_ref

    def _field(self, field_name: str) -> "QueryRef":
        """
        Access a public field on the Java object.

        This is used for objects with public fields rather than getter methods,
        like java.awt.Point which has public int fields x and y.

        Args:
            field_name: Name of the field to access (e.g., "x", "y")

        Returns:
            QueryRef to the field value

        Example:
            >>> canvas_point = q.callStatic('Perspective', 'localToCanvas', q.client, lp, 0)
            >>> x = canvas_point._field('x')
            >>> y = canvas_point._field('y')
            >>> result = q.execute({'x': x, 'y': y})
        """
        # Check cache first to avoid duplicate operations
        if field_name in self._field_cache:
            return self._field_cache[field_name]

        # Generate new ref ID for the field value
        new_ref_id = f"r{self.query.ref_counter}"
        self.query.ref_counter += 1

        # Create field_get operation
        operation = {
            "ref": new_ref_id,
            "type": "field_get",
            "target": self.ref_id,
            "field": field_name,
        }

        self.query.operations.append(operation)

        # Track dependency
        if new_ref_id not in self.query.dependency_graph:
            self.query.dependency_graph[new_ref_id] = set()
        self.query.dependency_graph[new_ref_id].add(self.ref_id)

        # Create and return new QueryRef
        new_ref = QueryRef(self.query, new_ref_id, None, None)
        self.query.refs[new_ref_id] = new_ref

        # Cache it
        self._field_cache[field_name] = new_ref

        return new_ref

    def __getattr__(self, name: str):
        """
        Handle dynamic method calls and field access.
        For methods: returns a callable that creates a method call ref when invoked
        For fields: returns a QueryRef to the field value
        """
        # Don't intercept private attributes, special methods, or actual instance attributes
        if name.startswith("_") or name in ("query", "ref_id", "source_ref", "return_type"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        # Try to determine if this is a field or method by checking if it exists as a method
        # If it's a known method with 0 args, it could be either - default to method
        # If it's not a known method, assume it's a field access

        # Check if this is a known method
        is_method = False
        if self.return_type:
            # Try to find this as a method with 0 arguments
            sig = self.query.api.getMethodSignature(name, [], self.return_type)
            if sig:
                is_method = True

        if not is_method:
            # Assume it's a field access - return the field QueryRef directly
            return self._field(name)

        # It's a method - return a callable that will create a ref when invoked
        def dynamicMethod(*args, **kwargs):
            # Look up BOTH signature AND declaring_class from the API data
            method_info = self.query.api.getMethodInfo(name, list(args), self.return_type)
            if not method_info:
                raise AttributeError(
                    f"Method '{name}' not found for type '{self.return_type}' "
                    f"with {len(args)} argument(s)"
                )
            return self._createRef(
                name,
                method_info["signature"],
                *args,
                declaring_class=method_info["declaring_class"],
                **kwargs,
            )

        return dynamicMethod

    def __repr__(self) -> str:
        return f"QueryRef({self.ref_id}, type={self.return_type})"


class Query:
    """
    Builds and tracks a full query for batch execution.
    Manages operations, references, and generates JSON for execution.
    Includes optimization for large batches.
    Now with Pythonic extensions for functional operations.
    """

    # Type hints for constructors/static classes (accessed via __getattr__)
    if TYPE_CHECKING:
        WorldPoint: _WorldPointConstructor
        LocalPoint: _LocalPointConstructor
        Perspective: _PerspectiveConstructor
        Dimension: _GenericConstructor
        Point: _GenericConstructor
        Rectangle: _GenericConstructor
        WorldArea: _GenericConstructor

    # Type hints for runtime accessors
    if TYPE_CHECKING:
        client: ClientProxy  # Root client reference with full type hints
    else:
        client: Any  # Runtime: will be ClientProxy or QueryRef

    plugin: PluginAccessor

    def __init__(self, api: "RuneLiteAPI", optimize: bool = True):
        """
        Initialize a new Query.

        Args:
            api: RuneLiteAPI instance for execution
            optimize: Whether to optimize queries (default True)
        """
        # Ensure proxies are loaded
        _loadProxies()

        self.api = api
        self.operations: List[Dict[str, Any]] = []
        self.selections: Dict[str, Dict[str, Any]] = {}
        self.refs: Dict[str, QueryRef] = {}
        self.ref_counter = 1
        self.optimize = optimize

        # Optimization tracking
        self.operation_cache: Dict[str, str] = {}  # Maps operation signatures to ref IDs
        self.dependency_graph: Dict[str, Set[str]] = {}  # Maps ref to its dependencies

        # Template caching
        self.template_id: str | None = None
        self.use_template: bool = True  # Enable template caching by default

        # Lambda compiler for Pythonic operations
        self.lambda_compiler = None
        try:
            from .pythonic_query import LambdaCompiler

            self.lambda_compiler = LambdaCompiler(self)
        except ImportError:
            pass  # Pythonic features not available

        # Create root client reference
        self.client = self._createClientRef()

        # Create plugin accessor
        self.plugin = self._createPluginAccessor()

        # Create bridge helpers accessor
        self.bridge = BridgeHelpersAccessor(self)

        # NULL marker for explicit null values
        self.NULL = {"$null": True}

        # Initialize class accessor for Pythonic constructor/static method access
        try:
            if _query_proxies and hasattr(_query_proxies, "QueryClassAccessor"):
                self._class_accessor = _query_proxies.QueryClassAccessor(self)
            else:
                self._class_accessor = None
        except Exception:
            self._class_accessor = None

    def _createClientRef(self) -> "ClientProxy":
        """
        Create the root client reference.

        Returns:
            QueryRef for the RuneLite client (generated proxy or basic QueryRef)
        """
        if _USE_GENERATED_PROXIES and GeneratedClientProxy:
            # Create a QueryRef first, then wrap it in the generated proxy
            client_ref = QueryRef(self, "client", None, "net.runelite.api.Client")
            # Wrap the QueryRef in the generated proxy for better type hints
            client_proxy = GeneratedClientProxy(client_ref)
            self.refs["client"] = client_ref
            return client_proxy
        else:
            # Fall back to basic QueryRef - dynamic proxy system will handle method calls
            client_ref = QueryRef(self, "client", None, "net.runelite.api.Client")
            self.refs["client"] = client_ref
            return client_ref

    def _createPluginAccessor(self) -> "PluginAccessor":
        """
        Create the plugin accessor for querying RuneLite plugins.

        Returns:
            PluginAccessor instance for accessing loaded plugins
        """
        return PluginAccessor(self)

    def _getRequiredRefs(self, selections: Dict[str, Any]) -> Set[str]:
        """
        Get all refs required for the given selections.
        Implements dead code elimination.

        Args:
            selections: The selections dict

        Returns:
            Set of required ref IDs
        """
        required = set()

        def extractRefs(sel):
            if isinstance(sel, dict):
                sel_type = sel.get("type")
                if sel_type == "ref":
                    # Single reference
                    required.add(sel["ref"])
                elif sel_type == "list":
                    # List of items - recursively process each
                    for item in sel.get("items", []):
                        extractRefs(item)
                elif sel_type == "nested":
                    # Nested selections
                    for sub_sel in sel.get("selections", {}).values():
                        extractRefs(sub_sel)
                # Also handle old format for backward compatibility
                elif "ref" in sel and "type" not in sel:
                    required.add(sel["ref"])
                elif "refs" in sel and "type" not in sel:
                    for ref_id in sel["refs"]:
                        required.add(ref_id)
            elif isinstance(sel, QueryRef):
                required.add(sel.ref_id)

        for selection in selections.values():
            extractRefs(selection)

        # Add all dependencies of required refs
        added = True
        while added:
            added = False
            for ref in list(required):
                if ref in self.dependency_graph:
                    for dep in self.dependency_graph[ref]:
                        if dep not in required:
                            required.add(dep)
                            added = True

        return required

    def _detectAndCompressPatterns(self, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect repeating patterns and compress them into pattern operations.
        Single-pass, efficient detection with minimal overhead.

        Args:
            operations: List of operations to analyze

        Returns:
            Compressed list with patterns replaced by pattern operations
        """
        if len(operations) < 20:  # Too small to have meaningful patterns
            return operations

        compressed = []
        i = 0

        while i < len(operations):
            # Quick check: Is this a potential getItem pattern?
            if (
                i + 2 < len(operations)
                and operations[i].get("method") == "getItem"
                and operations[i + 1].get("target") == operations[i]["ref"]
            ):
                # Detect the pattern signature
                pattern_info = self._detectGetitemPattern(operations, i)

                if pattern_info and pattern_info["count"] >= 10:
                    # Found a significant pattern - compress it
                    compressed.append(self._createPatternOperation(pattern_info))
                    i = pattern_info["end_index"]
                    continue

            # Not part of a pattern or pattern too small
            compressed.append(operations[i])
            i += 1

        return compressed

    def _detectGetitemPattern(
        self, operations: List[Dict[str, Any]], start_idx: int
    ) -> Dict | None:
        """
        Detect getItem loop pattern starting at given index.
        Returns pattern info if found, None otherwise.
        """
        first_op = operations[start_idx]
        if first_op.get("method") != "getItem":
            return None

        container_ref = first_op["target"]

        # Detect what methods are called on each item
        accessor_methods = []
        i = start_idx + 1
        while i < len(operations) and operations[i].get("target") == first_op["ref"]:
            accessor_methods.append(operations[i]["method"])
            i += 1

        if not accessor_methods:
            return None

        # Pattern signature: methods called on each item
        pattern_length = 1 + len(accessor_methods)  # getItem + accessors

        # Count how many times this pattern repeats
        indices = []
        refs = []
        j = start_idx

        while j + pattern_length <= len(operations):
            # Check if pattern continues
            if (
                operations[j].get("method") != "getItem"
                or operations[j].get("target") != container_ref
            ):
                break

            # Verify accessor methods match
            item_ref = operations[j]["ref"]
            match = True
            for k, method in enumerate(accessor_methods):
                if (
                    j + k + 1 >= len(operations)
                    or operations[j + k + 1].get("method") != method
                    or operations[j + k + 1].get("target") != item_ref
                ):
                    match = False
                    break

            if not match:
                break

            # Extract index and refs
            if operations[j].get("args"):
                idx = operations[j]["args"][0] if operations[j]["args"] else 0
                indices.append(idx if isinstance(idx, int) else int(idx))

            # Store ref mapping for result reconstruction
            ref_map = {"item": item_ref}
            for k, method in enumerate(accessor_methods):
                ref_map[method] = operations[j + k + 1]["ref"]
            refs.append(ref_map)

            j += pattern_length

        return {
            "type": "getItem_loop",
            "container": container_ref,
            "indices": indices,
            "accessors": accessor_methods,
            "refs": refs,
            "count": len(indices),
            "start_index": start_idx,
            "end_index": j,
        }

    def _createPatternOperation(self, pattern_info: Dict) -> Dict:
        """
        Create a compressed pattern operation from pattern info.
        """
        # Generate a unique ref for this pattern
        pattern_ref = f"pattern_{pattern_info['refs'][0]['item']}"

        # Format args as the C code expects them
        return {
            "type": "pattern",
            "ref": pattern_ref,
            "args": [
                pattern_info["type"],  # arg[0] = pattern_type (e.g., "getItem_loop")
                pattern_info["container"],  # arg[1] = container ref
                json.dumps(pattern_info["indices"]),  # arg[2] = indices JSON array
                json.dumps(pattern_info["accessors"]),  # arg[3] = accessor methods JSON array
                json.dumps(pattern_info["refs"]),  # arg[4] = ref_mappings JSON array
            ],
        }

    def _mergeConsecutiveSlices(self, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge consecutive sliceArray operations into multi-dimensional slices.

        This optimization handles cases like:
            tiles[plane][x_start:x_end][y_start:y_end]

        Which generates:
            r4 = r2[r3]           # Index by plane
            r5 = r4[23:87]        # Slice first dimension
            r6 = r5[18:82]        # Slice second dimension

        And merges them into:
            r4 = r2[r3]           # Index by plane
            r6 = r4[23:87, 18:82] # Multi-dimensional slice

        Args:
            operations: List of operations to optimize

        Returns:
            List of operations with consecutive slices merged
        """
        if not operations:
            return operations

        # Build a mapping of ref -> operation for fast lookup
        ref_to_op = {op["ref"]: op for op in operations}

        # Build a mapping of target -> operations that use it
        target_to_ops = {}
        for op in operations:
            target = op.get("target")
            if target:
                if target not in target_to_ops:
                    target_to_ops[target] = []
                target_to_ops[target].append(op)

        # Track which operations have been merged (to skip them later)
        merged_refs = set()

        # Result list
        result = []

        for op in operations:
            # Skip if already merged into another operation
            if op["ref"] in merged_refs:
                continue

            # Only process sliceArray operations
            if op.get("type") != "sliceArray":
                result.append(op)
                continue

            # Check if this operation has a consumer that is also a sliceArray
            # If so, skip it - it will be merged when we process the final operation
            consumers = target_to_ops.get(op["ref"], [])
            has_slice_consumer = any(c.get("type") == "sliceArray" for c in consumers)

            if has_slice_consumer:
                # This will be merged later, skip for now
                merged_refs.add(op["ref"])
                continue

            # This is the final operation in a chain (or a standalone slice)
            # Walk backward to collect the full chain
            chain = []
            current_op = op

            while current_op:
                if current_op.get("type") == "sliceArray":
                    chain.insert(0, current_op)
                    target_ref = current_op.get("target")
                    if target_ref and target_ref.startswith("r"):
                        current_op = ref_to_op.get(target_ref)
                    else:
                        break
                else:
                    # Hit a non-slice operation, stop
                    break

            # If we have a chain of 2+ operations, merge them
            if len(chain) > 1:
                # The final operation keeps its ref, but gets all dimensions
                merged_op = chain[-1].copy()
                merged_op["target"] = chain[0].get("target")

                # Collect all dimensions from the chain
                all_dimensions = []
                for slice_op in chain:
                    dimensions = slice_op.get("dimensions", [])
                    all_dimensions.extend(dimensions)

                merged_op["dimensions"] = all_dimensions

                # Mark intermediate operations as merged (excluding the final one)
                for slice_op in chain[:-1]:
                    merged_refs.add(slice_op["ref"])

                result.append(merged_op)
            else:
                # No merge needed, keep as-is
                result.append(op)

        return result

    def _optimizeOperations(
        self, required_refs: Set[str], operations: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Optimize operations by removing dead code and reordering.

        Args:
            required_refs: Set of refs that are actually needed
            operations: Operations to optimize (default: self.operations)

        Returns:
            Optimized list of operations
        """
        # Use provided operations or default to self.operations
        if operations is None:
            operations = self.operations

        # Resolve all dependencies recursively
        all_required_refs = set(required_refs)
        to_process = list(required_refs)

        while to_process:
            ref = to_process.pop()

            # Add dependencies from dependency graph
            if ref in self.dependency_graph:
                for dep in self.dependency_graph[ref]:
                    if dep not in all_required_refs:
                        all_required_refs.add(dep)
                        to_process.append(dep)

            # Also check operation targets and arrays
            for op in operations:
                if op["ref"] == ref:
                    # Check if this operation depends on another ref
                    target = op.get("target")
                    if target and target.startswith("r") and target not in all_required_refs:
                        all_required_refs.add(target)
                        to_process.append(target)

                    array = op.get("array")
                    if array and array.startswith("r") and array not in all_required_refs:
                        all_required_refs.add(array)
                        to_process.append(array)

        # Filter to only required operations (including dependencies)
        required_ops = [op for op in operations if op["ref"] in all_required_refs]

        if not self.optimize:
            return required_ops

        # Sort operations by dependency order
        sorted_ops = []
        processed = set()

        def addOpWithDeps(ref_id: str):
            if ref_id in processed:
                return

            # Find the operation for this ref
            op = None
            for o in required_ops:
                if o["ref"] == ref_id:
                    op = o
                    break

            if not op:
                return

            # First add dependencies
            if ref_id in self.dependency_graph:
                for dep in self.dependency_graph[ref_id]:
                    addOpWithDeps(dep)

            # Also add target dependencies
            target = op.get("target")
            if target and target.startswith("r"):
                addOpWithDeps(target)

            # And array dependencies
            array = op.get("array")
            if array and array.startswith("r"):
                addOpWithDeps(array)

            # Finally add this operation
            if ref_id not in processed:
                sorted_ops.append(op)
                processed.add(ref_id)

        # Process all operations
        for op in required_ops:
            addOpWithDeps(op["ref"])

        return sorted_ops

    def __getattr__(self, name: str):
        """
        Enable Pythonic syntax for constructors and static methods.

        Usage:
            q.WorldPoint(x, y, z)  # Constructor
            q.Perspective.localToCanvas(...)  # Static method
        """
        if name.startswith("_"):
            # Don't intercept private attributes
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        # Check if it's bridgeHelpers or BridgeHelpers (handle both cases)
        if name in ("bridgeHelpers", "BridgeHelpers"):
            return self.bridge

        if self._class_accessor:
            return getattr(self._class_accessor, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def execute(self, selections: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """
        Execute the built query with optional selections.
        With optimization enabled, this will eliminate dead code and reorder operations.
        With template caching, repeated patterns execute faster.

        Args:
            selections: Dictionary mapping result names to QueryRefs or method calls

        Returns:
            Dictionary of results from the executed query
        """
        # Process selections if provided
        if selections:
            for key, value in selections.items():
                self.selections[key] = self._processSelectionValue(value)

        # Auto-detect what user wants: track the last operation if no selections
        if not selections and not self.selections:
            # Return only the last operation's result by default
            if self.operations:
                last_op = self.operations[-1]
                last_ref = last_op.get("ref")
                if last_ref:
                    self.selections["result"] = {"ref": last_ref, "type": "ref"}

        # Always merge consecutive sliceArray operations (required for plugin)
        merged_ops = self._mergeConsecutiveSlices(self.operations)

        # Optimize operations (dead code elimination + dependency ordering)
        if self.optimize or self.selections:
            required_refs = (
                self._getRequiredRefs(self.selections)
                if self.selections
                else {self.operations[-1].get("ref")}
                if self.operations
                else set()
            )
            optimized_ops = self._optimizeOperations(required_refs, merged_ops)
        else:
            optimized_ops = merged_ops

        # Execute via API (pass operations directly, no JSON serialization)
        raw_results = self._executeQuery(optimized_ops)

        # Check for errors first - if there's an error, return it with consistent structure
        if raw_results.get("error") or not raw_results.get("success"):
            return {
                "success": False,
                "error": raw_results.get("error", "Unknown error"),
                "results": None,
            }

        # If we have selections and the query succeeded, filter the results
        # Note: MessagePack v2 doesn't return a 'success' field, just 'results'
        if self.selections and raw_results.get("results") is not None:
            filtered_results = {}

            # Build ref-to-index mapping from the actual operations sent
            ref_to_index = {}
            for idx, op in enumerate(optimized_ops):
                ref_to_index[op["ref"]] = idx

            # Map selection names to their ref IDs
            for name, selection in self.selections.items():
                filtered_results[name] = self._extractSelectionResults(
                    selection, raw_results["results"], ref_to_index
                )

            # If only one selection named 'result', return just that value
            if len(filtered_results) == 1 and "result" in filtered_results:
                return filtered_results["result"]

            # Return filtered results with same structure but renamed keys
            return {
                "success": raw_results.get("success", True),  # Default to True if not present
                "results": filtered_results,
                "error": raw_results.get("error"),
            }

        # No selections - convert enums in raw results and return
        return self._convertEnumsRecursive(raw_results)

    def _processSelectionValue(self, value: Any) -> Dict[str, Any]:
        """
        Process a selection value, handling arbitrary nesting of lists and QueryRefs.

        Args:
            value: The value to process (can be QueryRef, proxy object, list, dict, or primitive)

        Returns:
            Processed selection structure
        """
        # Check if it's a proxy object with a _ref attribute
        if hasattr(value, "_ref") and isinstance(value._ref, QueryRef):
            # Proxy object - extract its QueryRef
            return {"ref": value._ref.ref_id, "type": "ref"}
        elif isinstance(value, QueryRef):
            # Direct reference selection
            return {"ref": value.ref_id, "type": "ref"}
        elif isinstance(value, list):
            # Process list recursively
            processed_items = []
            for item in value:
                processed_items.append(self._processSelectionValue(item))
            return {"items": processed_items, "type": "list"}
        elif isinstance(value, dict):
            # Nested selections (for complex results)
            return self._processNestedSelections(value)
        else:
            # Primitive value
            return {"value": value, "type": "literal"}

    def _extractSelectionResults(
        self,
        selection: Dict[str, Any],
        results: Dict[str, Any],
        ref_to_index: Dict[str, int] = None,
    ) -> Any:
        """
        Extract results for a selection, handling arbitrary nesting.

        Args:
            selection: The processed selection structure
            results: The raw results from the query
            ref_to_index: Mapping from ref IDs to array indices (for optimized queries)

        Returns:
            The extracted results matching the selection structure (with enums converted)
        """
        sel_type = selection.get("type")

        if sel_type == "ref":
            # Single reference
            ref_id = selection["ref"]
            result = None
            # Handle MessagePack v2 format where results is a list
            if isinstance(results, list):
                # Use ref_to_index mapping if available (for optimized queries)
                if ref_to_index and ref_id in ref_to_index:
                    index = ref_to_index[ref_id]
                    if 0 <= index < len(results):
                        result = results[index]
                # Fallback: Convert ref_id like "r1" to index (r1 -> 0, r2 -> 1, etc.)
                elif ref_id.startswith("r") and ref_id[1:].isdigit():
                    index = int(ref_id[1:]) - 1  # r1 -> index 0
                    if 0 <= index < len(results):
                        result = results[index]
            else:
                # Legacy dict format
                result = results.get(ref_id)

            # Convert any enums in the result
            return self._convertEnumsRecursive(result)
        elif sel_type == "list":
            # List of items - recursively extract each
            list_results = []
            for item in selection.get("items", []):
                list_results.append(self._extractSelectionResults(item, results, ref_to_index))
            return list_results
        elif sel_type == "nested":
            # Nested dictionary structure
            nested_results = {}
            for key, sub_selection in selection.get("selections", {}).items():
                nested_results[key] = self._extractSelectionResults(
                    sub_selection, results, ref_to_index
                )
            return nested_results
        elif sel_type == "literal":
            # Literal value
            return selection.get("value")
        else:
            return None

    def _convertEnumsRecursive(self, data: Any) -> Any:
        """
        Recursively convert {"$enum": {...}} dicts to Python EnumValue objects.

        Args:
            data: Any data structure (dict, list, or primitive)

        Returns:
            Data with enums converted to EnumValue objects
        """
        if isinstance(data, dict):
            # Check if this is an enum dict
            if "$enum" in data:
                enum_data = data["$enum"]
                enum_class_name = enum_data.get("class")
                ordinal = enum_data.get("ordinal")
                enum_data.get("name")

                # Get the enum class if it exists
                if enum_class_name in self.api.enum_classes:
                    enum_class = self.api.enum_classes[enum_class_name]
                    # Create EnumValue object from ordinal
                    return enum_class.from_ordinal(ordinal)
                else:
                    # Return raw data if enum class not found
                    print(f"⚠️ Unknown enum class: {enum_class_name}")
                    return data
            else:
                # Recursively process all dict values
                return {key: self._convertEnumsRecursive(value) for key, value in data.items()}
        elif isinstance(data, list):
            # Recursively process all list items
            return [self._convertEnumsRecursive(item) for item in data]
        else:
            # Return primitives as-is
            return data

    def _processNestedSelections(self, nested: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process nested selection dictionaries.

        Args:
            nested: Nested dictionary of selections

        Returns:
            Processed selection structure
        """
        result = {}
        for key, value in nested.items():
            result[key] = self._processSelectionValue(value)
        return {"type": "nested", "selections": result}

    def _executeQuery(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute the query through the RuneLite API.

        Args:
            operations: List of operation dictionaries to execute

        Returns:
            Dictionary of results
        """
        # Check if API has the batch query method
        if hasattr(self.api, "executeBatchQuery"):
            return self.api.executeBatchQuery(operations=operations)
        else:
            # Fallback for testing without bridge connection
            print(f"Would execute query with {len(operations)} operations")
            return {"_placeholder": "Not yet connected to bridge"}

    def loop(self, container_ref: QueryRef, start: int, end: int, item_func: Callable) -> QueryRef:
        """
        Optimized loop over container.getItem(i) calls.

        Args:
            container_ref: Reference to an ItemContainer
            start: Start index (inclusive)
            end: End index (exclusive)
            item_func: Lambda that gets called with each item
                      e.g., lambda item: [item.getId(), item.getQuantity()]

        Returns:
            QueryRef to the result array
        """
        # Generate unique ref ID
        new_ref_id = f"r{self.ref_counter}"
        self.ref_counter += 1

        # Compile the item function to extract what methods to call
        transform_ops = None
        if item_func and self.lambda_compiler:
            try:
                transform_ops = self.lambda_compiler.compile_lambda(item_func, ["item"])
                # Convert to dict format for JSON
                transform_ops = [op.to_dict() for op in transform_ops]
            except Exception as e:
                print(f"Warning: Failed to compile item function: {e}")

        # Create the loop operation
        operation = {
            "type": "loop",
            "ref": new_ref_id,
            "target": container_ref.ref_id,
            "args": [str(start), str(end)],
            "transform_ops": transform_ops,
        }
        self.operations.append(operation)

        # Create and return new QueryRef
        new_ref = QueryRef(self, new_ref_id, None, "array")
        self.refs[new_ref_id] = new_ref
        return new_ref

    def forEach(
        self,
        array_ref: QueryRef | Any,
        transform_func: Callable | None = None,
        skip_nulls: bool = True,
    ) -> QueryRef:
        """
        Iterate over array elements with optional transformation.

        Args:
            array_ref: Reference to an array or collection
            transform_func: Optional lambda to transform each element
                           e.g., lambda item: item.getId()
            skip_nulls: If True (default), skip null elements for efficiency.
                       If False, include nulls to preserve array indices.

        Returns:
            QueryRef to the transformed array
        """
        # Generate unique ref ID
        new_ref_id = f"r{self.ref_counter}"
        self.ref_counter += 1

        # Convert array_ref if needed
        if isinstance(array_ref, QueryRef):
            array_ref_id = array_ref.ref_id
            # Extract element type from array return_type for better method resolution
            element_type = None
            if array_ref.return_type:
                rt = array_ref.return_type
                # Handle array types: "[Lnet/runelite/api/NPC;" -> "net/runelite/api/NPC"
                # Also handle multi-dimensional: "[[Lnet/runelite/api/Tile;" -> "net/runelite/api/Tile"
                # First check if it's an array type (starts with '[')
                if rt.startswith("["):
                    # Strip ALL leading [ characters
                    stripped = rt.lstrip("[")
                    # Now check if it's JNI object format: "Lnet/runelite/api/ClassName;"
                    if stripped.startswith("L") and stripped.endswith(";"):
                        element_type = stripped[1:-1]  # Remove L prefix and ; suffix
                    else:
                        # Primitive array or unknown format
                        element_type = stripped
                # Handle JNI format without array: "Lnet/runelite/api/Tile;" -> "net/runelite/api/Tile"
                elif rt.startswith("L") and rt.endswith(";"):
                    element_type = rt[1:-1]  # Remove L prefix and ; suffix
                # Handle already-extracted generic type: "net/runelite/api/NPC"
                elif rt.startswith("net/runelite/api/"):
                    element_type = rt  # Already in correct format
                # Handle simple array format: "GameObject[]" -> need to look up full path
                elif rt.endswith("[]"):
                    simple_name = rt[:-2]  # Remove [] suffix
                    # Try to find full path from class_packages in API data
                    if hasattr(self, "api") and "class_packages" in self.api.api_data:
                        package_path = self.api.api_data["class_packages"].get(simple_name)
                        if package_path:
                            # class_packages stores package path, need to append class name
                            element_type = f"{package_path}/{simple_name}"
                        else:
                            # Fallback: assume it's in base API package
                            element_type = f"net/runelite/api/{simple_name}"
                    else:
                        element_type = f"net/runelite/api/{simple_name}"
                # Handle simple class name without array: "WorldPoint" -> look up full path
                elif "/" not in rt and "." not in rt:
                    # Simple class name, need to look up full path
                    if hasattr(self, "api") and "class_packages" in self.api.api_data:
                        package_path = self.api.api_data["class_packages"].get(rt)
                        if package_path:
                            # class_packages stores package path, need to append class name
                            element_type = f"{package_path}/{rt}"
                        else:
                            # Check common packages
                            if rt in ["WorldPoint", "LocalPoint", "WorldArea"]:
                                element_type = f"net/runelite/api/coords/{rt}"
                            else:
                                element_type = f"net/runelite/api/{rt}"
                    else:
                        element_type = f"net/runelite/api/{rt}"
        else:
            # array_ref is not a QueryRef, treat as literal
            array_ref_id = str(array_ref)
            element_type = None

        # Try to extract method names or patterns from lambda
        method_name = None
        method_list = None
        transform_ops = None

        if transform_func:
            try:
                import inspect
                import re
                import sys

                # Get lambda source code
                source = inspect.getsource(transform_func).strip()

                # Extract just the lambda part if it's embedded in a larger statement
                # Find "lambda" keyword and extract to the end, handling nested parentheses
                lambda_start = source.find("lambda")
                if lambda_start >= 0:
                    # Find the colon after lambda
                    colon_pos = source.find(":", lambda_start)
                    if colon_pos >= 0:
                        # Extract from lambda to end, then balance parentheses
                        remaining = source[lambda_start:]
                        paren_count = 0
                        bracket_count = 0
                        end_pos = len(remaining)

                        for i, char in enumerate(remaining):
                            if char == "(":
                                paren_count += 1
                            elif char == ")":
                                paren_count -= 1
                                # If we go negative, we've hit the closing paren of forEach()
                                if paren_count < 0:
                                    end_pos = i
                                    break
                            elif char == "[":
                                bracket_count += 1
                            elif char == "]":
                                bracket_count -= 1

                        source = remaining[:end_pos].strip()

                # Extract variable name from lambda
                param_match = re.match(r"lambda\s+(\w+)\s*:", source)
                if not param_match:
                    pass  # Can't parse lambda
                else:
                    item_var = param_match.group(1)

                    # Extract the lambda body (everything after the colon)
                    body_match = re.search(r"lambda\s+\w+\s*:\s*(.+)", source)
                    if body_match:
                        lambda_body = body_match.group(1).strip()

                        # Check for list pattern FIRST: lambda item: [item.method1(), item.method2()]
                        # OR list of chains: [item.getWorldLocation().getX(), item.getWorldLocation().getY()]
                        # This must be checked before simple chains because chains can appear inside lists
                        list_match = re.search(r"lambda\s+(\w+)\s*:\s*\[", source)
                        if list_match:
                            item_var = list_match.group(1)
                            # Find the matching closing bracket
                            start_pos = list_match.end() - 1
                            bracket_count = 0
                            end_pos = start_pos
                            for i, char in enumerate(source[start_pos:], start=start_pos):
                                if char == "[":
                                    bracket_count += 1
                                elif char == "]":
                                    bracket_count -= 1
                                    if bracket_count == 0:
                                        end_pos = i
                                        break

                            list_content = source[start_pos + 1 : end_pos]

                            # Split by comma to get individual expressions
                            # Simple split (doesn't handle nested parens/brackets, but good enough for now)
                            expressions = [expr.strip() for expr in list_content.split(",")]

                            # Check if these are chains or simple methods
                            has_chains = any(
                                "." in expr.replace(f"{item_var}.", "", 1) for expr in expressions
                            )

                            if has_chains:
                                # Build list of transform_ops (one per chain)
                                chains_list = []
                                for expr in expressions:
                                    # Extract all methods in this chain
                                    all_methods = re.findall(
                                        rf"{item_var}\.(\w+)\(\)|\.(\w+)\(\)", expr
                                    )
                                    methods_chain = [m[0] if m[0] else m[1] for m in all_methods]

                                    if methods_chain:
                                        # Build transform_ops for this chain
                                        chain_ops = []
                                        missing_methods = []
                                        current_type = element_type  # Start with array element type
                                        for method in methods_chain:
                                            method_info = self.api.getMethodInfo(
                                                method, [], target_class=current_type
                                            )
                                            if method_info:
                                                chain_ops.append(
                                                    {
                                                        "type": "method",
                                                        "method": method,
                                                        "signature": method_info["signature"],
                                                        "declaring_class": method_info[
                                                            "declaring_class"
                                                        ],
                                                        "args": [],
                                                    }
                                                )
                                                # Update current_type for next method in chain
                                                sig = method_info["signature"]
                                                paren_end = sig.rfind(")")
                                                if paren_end >= 0:
                                                    ret_sig = sig[paren_end + 1 :]
                                                    if ret_sig.startswith("L") and ret_sig.endswith(
                                                        ";"
                                                    ):
                                                        current_type = ret_sig[1:-1]
                                            else:
                                                # Method not found on current_type - check if it exists elsewhere
                                                if method in self.api.api_data["methods"]:
                                                    # Use current_type as declaring_class with signature from API
                                                    any_entry = self.api.api_data["methods"][
                                                        method
                                                    ][0]
                                                    fallback_sig = any_entry[1]
                                                    import sys

                                                    print(
                                                        f"⚠️  Warning: Method '{method}' not found for type '{current_type}'",
                                                        file=sys.stderr,
                                                    )
                                                    print(
                                                        "   Using current_type as declaring_class.",
                                                        file=sys.stderr,
                                                    )
                                                    chain_ops.append(
                                                        {
                                                            "type": "method",
                                                            "method": method,
                                                            "signature": fallback_sig,
                                                            "declaring_class": current_type,
                                                            "args": [],
                                                        }
                                                    )
                                                    # Update current_type
                                                    paren_end = fallback_sig.rfind(")")
                                                    if paren_end >= 0:
                                                        ret_sig = fallback_sig[paren_end + 1 :]
                                                        if ret_sig.startswith(
                                                            "L"
                                                        ) and ret_sig.endswith(";"):
                                                            current_type = ret_sig[1:-1]
                                                else:
                                                    missing_methods.append(method)

                                        if missing_methods:
                                            import sys

                                            print(
                                                f"❌ ERROR: Method(s) not found in RuneLite API: {', '.join(missing_methods)}",
                                                file=sys.stderr,
                                            )
                                            print(
                                                "   Check spelling and API documentation.",
                                                file=sys.stderr,
                                            )
                                            for missing in missing_methods:
                                                similar = self.api.find_similar_methods(missing)
                                                if similar:
                                                    print(
                                                        f"   Did you mean: {', '.join(similar[:3])}?",
                                                        file=sys.stderr,
                                                    )
                                            raise ValueError(
                                                f"Method(s) not found: {', '.join(missing_methods)}"
                                            )

                                        if chain_ops:
                                            chains_list.append(chain_ops)

                                if chains_list:
                                    # Store as list of chains
                                    transform_ops = chains_list
                            else:
                                # Simple methods (no chains) - build transform_ops with signatures
                                methods = re.findall(rf"{item_var}\.(\w+)\(\)", list_content)
                                if methods:
                                    # Build transform_ops for each method
                                    method_ops = []
                                    missing_methods = []
                                    for method in methods:
                                        method_info = self.api.getMethodInfo(
                                            method, [], target_class=element_type
                                        )
                                        if method_info:
                                            method_ops.append(
                                                {
                                                    "type": "method",
                                                    "method": method,
                                                    "signature": method_info["signature"],
                                                    "declaring_class": method_info[
                                                        "declaring_class"
                                                    ],
                                                    "args": [],
                                                }
                                            )
                                        else:
                                            missing_methods.append(method)

                                    if missing_methods:
                                        import sys

                                        print(
                                            f"❌ ERROR: Method(s) not found in RuneLite API: {', '.join(missing_methods)}",
                                            file=sys.stderr,
                                        )
                                        print(
                                            "   Check spelling and API documentation.",
                                            file=sys.stderr,
                                        )
                                        # Suggest similar method names
                                        for missing in missing_methods:
                                            similar = self.api.find_similar_methods(missing)
                                            if similar:
                                                print(
                                                    f"   Did you mean: {', '.join(similar[:3])}?",
                                                    file=sys.stderr,
                                                )
                                        raise ValueError(
                                            f"Method(s) not found: {', '.join(missing_methods)}"
                                        )

                                    if method_ops:
                                        # Store as list of single-method ops (not chains)
                                        transform_ops = [[op] for op in method_ops]
                                    else:
                                        # Fallback to method_list if signatures not found
                                        method_list = methods
                        # Check for dict pattern: lambda item: {"key1": item.method1(), "key2": item.method2()}
                        elif re.search(r"lambda\s+(\w+)\s*:\s*\{", source):
                            dict_match = re.search(r"lambda\s+(\w+)\s*:\s*\{", source)
                            item_var = dict_match.group(1)
                            # Find the matching closing brace
                            start_pos = dict_match.end() - 1
                            brace_count = 0
                            end_pos = start_pos
                            for i, char in enumerate(source[start_pos:], start=start_pos):
                                if char == "{":
                                    brace_count += 1
                                elif char == "}":
                                    brace_count -= 1
                                    if brace_count == 0:
                                        end_pos = i
                                        break

                            dict_content = source[start_pos + 1 : end_pos]

                            # Extract key-value pairs: "key": item.method() or "key": item.chain().method()
                            # Pattern: "key": expression
                            kv_pattern = r'"(\w+)"\s*:\s*([^,}]+)'
                            kv_matches = re.findall(kv_pattern, dict_content)

                            if kv_matches:
                                # Build dict structure with keys and transform ops
                                dict_ops = {}
                                for key, expr in kv_matches:
                                    # Extract methods from expression
                                    all_methods = re.findall(
                                        rf"{item_var}\.(\w+)\(\)|\.(\w+)\(\)", expr
                                    )
                                    methods_chain = [m[0] if m[0] else m[1] for m in all_methods]

                                    if methods_chain:
                                        # Build transform_ops for this chain
                                        chain_ops = []
                                        current_type = element_type  # Start with array element type
                                        for method in methods_chain:
                                            method_info = self.api.getMethodInfo(
                                                method, [], target_class=current_type
                                            )
                                            if method_info:
                                                chain_ops.append(
                                                    {
                                                        "type": "method",
                                                        "method": method,
                                                        "signature": method_info["signature"],
                                                        "declaring_class": method_info[
                                                            "declaring_class"
                                                        ],
                                                        "args": [],
                                                    }
                                                )
                                                # Update current_type for next method in chain
                                                sig = method_info["signature"]
                                                paren_end = sig.rfind(")")
                                                if paren_end >= 0:
                                                    ret_sig = sig[paren_end + 1 :]
                                                    if ret_sig.startswith("L") and ret_sig.endswith(
                                                        ";"
                                                    ):
                                                        current_type = ret_sig[1:-1]
                                            else:
                                                # Method not found - use fallback
                                                if method in self.api.api_data["methods"]:
                                                    any_entry = self.api.api_data["methods"][
                                                        method
                                                    ][0]
                                                    fallback_sig = any_entry[1]
                                                    import sys

                                                    print(
                                                        f"⚠️  Warning: Method '{method}' not found for type '{current_type}'",
                                                        file=sys.stderr,
                                                    )
                                                    chain_ops.append(
                                                        {
                                                            "type": "method",
                                                            "method": method,
                                                            "signature": fallback_sig,
                                                            "declaring_class": current_type,
                                                            "args": [],
                                                        }
                                                    )
                                                    paren_end = fallback_sig.rfind(")")
                                                    if paren_end >= 0:
                                                        ret_sig = fallback_sig[paren_end + 1 :]
                                                        if ret_sig.startswith(
                                                            "L"
                                                        ) and ret_sig.endswith(";"):
                                                            current_type = ret_sig[1:-1]

                                        if chain_ops:
                                            dict_ops[key] = chain_ops

                                if dict_ops:
                                    # Store as dict with transform_ops
                                    transform_ops = {"_dict": dict_ops}
                        else:
                            # Not a list - check for chained method calls or simple method
                            # Pattern: item.method1().method2().method3()
                            chained_pattern = rf"{item_var}\.(\w+)\(\)" + r"(?:\.(\w+)\(\))+"
                            chained_match = re.search(chained_pattern, lambda_body)

                            if chained_match:
                                # Extract all methods in the chain
                                all_methods = re.findall(
                                    rf"{item_var}\.(\w+)\(\)|\.(\w+)\(\)", lambda_body
                                )
                                # Flatten the tuple results
                                methods_chain = [m[0] if m[0] else m[1] for m in all_methods]

                                if len(methods_chain) > 1:
                                    # Build transform_ops array for chained calls
                                    transform_ops = []
                                    current_type = element_type  # Start with array element type
                                    for method in methods_chain:
                                        # Look up signature and declaring class from API using current type
                                        method_info = self.api.getMethodInfo(
                                            method, [], target_class=current_type
                                        )

                                        if method_info:
                                            transform_ops.append(
                                                {
                                                    "type": "method",
                                                    "method": method,
                                                    "signature": method_info["signature"],
                                                    "declaring_class": method_info[
                                                        "declaring_class"
                                                    ],
                                                    "return_type": method_info.get(
                                                        "return_type"
                                                    ),  # Include generic type info
                                                    "args": [],
                                                }
                                            )
                                            # Update current_type for next method in chain
                                            # Extract return type from signature for accurate chaining
                                            sig = method_info["signature"]
                                            paren_end = sig.rfind(")")
                                            if paren_end >= 0:
                                                ret_sig = sig[paren_end + 1 :]
                                                if ret_sig.startswith("L") and ret_sig.endswith(
                                                    ";"
                                                ):
                                                    # Extract full path: Ljava/awt/Shape; -> java/awt/Shape
                                                    current_type = ret_sig[1:-1]
                                        else:
                                            # Method not found in scraped API (e.g., java.awt.* methods)
                                            # Check if we're dealing with an external class
                                            is_external = (
                                                current_type.startswith("java/")
                                                or current_type.startswith("javax/")
                                                or current_type.startswith("sun/")
                                            )

                                            if is_external:
                                                import sys

                                                # Detect if this is the LAST method in the chain
                                                method_index = methods_chain.index(method)
                                                is_last = method_index == len(methods_chain) - 1

                                                if (
                                                    is_last
                                                    and method in self.api.api_data["methods"]
                                                ):
                                                    # This is the LAST method, we can allow it
                                                    any_entry = self.api.api_data["methods"][
                                                        method
                                                    ][0]
                                                    fallback_sig = any_entry[1]
                                                    print(
                                                        f"⚠️  Warning: Calling '{method}' on external type '{current_type}'",
                                                        file=sys.stderr,
                                                    )
                                                    print(
                                                        "   This is the last method in chain - JNI will resolve at runtime.",
                                                        file=sys.stderr,
                                                    )

                                                    transform_ops.append(
                                                        {
                                                            "type": "method",
                                                            "method": method,
                                                            "signature": fallback_sig,
                                                            "declaring_class": current_type,
                                                            "return_type": any_entry[2]
                                                            if len(any_entry) > 2
                                                            else None,
                                                            "args": [],
                                                        }
                                                    )
                                                    break  # Don't update current_type, this is the end
                                                else:
                                                    # NOT the last method - cannot chain further on external types
                                                    print(
                                                        f"❌ ERROR: Cannot chain methods on external Java class '{current_type}'",
                                                        file=sys.stderr,
                                                    )
                                                    print(
                                                        f"   Method '{method}' returns a type not in the scraped RuneLite API.",
                                                        file=sys.stderr,
                                                    )
                                                    print(
                                                        "   Chaining is only supported on RuneLite API types.",
                                                        file=sys.stderr,
                                                    )
                                                    print(
                                                        f"   Chain attempted: {' -> '.join(methods_chain)}",
                                                        file=sys.stderr,
                                                    )
                                                    raise ValueError(
                                                        f"Cannot chain methods on external class '{current_type}'. "
                                                        f"Method '{method}' is not the last in chain: {' -> '.join(methods_chain)}"
                                                    )
                                            elif method in self.api.api_data["methods"]:
                                                # Not external, just not found for this specific type
                                                any_entry = self.api.api_data["methods"][method][0]
                                                fallback_sig = any_entry[1]
                                                import sys

                                                print(
                                                    f"⚠️  Warning: Method '{method}' not found for type '{current_type}'",
                                                    file=sys.stderr,
                                                )
                                                print(
                                                    "   Using current_type as declaring_class.",
                                                    file=sys.stderr,
                                                )

                                                transform_ops.append(
                                                    {
                                                        "type": "method",
                                                        "method": method,
                                                        "signature": fallback_sig,
                                                        "declaring_class": current_type,
                                                        "return_type": any_entry[2]
                                                        if len(any_entry) > 2
                                                        else None,
                                                        "args": [],
                                                    }
                                                )

                                                # Update current_type from signature
                                                paren_end = fallback_sig.rfind(")")
                                                if paren_end >= 0:
                                                    ret_sig = fallback_sig[paren_end + 1 :]
                                                    if ret_sig.startswith("L") and ret_sig.endswith(
                                                        ";"
                                                    ):
                                                        current_type = ret_sig[1:-1]
                                            else:
                                                # Method doesn't exist anywhere - this will fail
                                                import sys

                                                print(
                                                    f"❌ ERROR: Method '{method}' not found in RuneLite API",
                                                    file=sys.stderr,
                                                )
                                                break  # Stop processing this chain

                                    if len(transform_ops) == 0:
                                        transform_ops = None  # Couldn't find signatures
                                elif len(transform_ops) == 1:
                                    # Single method - keep as transform_ops for consistency
                                    pass
                                else:
                                    # Multiple methods successfully parsed
                                    pass
                            else:
                                # Check for simple single method: item.method()
                                simple_match = re.search(
                                    rf"lambda\s+{item_var}\s*:\s*{item_var}\.(\w+)\(\)", source
                                )
                                if simple_match:
                                    # Create transform_ops for single method instead of method_name
                                    method = simple_match.group(1)
                                    method_info = self.api.getMethodInfo(
                                        method, [], target_class=element_type
                                    )
                                    if method_info:
                                        transform_ops = [
                                            {
                                                "type": "method",
                                                "method": method,
                                                "signature": method_info["signature"],
                                                "declaring_class": method_info["declaring_class"],
                                                "return_type": method_info.get(
                                                    "return_type"
                                                ),  # Include generic type info
                                                "args": [],
                                            }
                                        ]
                                    else:
                                        method_name = method  # Fallback if signature not found
            except Exception as e:
                import dis
                import sys

                print(f"[DEBUG] Lambda source parsing failed: {e}", file=sys.stderr)
                print("[DEBUG] Attempting bytecode analysis fallback...", file=sys.stderr)

                # Fallback: Analyze bytecode to extract method calls
                try:
                    import io

                    bytecode_output = io.StringIO()
                    dis.dis(transform_func, file=bytecode_output)
                    bytecode = bytecode_output.getvalue()

                    # Extract LOAD_METHOD and CALL_METHOD instructions
                    # Pattern: LOAD_METHOD followed by CALL_METHOD indicates a method call
                    method_calls = []
                    lines = bytecode.split("\n")
                    for i, line in enumerate(lines):
                        if "LOAD_METHOD" in line or "LOAD_ATTR" in line:
                            # Extract method name from the instruction
                            parts = line.split()
                            if len(parts) >= 4:
                                method_name = parts[-1].strip("()")
                                if method_name and not method_name.startswith("_"):
                                    method_calls.append(method_name)

                    print(
                        f"[DEBUG] Bytecode analysis found methods: {method_calls}", file=sys.stderr
                    )

                    if method_calls:
                        # Build transform_ops from detected method calls (chained)
                        transform_ops = []
                        for method in method_calls:
                            method_info = self.api.getMethodInfo(
                                method, [], target_class=element_type
                            )
                            if method_info:
                                transform_ops.append(
                                    {
                                        "type": "method",
                                        "method": method,
                                        "signature": method_info["signature"],
                                        "declaring_class": method_info["declaring_class"],
                                        "args": [],
                                    }
                                )

                        if transform_ops:
                            print(
                                "[DEBUG] Successfully built transform_ops from bytecode!",
                                file=sys.stderr,
                            )
                        else:
                            print(
                                f"[DEBUG] Could not resolve signatures for methods: {method_calls}",
                                file=sys.stderr,
                            )
                except Exception as bytecode_err:
                    print(f"[DEBUG] Bytecode analysis also failed: {bytecode_err}", file=sys.stderr)

        # Create forEach operation
        operation = {
            "ref": new_ref_id,
            "type": "forEach",
            "array_ref": array_ref_id,
            "skip_nulls": skip_nulls,
        }

        # Add method, method_list, or transform_ops if extracted
        if transform_ops:
            # CRITICAL: Validate that all transform operations have declaring_class
            if isinstance(transform_ops, list):
                for i, op in enumerate(transform_ops):
                    if isinstance(op, dict) and op.get("type") == "method":
                        if "declaring_class" not in op or op["declaring_class"] is None:
                            import sys

                            print(
                                f"❌ CRITICAL ERROR: Transform operation #{i} missing declaring_class",
                                file=sys.stderr,
                            )
                            print(f"   Method: {op.get('method')}", file=sys.stderr)
                            print("   This will cause the JNI bridge to crash.", file=sys.stderr)
                            raise RuntimeError(
                                f"forEach transform operation for method '{op.get('method')}' is missing declaring_class. "
                                f"This indicates a bug in the query builder."
                            )
                    elif isinstance(op, list):
                        # Handle chains: [[op1, op2], [op3, op4]]
                        for j, chain_op in enumerate(op):
                            if isinstance(chain_op, dict) and chain_op.get("type") == "method":
                                if (
                                    "declaring_class" not in chain_op
                                    or chain_op["declaring_class"] is None
                                ):
                                    import sys

                                    print(
                                        f"❌ CRITICAL ERROR: Chain operation #{i}.{j} missing declaring_class",
                                        file=sys.stderr,
                                    )
                                    print(f"   Method: {chain_op.get('method')}", file=sys.stderr)
                                    raise RuntimeError(
                                        f"forEach chain operation for method '{chain_op.get('method')}' is missing declaring_class."
                                    )
            operation["transform"] = transform_ops
        elif method_name:
            operation["method"] = method_name
        elif method_list:
            operation["methods"] = method_list
        elif transform_func:
            # Lambda parsing failed but we have a function - warn user
            import sys

            print(
                "⚠️  WARNING: forEach lambda parsing failed. Unable to extract method calls from lambda.",
                file=sys.stderr,
            )
            print(
                "   Lambda will be ignored and raw array elements will be returned.",
                file=sys.stderr,
            )
            print(
                "   This usually happens when using lambdas in REPL or with -c flag.",
                file=sys.stderr,
            )
            print("   Try defining the lambda in a .py file instead.", file=sys.stderr)

        self.operations.append(operation)

        # Track dependency on the array
        if new_ref_id not in self.dependency_graph:
            self.dependency_graph[new_ref_id] = set()
        self.dependency_graph[new_ref_id].add(array_ref_id)

        # Determine the return type of the forEach result
        result_return_type = "array"  # Default fallback

        # If we have transform operations, extract return type from the last operation
        if transform_ops:
            # Handle dict format: {"_dict": [...]}
            if isinstance(transform_ops, dict) and "_dict" in transform_ops:
                # Dict results always return "array" (array of dicts)
                result_return_type = "array"
            # Handle list format: [{...}, {...}]
            elif isinstance(transform_ops, list) and len(transform_ops) > 0:
                last_op = transform_ops[-1]
                if "signature" in last_op:
                    # Extract return type from signature: "(args)ReturnType"
                    sig = last_op["signature"]
                    # Find the closing paren of args, everything after is the return type
                    paren_idx = sig.find(")")
                    if paren_idx != -1:
                        result_return_type = sig[paren_idx + 1 :]

                        # Handle generic collections: List<TileItem>, Collection<NPC>, etc.
                        # Check if we have the generic type info in return_type field
                        if "return_type" in last_op and last_op["return_type"]:
                            generic_type = last_op["return_type"]
                            # Extract the generic parameter: "List<TileItem>" -> "TileItem"
                            import re

                            match = re.search(r"<([^>]+)>", generic_type)
                            if match:
                                simple_name = match.group(1)
                                # Convert simple name to full path
                                if hasattr(self, "api") and "class_packages" in self.api.api_data:
                                    package_path = self.api.api_data["class_packages"].get(
                                        simple_name
                                    )
                                    if package_path:
                                        # Use the element type from the generic parameter
                                        result_return_type = f"[L{package_path}/{simple_name};"
                                    else:
                                        # Fallback to base API package
                                        result_return_type = f"[Lnet/runelite/api/{simple_name};"
                                else:
                                    result_return_type = f"[Lnet/runelite/api/{simple_name};"

        # Create and return QueryRef with proper return type
        new_ref = QueryRef(self, new_ref_id, None, result_return_type)
        self.refs[new_ref_id] = new_ref
        return new_ref

    def construct(self, class_name: str, *args) -> QueryRef:
        """
        Create a new instance of a Java class using its constructor.

        Args:
            class_name: Full Java class name (e.g., "net.runelite.api.coords.LocalPoint")
                       or short name (e.g., "LocalPoint") - will be resolved
            *args: Constructor arguments (can be static values or QueryRefs)

        Returns:
            QueryRef to the newly constructed object

        Example:
            q = api.query()
            lp = q.construct("LocalPoint", 100, 200)
            # or
            lp = q.LocalPoint(100, 200)  # via proxy
        """
        # Resolve short class names to full names
        full_class_name = self._resolveClassName(class_name)

        # Find matching constructor signature
        signature = self.api.get_constructor_signature(full_class_name, args)
        if not signature:
            # Try to infer signature from args
            signature = self._inferConstructorSignature(full_class_name, args)

        # Generate new ref ID
        new_ref_id = f"r{self.ref_counter}"
        self.ref_counter += 1

        # Convert arguments
        converted_args = []
        for arg in args:
            # Check if it's a QueryRef or proxy (has ref_id attribute)
            if isinstance(arg, QueryRef) or (hasattr(arg, "ref_id") and hasattr(arg, "query")):
                ref_id = arg.ref_id if isinstance(arg, QueryRef) else arg.ref_id
                converted_args.append({"_ref": ref_id})
                # Track dependency
                if new_ref_id not in self.dependency_graph:
                    self.dependency_graph[new_ref_id] = set()
                self.dependency_graph[new_ref_id].add(ref_id)
            else:
                converted_args.append(arg)

        # Create operation
        operation = {
            "ref": new_ref_id,
            "type": "construct",
            "class": full_class_name.replace(".", "/"),  # JNI format
            "signature": signature,
            "args": converted_args,
        }

        self.operations.append(operation)

        # Create and return QueryRef
        new_ref = QueryRef(self, new_ref_id, None, full_class_name)
        self.refs[new_ref_id] = new_ref
        return new_ref

    def callStatic(self, class_name: str, method_name: str, *args) -> QueryRef:
        """
        Call a static method on a Java class.

        Args:
            class_name: Full Java class name or short name
            method_name: Static method name
            *args: Method arguments (can be static values or QueryRefs)

        Returns:
            QueryRef to the result

        Example:
            q = api.query()
            scene = q.client.getScene()
            lp = q.callStatic("LocalPoint", "fromWorld", scene, 3223, 3217)
            # or
            lp = q.LocalPoint.fromWorld(scene, 3223, 3217)  # via proxy
        """
        # Resolve short class names to full names
        full_class_name = self._resolveClassName(class_name)

        # Get method signature
        signature = self.api.getStaticMethodSignature(full_class_name, method_name, args)
        if not signature:
            # Try to infer from regular methods (static methods share same signature format)
            signature = self.api.getMethodSignature(method_name, args)

        if not signature:
            # Last resort: infer signature from argument types
            signature = self._inferMethodSignature(method_name, args)

        # Generate new ref ID
        new_ref_id = f"r{self.ref_counter}"
        self.ref_counter += 1

        # Convert arguments
        converted_args = []
        for arg in args:
            # Check if it's a QueryRef or proxy (has ref_id attribute)
            if isinstance(arg, QueryRef) or (hasattr(arg, "ref_id") and hasattr(arg, "query")):
                ref_id = arg.ref_id if isinstance(arg, QueryRef) else arg.ref_id
                converted_args.append({"_ref": ref_id})
                # Track dependency
                if new_ref_id not in self.dependency_graph:
                    self.dependency_graph[new_ref_id] = set()
                self.dependency_graph[new_ref_id].add(ref_id)
            else:
                converted_args.append(arg)

        # Create operation
        operation = {
            "ref": new_ref_id,
            "type": "static",
            "class": full_class_name.replace(".", "/"),  # JNI format
            "method": method_name,
            "signature": signature,
            "args": converted_args,
        }

        self.operations.append(operation)

        # Extract return type from signature
        return_type = None
        if signature:
            # Signature format: (args)ReturnType
            paren_end = signature.rfind(")")
            if paren_end >= 0:
                ret_sig = signature[paren_end + 1 :]
                if ret_sig.startswith("L") and ret_sig.endswith(";"):
                    # Object return type - convert from JNI to dotted format
                    return_type = ret_sig[1:-1].replace("/", ".")

        # Create and return QueryRef with return type
        new_ref = QueryRef(self, new_ref_id, None, return_type)
        self.refs[new_ref_id] = new_ref
        return new_ref

    def _resolveClassName(self, class_name: str) -> str:
        """Resolve short class names to full Java class names."""
        # Common coordinate classes
        short_names = {
            "LocalPoint": "net.runelite.api.coords.LocalPoint",
            "WorldPoint": "net.runelite.api.coords.WorldPoint",
            "WorldArea": "net.runelite.api.coords.WorldArea",
            "Area": "net.runelite.api.Area",
        }

        if class_name in short_names:
            return short_names[class_name]

        # If it contains dots, assume it's already a full name
        if "." in class_name:
            return class_name

        # Otherwise, assume it's in net.runelite.api package
        return f"net.runelite.api.{class_name}"

    def _inferConstructorSignature(self, class_name: str, args: tuple) -> str:
        """Infer constructor signature from arguments."""
        # Build signature from argument types
        arg_sigs = []
        for arg in args:
            if isinstance(arg, int):
                arg_sigs.append("I")
            elif isinstance(arg, bool):
                arg_sigs.append("Z")
            elif isinstance(arg, float):
                arg_sigs.append("D")
            elif isinstance(arg, str):
                arg_sigs.append("Ljava/lang/String;")
            elif isinstance(arg, QueryRef):
                # Try to use the QueryRef's return type
                if arg.return_type:
                    arg_sigs.append(f"L{arg.return_type.replace('.', '/')};")
                else:
                    arg_sigs.append("Ljava/lang/Object;")
            else:
                arg_sigs.append("Ljava/lang/Object;")

        return f"({''.join(arg_sigs)})V"

    def _inferMethodSignature(self, method_name: str, args: tuple) -> str:
        """Infer method signature from method name and arguments."""
        # Build argument signature
        arg_sigs = []
        for arg in args:
            if isinstance(arg, int):
                arg_sigs.append("I")
            elif isinstance(arg, bool):
                arg_sigs.append("Z")
            elif isinstance(arg, float):
                arg_sigs.append("D")
            elif isinstance(arg, str):
                arg_sigs.append("Ljava/lang/String;")
            elif isinstance(arg, QueryRef) or (
                hasattr(arg, "ref_id") and hasattr(arg, "return_type")
            ):
                # QueryRef or proxy object - use its return type
                return_type = arg.return_type if hasattr(arg, "return_type") else None
                if return_type:
                    arg_sigs.append(f"L{return_type.replace('.', '/')};")
                else:
                    arg_sigs.append("Ljava/lang/Object;")
            else:
                arg_sigs.append("Ljava/lang/Object;")

        # Return object by default (most methods return objects, not primitives)
        return f"({''.join(arg_sigs)})Ljava/lang/Object;"

    def __repr__(self) -> str:
        return f"Query(operations={len(self.operations)}, selections={len(self.selections)})"


# Lazy-load proxy metadata (called when needed)
PROXY_CLASSES = None
GeneratedClientProxy = None
_USE_GENERATED_PROXIES = False


def _ensureProxyMetadata():
    """Ensure proxy metadata is loaded."""
    global PROXY_CLASSES, GeneratedClientProxy, _USE_GENERATED_PROXIES

    if _USE_GENERATED_PROXIES:
        return

    proxies = _loadProxies()
    if proxies:
        PROXY_CLASSES = getattr(proxies, "PROXY_CLASSES", None)
        GeneratedClientProxy = getattr(proxies, "ClientProxy", None)
        _USE_GENERATED_PROXIES = True
