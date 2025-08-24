#!/usr/bin/env python3
"""Configuration validation script"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings

def main():
    """Validate configuration and dump settings"""
    try:
        print("🔍 Validating Multi-Agent Factory configuration...")
        
        # Test settings loading
        config_dump = settings.dump_config()
        
        print("✅ Configuration loaded successfully!")
        print(f"Environment: {settings.env}")
        print(f"Debug mode: {settings.debug}")
        
        # Check required fields
        required_checks = [
            (settings.llm.openai_api_key, "OpenAI API key"),
            (settings.security.jwt_secret, "JWT secret"),
            (settings.security.encryption_key, "Encryption key"),
            (settings.database.user, "Database user"),
            (settings.database.password, "Database password"),
        ]
        
        missing_required = []
        for value, name in required_checks:
            if not value or value in ["your-key-here", "change-this"]:
                missing_required.append(name)
        
        if missing_required:
            print("⚠️  Missing required configuration:")
            for item in missing_required:
                print(f"   - {item}")
            print("\n💡 Update your .env file with production values")
        
        # Dump configuration (with secrets masked)
        print("\n📋 Configuration dump:")
        print(json.dumps(config_dump, indent=2))
        
        return 0 if not missing_required else 1
        
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())