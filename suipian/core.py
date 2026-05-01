from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
from dataclasses import dataclass
from pathlib import Path

import lz4.frame  # type: ignore[import-untyped]
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

HEADER_BEGIN = "-----BEGIN SUIPIAN HEADER-----"
HEADER_END = "-----END SUIPIAN HEADER-----"
FOOTER_BEGIN = "-----BEGIN SUIPIAN FOOTER-----"
FOOTER_END = "-----END SUIPIAN FOOTER-----"

MAGIC = b"SPRF"
FORMAT_VERSION = 1


@dataclass
class MorphedFileInfo:
    version: str
    original_name: str
    original_type: str
    checksum: str
    payload_size: int


@dataclass
class MorphEngine:
    salt_size: int = 16
    nonce_size: int = 12
    iterations: int = 100000

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.iterations,
        )
        return kdf.derive(password.encode())

    def _compress(self, data: bytes) -> bytes:
        return bytes(lz4.frame.compress(data))

    def _decompress(self, data: bytes) -> bytes:
        return bytes(lz4.frame.decompress(data))

    def _encrypt(self, data: bytes, password: str) -> tuple[bytes, bytes, bytes]:
        salt = os.urandom(self.salt_size)
        key = self._derive_key(password, salt)
        nonce = os.urandom(self.nonce_size)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return salt, nonce, ciphertext

    def _decrypt(self, salt: bytes, nonce: bytes, ciphertext: bytes, password: str) -> bytes:
        key = self._derive_key(password, salt)
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None)

    def hide_file(
        self, source_path: Path, carrier_path: Path, output_path: Path, password: str
    ) -> None:
        source_data = source_path.read_bytes()
        original_name = source_path.name
        original_type = self._get_mime_type(source_data)

        compressed = self._compress(source_data)
        salt, nonce, encrypted = self._encrypt(compressed, password)

        payload = MAGIC
        payload += struct.pack("!BII", FORMAT_VERSION, self.salt_size, self.nonce_size)
        payload += salt + nonce
        payload += struct.pack("!I", len(encrypted))
        payload += encrypted

        encoded = base64.b64encode(payload).decode("ascii")

        checksum = hashlib.sha256(source_data).hexdigest()

        carrier_content = carrier_path.read_text(encoding="utf-8") if carrier_path.exists() else ""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(carrier_content)
            if carrier_content and not carrier_content.endswith("\n"):
                f.write("\n\n")
            f.write(f"{HEADER_BEGIN}\n")
            f.write(f"Version: {FORMAT_VERSION}.0\n")
            f.write(f"Original: {original_name}\n")
            f.write(f"Type: {original_type}\n")
            f.write(f"{HEADER_END}\n\n")
            f.write(encoded)
            f.write(f"\n\n{FOOTER_BEGIN}\n")
            f.write(f"Checksum: {checksum}\n")
            f.write(f"{FOOTER_END}\n")

    def reveal_file(self, morphed_path: Path, output_path: Path, password: str) -> None:
        content = morphed_path.read_text(encoding="utf-8")
        checksum = self._extract_checksum(content)
        payload_b64 = self._extract_payload(content)

        payload = base64.b64decode(payload_b64)

        offset = 0
        magic = payload[offset : offset + 4]
        if magic != MAGIC:
            raise ValueError("Invalid suipian file: bad magic bytes")
        offset += 4

        format_ver, salt_size, nonce_size = struct.unpack("!BII", payload[offset : offset + 9])
        offset += 9

        salt = payload[offset : offset + salt_size]
        offset += salt_size
        nonce = payload[offset : offset + nonce_size]
        offset += nonce_size

        encrypted_len = struct.unpack("!I", payload[offset : offset + 4])[0]
        offset += 4
        ciphertext = payload[offset : offset + encrypted_len]

        decrypted = self._decrypt(salt, nonce, ciphertext, password)
        decompressed = self._decompress(decrypted)

        actual_checksum = hashlib.sha256(decompressed).hexdigest()
        if not hmac.compare_digest(actual_checksum, checksum):
            raise ValueError("Checksum mismatch - wrong password or corrupted file")

        output_path.write_bytes(decompressed)

    def validate(self, morphed_path: Path) -> tuple[bool, MorphedFileInfo | None, str | None]:
        try:
            content = morphed_path.read_text(encoding="utf-8")
            if HEADER_BEGIN not in content or HEADER_END not in content:
                return False, None, "Missing header markers"
            if FOOTER_BEGIN not in content or FOOTER_END not in content:
                return False, None, "Missing footer markers"

            info = self._parse_header(content)
            if info is None:
                return False, None, "Could not parse header"

            payload_b64 = self._extract_payload(content)
            payload = base64.b64decode(payload_b64)

            if payload[:4] != MAGIC:
                return False, None, "Invalid magic bytes"

            return True, info, None
        except Exception as e:
            return False, None, str(e)

    def get_info(self, morphed_path: Path) -> MorphedFileInfo | None:
        content = morphed_path.read_text(encoding="utf-8")
        return self._parse_header(content)

    def _get_mime_type(self, data: bytes) -> str:
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if data[:2] == b"\xff\xd8":
            return "image/jpeg"
        if data[:4] == b"GIF8":
            return "image/gif"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"
        if data[:4] == b"%PDF":
            return "application/pdf"
        if data[:4] == b"PK\x03\x04":
            return "application/zip"
        return "application/octet-stream"

    def _parse_header(self, content: str) -> MorphedFileInfo | None:
        try:
            header_block = content.split(HEADER_BEGIN)[1].split(HEADER_END)[0]
            lines = [ln.strip() for ln in header_block.strip().split("\n")]
            info = {}
            for line in lines:
                if ":" in line:
                    key, val = line.split(":", 1)
                    info[key.strip()] = val.strip()

            checksum_block = content.split(FOOTER_BEGIN)[1].split(FOOTER_END)[0]
            checksum = checksum_block.split("Checksum:")[1].strip()

            payload_b64 = self._extract_payload(content)
            payload_bytes = base64.b64decode(payload_b64)

            return MorphedFileInfo(
                version=info.get("Version", "1.0"),
                original_name=info.get("Original", "unknown"),
                original_type=info.get("Type", "unknown"),
                checksum=checksum,
                payload_size=len(payload_bytes),
            )
        except Exception:
            return None

    def _extract_payload(self, content: str) -> str:
        between = content.split(HEADER_END)[1].split(FOOTER_BEGIN)[0].strip()
        return between.strip()

    def _extract_checksum(self, content: str) -> str:
        footer_block = content.split(FOOTER_BEGIN)[1].split(FOOTER_END)[0]
        return footer_block.split("Checksum:")[1].strip()
