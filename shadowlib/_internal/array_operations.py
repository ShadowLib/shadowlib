"""
Direct array operations for MessagePack protocol
Efficient forEach, filter, and map without JSON conversion
"""

from typing import Any, Dict, List, Optional

import msgpack


class ArrayOperation:
    """Build array operations for MessagePack protocol"""

    @staticmethod
    def forEach(
        target_ref: str, method: str, collect: bool = True, signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a forEach operation.

        Args:
            target_ref: Reference to cached array object
            method: Method name to call on each element (e.g., "getId", "getQuantity")
            collect: Whether to collect and return results
            signature: Optional JNI signature if method is ambiguous

        Special methods:
            - "getItemInfo": Returns {id, quantity} for each item
            - "getId": Returns just the item ID
            - Any method name: Calls that method on each element

        Example:
            # Get all item IDs from inventory
            op = ArrayOperation.forEach("inv_items_ref", "getId")
        """
        operation = {
            "type": "forEach",
            "target": target_ref,
            "operation": {"method": method, "collect": collect},
        }

        if signature:
            operation["operation"]["signature"] = signature

        return operation

    @staticmethod
    def filter(
        target_ref: str,
        method: str = "getId",
        value: Optional[int] = None,
        not_equal: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a filter operation.

        Args:
            target_ref: Reference to cached array object
            method: Method to call for filtering (default: "getId")
            value: Keep elements where method returns this value
            not_equal: Keep elements where method does NOT return this value

        If neither value nor not_equal specified, filters out -1 (empty slots).

        Example:
            # Filter out empty inventory slots (id != -1)
            op = ArrayOperation.filter("inv_items_ref", not_equal=-1)

            # Get only runes (assuming rune IDs are in certain range)
            op = ArrayOperation.filter("inv_items_ref", "getId", value=554)  # Fire rune
        """
        condition = {"method": method}

        if value is not None:
            condition["value"] = value
        elif not_equal is not None:
            condition["not_equal"] = not_equal

        return {"type": "filter", "target": target_ref, "condition": condition}

    @staticmethod
    def mapTransform(
        target_ref: str, method: str, signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a map operation to transform array elements.

        Args:
            target_ref: Reference to cached array object
            method: Method to call for transformation
            signature: Optional JNI signature

        Example:
            # Transform items to their IDs
            op = ArrayOperation.mapTransform("inv_items_ref", "getId")
        """
        return {
            "type": "map",
            "target": target_ref,
            "operation": {
                "method": method,
                "collect": True,  # Map always collects
            },
        }

    @staticmethod
    def chain(operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Chain multiple operations together.

        Example:
            ops = ArrayOperation.chain([
                ArrayOperation.filter("items", not_equal=-1),  # Filter empty
                ArrayOperation.mapTransform("$result", "getId")  # Get IDs
            ])
        """
        return {"type": "chain", "operations": operations}


class InventoryHelper:
    """Helper for common inventory operations"""

    @staticmethod
    def getNonEmptyItems(inventory_ref: str) -> Dict[str, Any]:
        """Get all non-empty inventory slots with full info"""
        return ArrayOperation.filter(inventory_ref, "getId", not_equal=-1)

    @staticmethod
    def getItemIds(inventory_ref: str) -> Dict[str, Any]:
        """Get list of all item IDs (including -1 for empty)"""
        return ArrayOperation.forEach(inventory_ref, "getId")

    @staticmethod
    def getItemInfo(inventory_ref: str) -> Dict[str, Any]:
        """Get {id, quantity} for all items"""
        return ArrayOperation.forEach(inventory_ref, "getItemInfo")

    @staticmethod
    def countItem(inventory_ref: str, item_id: int) -> Dict[str, Any]:
        """Count how many of a specific item are in inventory"""
        return {
            "type": "reduce",
            "target": inventory_ref,
            "operation": {"method": "getId", "match": item_id, "reducer": "count"},
        }

    @staticmethod
    def sumQuantity(inventory_ref: str, item_id: int) -> Dict[str, Any]:
        """Sum total quantity of a specific item"""
        return {
            "type": "reduce",
            "target": inventory_ref,
            "operation": {
                "filter_method": "getId",
                "filter_value": item_id,
                "sum_method": "getQuantity",
            },
        }


def integrateWithQueryBuilder(query_builder):
    """
    Extend QueryBuilder with array operations.

    This would be called from query_builder.py to add these methods.
    """

    def _forEach(self, method: str, collect: bool = True):
        """Execute forEach on the current reference"""
        if not self._current_ref:
            raise ValueError("No array reference to operate on")

        operation = ArrayOperation.forEach(self._current_ref, method, collect)

        # Add to batch
        self._query._add_operation(operation)
        return self

    def _filter(self, method: str = "getId", **kwargs):
        """Filter array elements"""
        if not self._current_ref:
            raise ValueError("No array reference to operate on")

        operation = ArrayOperation.filter(self._current_ref, method, **kwargs)

        self._query._add_operation(operation)
        return self

    def _map(self, method: str):
        """Map array elements"""
        if not self._current_ref:
            raise ValueError("No array reference to operate on")

        operation = ArrayOperation.mapTransform(self._current_ref, method)

        self._query._add_operation(operation)
        return self

    # Add methods to the class
    query_builder.forEach = _for_each
    query_builder.filter = _filter
    query_builder.map = _map


# Example usage patterns
if __name__ == "__main__":
    # These would be sent as MessagePack operations

    # 1. Get all non-empty inventory items
    op1 = InventoryHelper.getNonEmptyItems("inventory_array_ref")
    print("Filter empty slots:", op1)

    # 2. Get item IDs and quantities
    op2 = InventoryHelper.getItemInfo("inventory_array_ref")
    print("Get item info:", op2)

    # 3. Custom forEach
    op3 = ArrayOperation.forEach("widget_array", "isHidden", collect=True)
    print("Check widget visibility:", op3)

    # 4. Chain operations
    op4 = ArrayOperation.chain(
        [
            ArrayOperation.filter("items", not_equal=-1),
            ArrayOperation.mapTransform("$result", "getId"),
        ]
    )
    print("Chained ops:", op4)

    # The packed version for sending:
    packed = msgpack.packb(op2)
    print(f"\nPacked size: {len(packed)} bytes")
