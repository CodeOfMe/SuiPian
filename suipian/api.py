from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = ["ToolResult", "hide_file", "reveal_file", "validate_morph", "get_info"]


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }


def hide_file(
    *,
    source: str | Path,
    carrier: str | Path,
    output: str | Path,
    password: str,
) -> ToolResult:
    from . import __version__
    from .core import MorphEngine

    try:
        if not password:
            return ToolResult(success=False, error="Password cannot be empty")

        source_p = Path(source)
        carrier_p = Path(carrier)
        output_p = Path(output)

        if not source_p.exists():
            return ToolResult(success=False, error=f"Source file not found: {source}")

        engine = MorphEngine()
        engine.hide_file(source_p, carrier_p, output_p, password)

        return ToolResult(
            success=True,
            data={"output": str(output_p)},
            metadata={"version": __version__, "original": source_p.name},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def reveal_file(
    *,
    morphed: str | Path,
    output: str | Path,
    password: str,
) -> ToolResult:
    from pathlib import Path

    from cryptography.exceptions import InvalidTag

    from . import __version__
    from .core import MorphEngine

    try:
        if not password:
            return ToolResult(success=False, error="Password cannot be empty")

        morphed_p = Path(morphed)
        output_p = Path(output)

        if not morphed_p.exists():
            return ToolResult(success=False, error=f"Morphed file not found: {morphed}")

        engine = MorphEngine()
        engine.reveal_file(morphed_p, output_p, password)

        return ToolResult(
            success=True,
            data={"output": str(output_p)},
            metadata={"version": __version__},
        )
    except InvalidTag:
        return ToolResult(
            success=False, error="Decryption failed - wrong password or corrupted file"
        )
    except ValueError as e:
        return ToolResult(success=False, error=str(e))
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def validate_morph(*, file: str | Path) -> ToolResult:
    from pathlib import Path

    from . import __version__
    from .core import MorphEngine

    try:
        file_p = Path(file)
        if not file_p.exists():
            return ToolResult(success=False, error=f"File not found: {file}")

        engine = MorphEngine()
        valid, info, error = engine.validate(file_p)

        if valid and info is not None:
            return ToolResult(
                success=True,
                data={
                    "valid": True,
                    "info": {
                        "version": info.version,
                        "original_name": info.original_name,
                        "original_type": info.original_type,
                        "checksum": info.checksum,
                        "payload_size": info.payload_size,
                    },
                },
                metadata={"version": __version__},
            )
        else:
            return ToolResult(success=False, error=error)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def get_info(*, file: str | Path) -> ToolResult:
    from pathlib import Path

    from . import __version__
    from .core import MorphEngine

    try:
        file_p = Path(file)
        if not file_p.exists():
            return ToolResult(success=False, error=f"File not found: {file}")

        engine = MorphEngine()
        info = engine.get_info(file_p)

        if info:
            return ToolResult(
                success=True,
                data={
                    "version": info.version,
                    "original_name": info.original_name,
                    "original_type": info.original_type,
                    "checksum": info.checksum,
                    "payload_size": info.payload_size,
                },
                metadata={"version": __version__},
            )
        else:
            return ToolResult(success=False, error="Could not parse file info")
    except Exception as e:
        return ToolResult(success=False, error=str(e))
