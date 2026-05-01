# SuiPian (碎片) - File Disguise & Restoration Tool

## Concept & Vision

SuiPian (碎片, meaning "fragments") is a cryptographic file transformation tool that disguises one file as another seemingly normal file. An image can be transformed into a text file that looks perfectly ordinary, yet contains the hidden image. The tool feels like digital camouflage - files hide in plain sight, transform on command, and restore perfectly. Think of it as digital shapeshifting.

## Technical Design

### Core Algorithm

**Transformation Pipeline:**
1. **Compression**: LZ4 compression of source file for efficiency
2. **Encryption**: AES-256-GCM encryption with a derived key
3. **Encoding**: Base64 encoding to make output appear as text
4. **Wrapping**: Inject the encoded data into a "carrier" text file with normal content

**Key Derivation**: PBKDF2 with SHA-256, 100,000 iterations, 32-byte key

**Reversibility**: All transformations are mathematically reversible with the correct password.

### File Format

The disguised file format:
```
-----BEGIN SUIPIAN HEADER-----
Version: 1.0
Original: <filename>.<ext>
Type: <original_mime_type>
-----END SUIPIAN HEADER-----

[Base64 encoded encrypted payload]

-----BEGIN SUIPIAN FOOTER-----
Checksum: <SHA256 of original>
-----END SUIPIAN FOOTER-----
```

### CLI Commands

1. `suipian hide <source> <carrier> -o <output> -p <password>` - Hide source file inside carrier text
2. `suipian reveal <disguised> -o <output> -p <password>` - Restore disguised file to original
3. `suipian validate <file>` - Check if a file is a valid morphed file
4. `suipian info <file>` - Show information about a morphed file

### Python API

```python
from suipian import hide_file, reveal_file, validate_morph

result = hide_file(source="image.png", carrier="readme.txt", output="output.txt", password="secret")
result = reveal_file(morphed="output.txt", output="restored.png", password="secret")
result = validate_morph(file="output.txt")
```

## Project Structure

```
SuiPian/
├── suipian/
│   ├── __init__.py      # Version + exports
│   ├── core.py          # Steganography engine
│   ├── cli.py           # CLI interface
│   ├── api.py           # Python API
│   ├── tools.py         # OpenAI function tools
│   └── __main__.py      # python -m entry
├── tests/
│   └── test_unified_api.py
├── upload_pypi.sh
├── upload_pypi.bat
├── pyproject.toml
├── README.md
└── README_CN.md
```

## CLI Flags

- `-V, --version`: Show version
- `-v, --verbose`: Verbose output
- `-o, --output <path>`: Output file path
- `-p, --password <pwd>`: Password for encryption
- `-q, --quiet`: Quiet mode
- `--json`: JSON output (on subcommands)

## Acceptance Criteria

1. Successfully hide an image inside a text file
2. The resulting text file is readable and appears normal
3. The hidden image can be perfectly restored
4. Wrong password correctly fails
5. Invalid morphed files are detected
6. All CLI flags work correctly
7. Python API returns proper ToolResult objects
8. All tests pass
9. Version defined in single location (__init__.py)
10. upload_pypi.sh and upload_pypi.bat work correctly