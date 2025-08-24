from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Union
from datetime import datetime
import hashlib
import hmac
import json

class SignedEnvelope(BaseModel):
    """Secure message envelope with signature verification"""
    
    # Envelope metadata
    envelope_version: str = Field(default="1.0")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Message content (encrypted or plaintext)
    message: Dict[str, Any] = Field(..., description="The actual message payload")
    message_hash: str = Field(..., description="SHA-256 hash of message content")
    
    # Security
    signature: str = Field(..., description="HMAC-SHA256 signature")
    key_id: Optional[str] = Field(None, description="Key identifier for rotation")
    
    # NATS-specific
    nats_subject: str = Field(..., description="NATS subject for verification")
    nats_headers: Dict[str, str] = Field(default_factory=dict)
    
    @validator('message_hash')
    def validate_message_hash(cls, v, values):
        if 'message' in values:
            expected_hash = hashlib.sha256(
                json.dumps(values['message'], sort_keys=True).encode()
            ).hexdigest()
            if v != expected_hash:
                raise ValueError('Message hash does not match content')
        return v
    
    def verify_signature(self, secret: str) -> bool:
        """Verify the HMAC signature"""
        message_str = json.dumps(self.message, sort_keys=True)
        payload = f"{self.nats_subject}:{message_str}:{self.created_at.isoformat()}"
        
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(self.signature, expected_signature)
    
    @classmethod
    def create_signed(cls, message: Dict[str, Any], subject: str, secret: str, key_id: str = None) -> 'SignedEnvelope':
        """Create a signed envelope"""
        created_at = datetime.utcnow()
        message_hash = hashlib.sha256(
            json.dumps(message, sort_keys=True).encode()
        ).hexdigest()
        
        payload = f"{subject}:{json.dumps(message, sort_keys=True)}:{created_at.isoformat()}"
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return cls(
            message=message,
            message_hash=message_hash,
            signature=signature,
            key_id=key_id,
            nats_subject=subject,
            created_at=created_at
        )