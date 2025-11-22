"""
Pure MessagePack protocol for RuneLite bridge communication
Replaces the hybrid JSON/MessagePack approach with pure binary protocol
"""

import struct
from typing import Any, Dict, List, Tuple

import msgpack


class ProtocolEncoder:
    """Smart encoder that pre-processes all type information"""

    @staticmethod
    def parseSignature(sig: str) -> Dict:
        """Convert JNI signature to simple type info"""
        if not sig or sig[0] != "(":
            return {"arg_types": [], "return_type": "void"}

        params = []
        i = 1  # Skip '('

        while i < len(sig) and sig[i] != ")":
            if sig[i] == "I":
                params.append("int")
                i += 1
            elif sig[i] == "J":
                params.append("long")
                i += 1
            elif sig[i] == "Z":
                params.append("boolean")
                i += 1
            elif sig[i] == "F":
                params.append("float")
                i += 1
            elif sig[i] == "D":
                params.append("double")
                i += 1
            elif sig[i] == "B":
                params.append("byte")
                i += 1
            elif sig[i] == "C":
                params.append("char")
                i += 1
            elif sig[i] == "S":
                params.append("short")
                i += 1
            elif sig[i] == "L":
                # Object type - extract class name
                end = sig.index(";", i)
                class_name = sig[i + 1 : end].replace("/", ".")
                params.append({"type": "object", "class": class_name})
                i = end + 1
            elif sig[i] == "[":
                # Array type
                array_depth = 0
                while i < len(sig) and sig[i] == "[":
                    array_depth += 1
                    i += 1
                # Get element type
                if sig[i] == "L":
                    end = sig.index(";", i)
                    element_type = sig[i + 1 : end].replace("/", ".")
                    params.append({"type": "array", "depth": array_depth, "element": element_type})
                    i = end + 1
                elif sig[i] == "I":
                    params.append({"type": "array", "depth": array_depth, "element": "int"})
                    i += 1
                elif sig[i] == "J":
                    params.append({"type": "array", "depth": array_depth, "element": "long"})
                    i += 1
                elif sig[i] == "Z":
                    params.append({"type": "array", "depth": array_depth, "element": "boolean"})
                    i += 1
                else:
                    params.append({"type": "array", "depth": array_depth, "element": "unknown"})
                    i += 1
            else:
                params.append("unknown")
                i += 1

        # Parse return type
        i += 1  # Skip ')'
        if i >= len(sig):
            return_type = "void"
        else:
            ret = sig[i:]
            if ret[0] == "V":
                return_type = "void"
            elif ret[0] == "I":
                return_type = "int"
            elif ret[0] == "J":
                return_type = "long"
            elif ret[0] == "Z":
                return_type = "boolean"
            elif ret[0] == "F":
                return_type = "float"
            elif ret[0] == "D":
                return_type = "double"
            elif ret[0] == "B":
                return_type = "byte"
            elif ret[0] == "C":
                return_type = "char"
            elif ret[0] == "S":
                return_type = "short"
            elif ret[0] == "L":
                end = ret.index(";") if ";" in ret else len(ret)
                class_name = ret[1:end].replace("/", ".")
                return_type = {"type": "object", "class": class_name}
            elif ret[0] == "[":
                # Parse array return type
                depth = 0
                j = 0
                while j < len(ret) and ret[j] == "[":
                    depth += 1
                    j += 1
                if ret[j] == "I":
                    return_type = {"type": "array", "depth": depth, "element": "int"}
                elif ret[j] == "L":
                    end = ret.index(";", j) if ";" in ret[j:] else len(ret)
                    element = ret[j + 1 : end].replace("/", ".")
                    return_type = {"type": "array", "depth": depth, "element": element}
                else:
                    return_type = {"type": "array", "depth": depth, "element": "unknown"}
            else:
                return_type = "unknown"

        return {"arg_types": params, "return_type": return_type}

    @staticmethod
    def encodeValue(value: Any, type_hint: str = None) -> Tuple[str, Any]:
        """Encode a value with type information"""
        # Handle None/null
        if value is None:
            return ("null", None)

        # Handle booleans
        if isinstance(value, bool):
            return ("boolean", value)

        # Handle integers
        if isinstance(value, int):
            # Determine int size based on value or hint
            if type_hint == "long" or value > 2147483647 or value < -2147483648:
                return ("long", value)
            elif type_hint == "byte" and -128 <= value <= 127:
                return ("byte", value)
            elif type_hint == "short" and -32768 <= value <= 32767:
                return ("short", value)
            else:
                return ("int", value)

        # Handle floats
        if isinstance(value, float):
            if type_hint == "double":
                return ("double", value)
            else:
                return ("float", value)

        # Handle strings
        if isinstance(value, str):
            # Check if it's an object reference
            if value.startswith("ref_") or value.startswith("result_"):
                return ("ref", value)
            else:
                return ("string", value)

        # Handle lists/arrays
        if isinstance(value, list):
            return ("array", value)

        # Handle object references (if using a custom class)
        if hasattr(value, "ref_id"):
            return ("ref", value.ref_id)

        # Handle enum values
        if hasattr(value, "__class__") and hasattr(value.__class__, "__name__"):
            class_name = value.__class__.__name__
            if hasattr(value, "ordinal"):
                return ("enum", {"class": class_name, "ordinal": value.ordinal})

        # Default to object
        return ("object", str(value))

    @staticmethod
    def encodeRequest(operations: List[Dict]) -> bytes:
        """Encode operations with pre-parsed type information"""
        processed = []

        for op in operations:
            new_op = {}

            # Operation ID (for referencing results)
            if "ref" in op:
                new_op["id"] = op["ref"]

            # Method call
            new_op["method"] = op["method"]

            # Set target or class
            if "target" in op:
                # Convert ObjectReference to string if needed
                if hasattr(op["target"], "ref_id"):
                    new_op["target"] = op["target"].ref_id
                else:
                    new_op["target"] = op["target"]
            elif "class" in op:
                new_op["class"] = op["class"]

            # Parse signature and add type info
            if "signature" in op:
                type_info = ProtocolEncoder.parseSignature(op["signature"])
                new_op["arg_types"] = type_info["arg_types"]
                new_op["return_type"] = type_info["return_type"]
                new_op["signature"] = op["signature"]  # Keep for method lookup

            # Process arguments with type encoding
            if "args" in op:
                encoded_args = []
                arg_types = new_op.get("arg_types", [])

                for i, arg in enumerate(op["args"]):
                    # Get type hint from signature if available
                    type_hint = arg_types[i] if i < len(arg_types) else None
                    if isinstance(type_hint, dict):
                        type_hint = type_hint.get("type")

                    arg_type, arg_value = ProtocolEncoder.encodeValue(arg, type_hint)
                    encoded_args.append({"type": arg_type, "value": arg_value})

                new_op["args"] = encoded_args

            processed.append(new_op)

        # Pack with MessagePack
        request = {
            "version": 2,  # Version 2 indicates pure MessagePack protocol
            "operations": processed,
        }

        return msgpack.packb(request, use_bin_type=True)


