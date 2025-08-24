# Comprehensive data protection and encryption
import os
import hashlib
import secrets
from typing import Dict, List, Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
import json
from dataclasses import dataclass
from enum import Enum

class DataClassification(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

@dataclass
class EncryptionPolicy:
    classification: DataClassification
    encryption_required: bool
    key_rotation_days: int
    access_logging: bool
    retention_days: Optional[int] = None

class DataProtectionManager:
    def __init__(self):
        self.master_key = self._get_master_key()
        self.fernet = Fernet(self.master_key)
        self.aes_gcm = AESGCM(self._derive_aes_key())
        
        # Data classification policies
        self.policies = {
            DataClassification.PUBLIC: EncryptionPolicy(
                DataClassification.PUBLIC, False, 365, False
            ),
            DataClassification.INTERNAL: EncryptionPolicy(
                DataClassification.INTERNAL, True, 180, True, 2555  # 7 years
            ),
            DataClassification.CONFIDENTIAL: EncryptionPolicy(
                DataClassification.CONFIDENTIAL, True, 90, True, 1825  # 5 years
            ),
            DataClassification.RESTRICTED: EncryptionPolicy(
                DataClassification.RESTRICTED, True, 30, True, 365  # 1 year
            )
        }
    
    def _get_master_key(self) -> bytes:
        """Get or generate master encryption key"""
        key_file = "/etc/maf/keys/master.key"
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        
        # Generate new master key
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        
        with open(key_file, 'wb') as f:
            f.write(key)
        
        # Set restrictive permissions
        os.chmod(key_file, 0o600)
        return key
    
    def _derive_aes_key(self) -> bytes:
        """Derive AES key from master key"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'maf_aes_salt',
            iterations=100000,
        )
        return kdf.derive(self.master_key)
    
    def encrypt_data(self, data: Union[str, bytes], 
                    classification: DataClassification,
                    metadata: Dict[str, any] = None) -> Dict[str, any]:
        """Encrypt data based on classification"""
        policy = self.policies[classification]
        
        if not policy.encryption_required:
            return {
                "data": data if isinstance(data, str) else data.decode(),
                "encrypted": False,
                "classification": classification.value,
                "metadata": metadata or {}
            }
        
        # Convert to bytes if string
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Generate nonce for AES-GCM
        nonce = secrets.token_bytes(12)
        
        # Encrypt with AES-GCM
        ciphertext = self.aes_gcm.encrypt(nonce, data, None)
        
        # Create encrypted package
        encrypted_package = {
            "data": base64.b64encode(ciphertext).decode(),
            "nonce": base64.b64encode(nonce).decode(),
            "encrypted": True,
            "algorithm": "AES-GCM",
            "classification": classification.value,
            "encrypted_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        return encrypted_package
    
    def decrypt_data(self, encrypted_package: Dict[str, any]) -> Union[str, bytes]:
        """Decrypt data package"""
        if not encrypted_package.get("encrypted", False):
            return encrypted_package["data"]
        
        # Extract components
        ciphertext = base64.b64decode(encrypted_package["data"])
        nonce = base64.b64decode(encrypted_package["nonce"])
        
        # Decrypt
        plaintext = self.aes_gcm.decrypt(nonce, ciphertext, None)
        
        # Return as string if it was originally string data
        try:
            return plaintext.decode('utf-8')
        except UnicodeDecodeError:
            return plaintext
    
    def encrypt_database_field(self, value: str, field_name: str) -> str:
        """Encrypt database field with field-specific key derivation"""
        # Derive field-specific key
        field_key = self._derive_field_key(field_name)
        field_fernet = Fernet(field_key)
        
        encrypted = field_fernet.encrypt(value.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_database_field(self, encrypted_value: str, field_name: str) -> str:
        """Decrypt database field"""
        # Derive field-specific key
        field_key = self._derive_field_key(field_name)
        field_fernet = Fernet(field_key)
        
        encrypted_bytes = base64.b64decode(encrypted_value)
        decrypted = field_fernet.decrypt(encrypted_bytes)
        return decrypted.decode()
    
    def _derive_field_key(self, field_name: str) -> bytes:
        """Derive field-specific encryption key"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=f'maf_field_{field_name}'.encode(),
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(self.master_key))