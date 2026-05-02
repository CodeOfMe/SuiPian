# SuiPian (碎片)

Encode any file as plain text using invisible zero-width characters — looks perfectly normal, only the key can restore it.

## How It Works

1. **Compress**: LZ4 compression of source file
2. **Encrypt**: AES-256-GCM with PBKDF2 key derivation (100k iterations)
3. **Encode**: Binary payload → zero-width characters (​‌U+200B / ​‌U+200C)
4. **Append**: Hidden data appended to carrier text end — output looks 100% normal

**Undetectable**: No special markers, no visible Base64, zero-width chars are invisible in most editors.

## Features

- **Hide**: Encode any file (image, document, etc.) into a seemingly normal text file
- **Reveal**: Restore the original file from the disguised text using the password
- **Validate**: Check if a text file contains hidden data
- **Info**: Get metadata about hidden data

## Requirements

- Python 3.10+
- lz4
- cryptography

## Installation

```bash
pip install suipian
```

Or install from source:

```bash
pip install -e .
```

## Quick Start

### CLI

Hide a file (image → text):
```bash
suipian hide photo.png article.txt -o output.txt -p mypassword
```

Reveal a file (text → image):
```bash
suipian reveal output.txt -o restored.png -p mypassword
```

Validate hidden data:
```bash
suipian validate output.txt
```

Get hidden file info:
```bash
suipian info output.txt
```

### Python API

```python
from suipian import hide_file, reveal_file, validate_morph

result = hide_file(
    source="photo.png",
    carrier="article.txt",
    output="output.txt",
    password="secret"
)

result = reveal_file(
    morphed="output.txt",
    output="restored.png",
    password="secret"
)

result = validate_morph(file="output.txt")
print(result.success)
print(result.data)
```

## Agent Integration

```python
from suipian.tools import TOOLS, dispatch
```

## Development

```bash
pip install -e ".[dev]"
pytest tests/test_unified_api.py -v
```

## License

GPL-3.0