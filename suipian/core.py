from __future__ import annotations

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

MAGIC = b"SPRF"
FORMAT_VERSION = 1

ZW_ZERO = "\u200b"
ZW_ONE = "\u200c"
ZW_CHARS = {ZW_ZERO, ZW_ONE}


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

    def _build_payload(
        self, source_data: bytes, original_name: str, original_type: str, password: str
    ) -> bytes:
        compressed = self._compress(source_data)
        salt, nonce, encrypted = self._encrypt(compressed, password)

        name_bytes = original_name.encode("utf-8")
        type_bytes = original_type.encode("utf-8")
        checksum = hashlib.sha256(source_data).digest()

        payload = MAGIC
        payload += struct.pack("!B", FORMAT_VERSION)
        payload += struct.pack("!H", len(name_bytes))
        payload += name_bytes
        payload += struct.pack("!H", len(type_bytes))
        payload += type_bytes
        payload += checksum
        payload += salt
        payload += nonce
        payload += struct.pack("!I", len(encrypted))
        payload += encrypted
        return payload

    def _parse_payload(self, payload: bytes) -> dict:
        offset = 0
        magic = payload[offset : offset + 4]
        if magic != MAGIC:
            raise ValueError("Invalid suipian file: bad magic bytes")
        offset += 4

        format_ver = struct.unpack("!B", payload[offset : offset + 1])[0]
        offset += 1

        name_len = struct.unpack("!H", payload[offset : offset + 2])[0]
        offset += 2
        original_name = payload[offset : offset + name_len].decode("utf-8")
        offset += name_len

        type_len = struct.unpack("!H", payload[offset : offset + 2])[0]
        offset += 2
        original_type = payload[offset : offset + type_len].decode("utf-8")
        offset += type_len

        checksum = payload[offset : offset + 32]
        offset += 32

        salt = payload[offset : offset + self.salt_size]
        offset += self.salt_size
        nonce = payload[offset : offset + self.nonce_size]
        offset += self.nonce_size

        encrypted_len = struct.unpack("!I", payload[offset : offset + 4])[0]
        offset += 4
        ciphertext = payload[offset : offset + encrypted_len]

        return {
            "version": f"{format_ver}.0",
            "original_name": original_name,
            "original_type": original_type,
            "checksum": checksum,
            "salt": salt,
            "nonce": nonce,
            "ciphertext": ciphertext,
            "payload_size": len(payload),
        }

    @staticmethod
    def _bytes_to_zw(data: bytes) -> str:
        bits = []
        for byte in data:
            for i in range(7, -1, -1):
                bits.append(ZW_ONE if (byte >> i) & 1 else ZW_ZERO)
        return "".join(bits)

    @staticmethod
    def _zw_to_bytes(zw_str: str) -> bytes:
        bits = [1 if c == ZW_ONE else 0 for c in zw_str]
        byte_vals = []
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                if i + j < len(bits):
                    byte = (byte << 1) | bits[i + j]
                else:
                    byte <<= 1
            byte_vals.append(byte)
        return bytes(byte_vals)

    @staticmethod
    def _extract_zw(text: str) -> str:
        return "".join(c for c in text if c in ZW_CHARS)

    @staticmethod
    def _embed_zw(carrier: str, zw_data: str) -> str:
        return carrier + zw_data

    def hide_file(
        self, source_path: Path, carrier_path: Path, output_path: Path, password: str
    ) -> None:
        source_data = source_path.read_bytes()
        original_name = source_path.name
        original_type = self._get_mime_type(source_data)

        payload = self._build_payload(source_data, original_name, original_type, password)
        zw_data = self._bytes_to_zw(payload)

        carrier_content = carrier_path.read_text(encoding="utf-8") if carrier_path.exists() else ""
        stego_text = self._embed_zw(carrier_content, zw_data)

        output_path.write_text(stego_text, encoding="utf-8")

    def reveal_file(self, morphed_path: Path, output_path: Path, password: str) -> None:
        content = morphed_path.read_text(encoding="utf-8")
        zw_data = self._extract_zw(content)

        if not zw_data:
            raise ValueError("No hidden data found in file")

        payload = self._zw_to_bytes(zw_data)
        info = self._parse_payload(payload)

        decrypted = self._decrypt(info["salt"], info["nonce"], info["ciphertext"], password)
        decompressed = self._decompress(decrypted)

        actual_checksum = hashlib.sha256(decompressed).digest()
        if not hmac.compare_digest(actual_checksum, info["checksum"]):
            raise ValueError("Checksum mismatch - wrong password or corrupted file")

        output_path.write_bytes(decompressed)

    def validate(self, morphed_path: Path) -> tuple[bool, MorphedFileInfo | None, str | None]:
        try:
            content = morphed_path.read_text(encoding="utf-8")
            zw_data = self._extract_zw(content)

            if not zw_data:
                return False, None, "No hidden data found"

            payload = self._zw_to_bytes(zw_data)
            info = self._parse_payload(payload)

            file_info = MorphedFileInfo(
                version=info["version"],
                original_name=info["original_name"],
                original_type=info["original_type"],
                checksum=info["checksum"].hex(),
                payload_size=info["payload_size"],
            )
            return True, file_info, None
        except Exception as e:
            return False, None, str(e)

    def get_info(self, morphed_path: Path) -> MorphedFileInfo | None:
        content = morphed_path.read_text(encoding="utf-8")
        zw_data = self._extract_zw(content)
        if not zw_data:
            return None

        payload = self._zw_to_bytes(zw_data)
        try:
            info = self._parse_payload(payload)
            return MorphedFileInfo(
                version=info["version"],
                original_name=info["original_name"],
                original_type=info["original_type"],
                checksum=info["checksum"].hex(),
                payload_size=info["payload_size"],
            )
        except Exception:
            return None

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
