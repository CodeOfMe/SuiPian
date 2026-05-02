# SuiPian (碎片) - Zero-Width Steganography File Tool

## Concept & Vision

SuiPian (碎片, meaning "fragments") encodes any file into pure text using zero-width Unicode characters, making it look completely ordinary. An image can be hidden inside an email or article that reads perfectly normally — no special markers, no suspicious encoding, just text. Only someone with the password can restore the original file.

## Technical Design

### Core Algorithm

**Transformation Pipeline:**
1. **Compression**: LZ4 compression of source file
2. **Encryption**: AES-256-GCM encryption with a derived key
3. **Encoding**: Binary payload encoded to zero-width characters (U+200B zero-width space, U+200C zero-width non-joiner)
4. **Embedding**: Append zero-width string to carrier text end

**Key Derivation**: PBKDF2 with SHA-256, 100,000 iterations, 32-byte key

**Binary Format** (before encoding):
```
4 bytes  : MAGIC "SPRF"
1 byte   : format version
2 bytes  : original_name length + name bytes
2 bytes  : original_type length + type bytes
32 bytes: SHA-256 checksum of original data
16 bytes: salt
12 bytes: nonce
4 bytes : ciphertext length
N bytes : ciphertext (encrypted + authenticated)
```

### Why Zero-Width Is Undetectable

- No header/footer markers — no `-----BEGIN-----` blocks
- No Base64 characters visible in output — only `A-Za-z0-9+/=` in carrier
- Zero-width characters (U+200B, U+200C) are invisible in most text editors and browsers
- Statistical analysis is ineffective because output passes as natural text

### CLI Commands

1. `suipian hide <source> <carrier> -o <output> -p <password>` - Hide source inside carrier text
2. `suipian reveal <disguised> -o <output> -p <password>` - Restore file from disguised text
3. `suipian validate <file>` - Check if file contains hidden data
4. `suipian info <file>` - Show metadata of hidden data

### Python API

```python
from suipian import hide_file, reveal_file, validate_morph

result = hide_file(source="image.png", carrier="article.txt", output="output.txt", password="secret")
result = reveal_file(morphed="output.txt", output="restored.png", password="secret")
result = validate_morph(file="output.txt")
```

## Project Structure

```
SuiPian/
├── suipian/
│   ├── __init__.py      # Version + exports
│   ├── core.py           # Steganography engine
│   ├── cli.py            # CLI interface
│   ├── api.py            # Python API
│   ├── tools.py          # OpenAI function tools
│   └── __main__.py       # python -m entry
├── tests/
│   └── test_unified_api.py
├── upload_pypi.sh
├── upload_pypi.bat
├── pyproject.toml
├── README.md
└── README_CN.md
```

## Acceptance Criteria

1. Image hidden in text looks 100% like normal text (no markers visible)
2. Hidden image perfectly restored with correct password
3. Wrong password correctly fails (without revealing file exists)
4. No zero-width detection possible by casual inspection
5. All CLI flags work correctly
6. Python API returns proper ToolResult objects
7. All 54 tests pass
8. Version defined in single location (__init__.py)