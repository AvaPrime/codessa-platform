# Comprehensive encryption implementation
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from typing import bytes, str, Optional
import secrets

class EncryptionManager:
    def __init__(self):
        self.master_key = self._get_or_create_master_key()
        self.fernet = Fernet(self.master_key)
    
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key"""
        key_file = "/etc/maf/master.key"
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            os.makedirs(os.path.dirname(key_file), exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            return key
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data using Fernet"""
        if not data:
            return data
        
        encrypted = self.fernet.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not encrypted_data:
            return encrypted_data
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception:
            raise ValueError("Failed to decrypt data")
    
    def encrypt_file(self, file_path: str, output_path: str):
        """Encrypt file using AES-256-GCM"""
        key = secrets.token_bytes(32)  # 256-bit key
        iv = secrets.token_bytes(16)   # 128-bit IV
        
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
        encryptor = cipher.encryptor()
        
        with open(file_path, 'rb') as infile, open(output_path, 'wb') as outfile:
            # Write key and IV (encrypted with master key)
            encrypted_key = self.fernet.encrypt(key)
            outfile.write(len(encrypted_key).to_bytes(4, 'big'))
            outfile.write(encrypted_key)
            outfile.write(iv)
            
            # Encrypt file content
            while True:
                chunk = infile.read(8192)
                if not chunk:
                    break
                outfile.write(encryptor.update(chunk))
            
            # Write authentication tag
            outfile.write(encryptor.finalize())
            outfile.write(encryptor.tag)

# Database field encryption
class EncryptedField:
    def __init__(self, encryption_manager: EncryptionManager):
        self.encryption_manager = encryption_manager
    
    def encrypt(self, value: str) -> str:
        if value is None:
            return None
        return self.encryption_manager.encrypt_sensitive_data(value)
    
    def decrypt(self, encrypted_value: str) -> str:
        if encrypted_value is None:
            return None
        return self.encryption_manager.decrypt_sensitive_data(encrypted_value)