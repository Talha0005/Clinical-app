#!/usr/bin/env python3
"""
Debug JWT creation for NHS API
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import jwt
import json
from cryptography.hazmat.primitives import serialization

# Add backend to path
backend_path = Path(__file__).parent.parent  # Go up to backend/
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
load_dotenv()

def test_jwt_creation():
    """Test JWT creation and show details"""
    
    client_id = os.getenv("NHS_CLIENT_ID")
    client_secret = os.getenv("NHS_CLIENT_SECRET")
    
    print("🔍 JWT Debugging for NHS API")
    print("=" * 60)
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {client_secret[:10]}...")
    print()
    
    # Load private key
    key_path = Path("backend/keys/nhs_private_key.pem")
    if not key_path.exists():
        print("❌ Private key not found!")
        return
    
    with open(key_path, 'rb') as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
        )
    
    # Create JWT
    now = datetime.utcnow()
    print(f"Current UTC time: {now}")
    print()
    
    # Try different time configurations
    configs = [
        {"name": "Standard", "iat": now, "exp": now + timedelta(minutes=5)},
        {"name": "With buffer", "iat": now - timedelta(seconds=30), "exp": now + timedelta(minutes=10)},
        {"name": "Future", "iat": now + timedelta(seconds=30), "exp": now + timedelta(minutes=5, seconds=30)},
    ]
    
    token_url = "https://sandbox.api.service.nhs.uk/oauth2/token"
    
    for config in configs:
        print(f"\n📝 JWT Config: {config['name']}")
        print("-" * 40)
        
        payload = {
            "iss": client_id,
            "sub": client_id,
            "aud": token_url,
            "jti": "test-" + str(int(now.timestamp())),
            "exp": int(config["exp"].timestamp()),
            "iat": int(config["iat"].timestamp()),
        }
        
        print(f"Issued at (iat): {config['iat']} ({payload['iat']})")
        print(f"Expires (exp): {config['exp']} ({payload['exp']})")
        print(f"Valid for: {(config['exp'] - config['iat']).total_seconds()} seconds")
        
        # Create token
        token = jwt.encode(payload, private_key, algorithm="RS512")
        
        # Decode without verification to show contents
        decoded = jwt.decode(token, options={"verify_signature": False})
        print(f"\nDecoded payload:")
        print(json.dumps(decoded, indent=2))
        
        print(f"\nToken (first 100 chars):")
        print(token[:100] + "...")
    
    print("\n" + "=" * 60)
    print("📋 NHS Portal Instructions:")
    print("1. Log into https://digital.nhs.uk/developer")
    print("2. Find your Doogie-AI app or organization settings")
    print("3. Upload the public key from: backend/keys/nhs_public_key.pem")
    print("4. Save and wait 5-10 minutes for propagation")
    print("5. Run test_nhs_api.py again")

if __name__ == "__main__":
    test_jwt_creation()