import base64
import hashlib
import hmac
import json
import os
import time

PBKDF2_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 260000

SESSION_COOKIE = "spendly_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30


def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return "$".join(
        [PBKDF2_ALGORITHM, str(PBKDF2_ITERATIONS), salt.hex(), digest.hex()]
    )


def verify_password(password, stored):
    if not stored:
        return False
    parts = stored.split("$")
    if len(parts) != 4 or parts[0] != PBKDF2_ALGORITHM:
        return False
    _, iterations, salt_hex, expected_hex = parts
    try:
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), expected_hex)


def _b64url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value):
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(payload, secret):
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()


def make_session_token(uid, secret):
    payload = json.dumps(
        {"uid": uid, "exp": int(time.time()) + SESSION_MAX_AGE}
    ).encode("utf-8")
    body = _b64url_encode(payload)
    sig = _b64url_encode(_sign(payload, secret))
    return "{}.{}".format(body, sig)


def read_session_token(token, secret):
    if not token:
        return None
    try:
        body, sig = token.split(".")
        payload = _b64url_decode(body)
        expected = _b64url_decode(sig)
    except (ValueError, TypeError):
        return None
    if not hmac.compare_digest(_sign(payload, secret), expected):
        return None
    try:
        data = json.loads(payload)
    except ValueError:
        return None
    if int(data.get("exp", 0)) < time.time():
        return None
    return int(data["uid"])
