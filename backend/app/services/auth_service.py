import hashlib
import hmac
import secrets
from typing import Dict, Optional
from uuid import uuid4

from app.schemas.auth import AuthUser


class AuthService:
    def __init__(self) -> None:
        self._users: Dict[str, dict] = {}
        self._tokens: Dict[str, AuthUser] = {}

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000).hex()

    def register(self, name: str, email: str, password: str) -> AuthUser:
        normalized_email = self._normalize_email(email)
        if normalized_email in self._users:
            raise ValueError("An account with this email already exists")

        salt = secrets.token_bytes(16)
        self._users[normalized_email] = {
            "id": str(uuid4()),
            "name": name.strip(),
            "email": normalized_email,
            "salt": salt.hex(),
            "password_hash": self._hash_password(password, salt),
        }
        return self._to_user(self._users[normalized_email])

    def authenticate(self, email: str, password: str) -> Optional[AuthUser]:
        record = self._users.get(self._normalize_email(email))
        if record is None:
            return None
        salt = bytes.fromhex(record["salt"])
        password_hash = self._hash_password(password, salt)
        if not hmac.compare_digest(password_hash, record["password_hash"]):
            return None
        return self._to_user(record)

    def issue_token(self, user: AuthUser) -> str:
        token = secrets.token_urlsafe(32)
        self._tokens[token] = user
        return token

    def validate_token(self, token: str) -> Optional[AuthUser]:
        return self._tokens.get(token)

    @staticmethod
    def _to_user(record: dict) -> AuthUser:
        return AuthUser(id=record["id"], name=record["name"], email=record["email"])


# Replace with a persistent user repository when a database is introduced.
auth_service = AuthService()