class ProtocolDecoder:
    """Decoder for MessagePack responses"""

    @staticmethod
    def decodeResponse(data: bytes) -> Dict:
        """Decode a MessagePack response"""
        # Check for MessagePack magic header if present
        if len(data) >= 8:
            magic = struct.unpack("<I", data[:4])[0]  # Little-endian
            if magic == 0xDEADBEEF:  # MessagePack magic
                size = struct.unpack("<I", data[4:8])[0]  # Little-endian
                data = data[8 : 8 + size]

        # Unpack MessagePack data
        try:
            response = msgpack.unpackb(data, raw=False, strict_map_key=False)
            return ProtocolDecoder.processResponse(response)
        except Exception as e:
            return {"error": f"Failed to decode response: {str(e)}"}

    @staticmethod
    def processResponse(response: Any) -> Any:
        """Process decoded response, handling special types"""
        if isinstance(response, dict):
            # Check for error
            if "error" in response:
                return response

            # Check for success/results format
            if "success" in response and "results" in response:
                return response

            # Check for reference
            if "_ref" in response:
                # Return as object reference
                return {"type": "ref", "value": response["_ref"]}

            # Recursively process dict values
            return {k: ProtocolDecoder.processResponse(v) for k, v in response.items()}

        elif isinstance(response, list):
            # Process each element
            return [ProtocolDecoder.processResponse(item) for item in response]

        else:
            # Return primitive values as-is
            return response


# Export functions
def encodeRequest(operations: List[Dict]) -> bytes:
    """Encode operations to MessagePack format"""
    return ProtocolEncoder.encodeRequest(operations)


def decodeResponse(data: bytes) -> Dict:
    """Decode MessagePack response"""
    return ProtocolDecoder.decodeResponse(data)


# Test the encoder
if __name__ == "__main__":
    # Test operation encoding
    test_ops = [
        {
            "ref": "r1",
            "target": "client",
            "method": "getLocalPlayer",
            "signature": "()Lnet/runelite/api/Player;",
            "args": [],
        },
        {
            "ref": "r2",
            "target": "r1",
            "method": "getName",
            "signature": "()Ljava/lang/String;",
            "args": [],
        },
        {
            "ref": "r3",
            "target": "client",
            "method": "getSkillExperience",
            "signature": "(Lnet/runelite/api/Skill;)I",
            "args": [{"class": "Skill", "ordinal": 0}],  # ATTACK enum
        },
    ]

    encoded = encodeRequest(test_ops)
    print(f"Encoded {len(test_ops)} operations into {len(encoded)} bytes")

    # Show the unpacked structure for debugging
    unpacked = msgpack.unpackb(encoded, raw=False, strict_map_key=False)
    import json

    print("Encoded structure:")
    print(json.dumps(unpacked, indent=2))
