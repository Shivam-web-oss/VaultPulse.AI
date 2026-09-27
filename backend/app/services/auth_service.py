import hashlib
import hmac
import secrets
from typing import Optional
from uuid import uuid4

from app.db import connection
from app.schemas.auth import AuthUser


class AuthService:
    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000).hex()

    def register(self, name: str, email: str, password: str) -> AuthUser:
        normalized_email = self._normalize_email(email)
        salt = secrets.token_bytes(16)
        record = {
            "id": uuid4(),
            "name": name.strip(),
            "email": normalized_email,
            "salt": salt.hex(),
            "password_hash": self._hash_password(password, salt),
        }
        try:
            with connection() as conn:
                conn.execute(
                    "insert into app_users (id, name, email, salt, password_hash) values (%s, %s, %s, %s, %s)",
                    tuple(record.values()),
                )
                conn.commit()
        except Exception as error:
            if getattr(error, "sqlstate", None) == "23505":
                raise ValueError("An account with this email already exists") from error
            raise
        return self._to_user(record)

    def authenticate(self, email: str, password: str) -> Optional[AuthUser]:
        with connection() as conn:
            record = conn.execute(
                "select id, name, email, salt, password_hash from app_users where email = %s",
                (self._normalize_email(email),),
            ).fetchone()
        if record is None:
            return None
        salt = bytes.fromhex(record["salt"])
        password_hash = self._hash_password(password, salt)
        if not hmac.compare_digest(password_hash, record["password_hash"]):
            return None
        return self._to_user(record)

    def issue_token(self, user: AuthUser) -> str:
        token = secrets.token_urlsafe(32)
        with connection() as conn:
            conn.execute("insert into auth_sessions (token, user_id) values (%s, %s)", (token, user.id))
            conn.commit()
        return token

    def validate_token(self, token: str) -> Optional[AuthUser]:
        with connection() as conn:
            record = conn.execute(
                "select u.id, u.name, u.email from auth_sessions s join app_users u on u.id = s.user_id where s.token = %s",
                (token,),
            ).fetchone()
        return self._to_user(record) if record else None

    @staticmethod
    def _to_user(record: dict) -> AuthUser:
        return AuthUser(id=str(record["id"]), name=record["name"], email=record["email"])


# Replace with a persistent user repository when a database is introduced.
auth_service = AuthService()
