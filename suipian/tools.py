from __future__ import annotations

import json

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "suipian_hide_file",
            "description": (
                "Hide a file inside a carrier text file. The source file "
                "(image, document, etc.) is encrypted and embedded into a carrier "
                "text file, producing a seemingly normal text file that can be "
                "later restored to the original."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Path to the source file to hide (image, pdf, etc.)",
                    },
                    "carrier": {
                        "type": "string",
                        "description": "Path to the carrier text file (the file to embed into)",
                    },
                    "output": {
                        "type": "string",
                        "description": "Path to the output morphed file",
                    },
                    "password": {
                        "type": "string",
                        "description": "Password for encryption (required for restoration)",
                    },
                },
                "required": ["source", "carrier", "output", "password"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suipian_reveal_file",
            "description": "Restore a hidden file from a morphed file using the password.",
            "parameters": {
                "type": "object",
                "properties": {
                    "morphed": {
                        "type": "string",
                        "description": "Path to the morphed file to reveal",
                    },
                    "output": {
                        "type": "string",
                        "description": "Path to save the restored file",
                    },
                    "password": {
                        "type": "string",
                        "description": "Password used during hiding",
                    },
                },
                "required": ["morphed", "output", "password"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suipian_validate",
            "description": "Validate if a file is a valid morphed file and get its metadata.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "description": "Path to the file to validate",
                    },
                },
                "required": ["file"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suipian_get_info",
            "description": (
                "Get metadata about a morphed file: version, original name, type, checksum, size."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "description": "Path to the morphed file",
                    },
                },
                "required": ["file"],
            },
        },
    },
]


def dispatch(name: str, arguments: dict | str) -> dict:
    if isinstance(arguments, str):
        arguments = json.loads(arguments)

    assert isinstance(arguments, dict), "arguments must be a dict"

    if name == "suipian_hide_file":
        from .api import hide_file

        result = hide_file(**arguments)
        return result.to_dict()

    if name == "suipian_reveal_file":
        from .api import reveal_file

        result = reveal_file(**arguments)
        return result.to_dict()

    if name == "suipian_validate":
        from .api import validate_morph

        result = validate_morph(**arguments)
        return result.to_dict()

    if name == "suipian_get_info":
        from .api import get_info

        result = get_info(**arguments)
        return result.to_dict()

    raise ValueError(f"Unknown tool: {name}")
