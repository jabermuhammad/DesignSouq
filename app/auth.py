import hashlib
import hmac
import secrets

PBKDF2_PREFIX = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 260000


def is_password_hashed(value: str) -> bool:
    if not value:
        return False
    if value.startswith(f"{PBKDF2_PREFIX}$"):
        return True
    return value.startswith("$2a$") or value.startswith("$2b$") or value.startswith("$2y$")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS)
    return f"{PBKDF2_PREFIX}${PBKDF2_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False

    # New local format
    if hashed.startswith(f"{PBKDF2_PREFIX}$"):
        parts = hashed.split("$", 3)
        if len(parts) != 4:
            return False
        _, iter_s, salt, expected_hex = parts
        try:
            iterations = int(iter_s)
        except ValueError:
            return False

        got = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations).hex()
        return hmac.compare_digest(got, expected_hex)

    # Unsupported legacy hash in this runtime
    return False
