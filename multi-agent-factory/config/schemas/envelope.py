# File: config/schemas/envelope.py
# Purpose: Security envelope and HMAC signature with canonicalized JSON.

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import hashlib, hmac, json

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class SignedEnvelope(BaseModel):
    envelope_version: str = "1.0"
    created_at: datetime = Field(default_factory=utcnow)
    subject: str
    message: Dict[str, Any]
    message_hash: str
    signature: str
    key_id: Optional[str] = None
    nats_headers: Dict[str, str] = Field(default_factory=dict)

    @staticmethod
    def _canonical(obj: Dict[str, Any]) -> str:
        # Stable canonical JSON for signing/verifying
        return json.dumps(obj, separators=(",", ":"), sort_keys=True)

    @classmethod
    def sign(cls, subject: str, message: Dict[str, Any], secret: str,
             key_id: Optional[str] = None, nats_headers: Optional[Dict[str, str]] = None) -> "SignedEnvelope":
        created = utcnow()
        canon = cls._canonical(message)
        msg_hash = hashlib.sha256(canon.encode()).hexdigest()
        payload = f"{subject}:{canon}:{created.isoformat()}"
        sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return cls(
            subject=subject,
            message=message,
            message_hash=msg_hash,
            signature=sig,
            key_id=key_id,
            created_at=created,
            nats_headers=nats_headers or {},
        )

    def verify(self, secret: str) -> bool:
        canon = self._canonical(self.message)
        expected_hash = hashlib.sha256(canon.encode()).hexdigest()
        if expected_hash != self.message_hash:
            return False
        payload = f"{self.subject}:{canon}:{self.created_at.isoformat()}"
        sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, self.signature)
