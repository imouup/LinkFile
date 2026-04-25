from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def generate_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def encrypt_json_bytes(
    key: bytes,
    plaintext: bytes,
    associated_data: bytes | None = None,
) -> dict[str, str]:
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, associated_data)
    return {
        "ciphertext": base64.urlsafe_b64encode(ciphertext).decode("ascii"),
        "nonce": base64.urlsafe_b64encode(nonce).decode("ascii"),
        "algorithm": "AES-256-GCM",
    }


def decrypt_json_bytes(
    key: bytes,
    payload: dict[str, str],
    associated_data: bytes | None = None,
) -> bytes:
    nonce = base64.urlsafe_b64decode(payload["nonce"])
    ciphertext = base64.urlsafe_b64decode(payload["ciphertext"])
    return AESGCM(key).decrypt(nonce, ciphertext, associated_data)
