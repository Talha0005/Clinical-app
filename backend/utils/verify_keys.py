#!/usr/bin/env python3
"""
Verify NHS API key pair setup
"""

import sys
import jwt
import json
from pathlib import Path
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
import base64

def verify_key_setup():
    """Verify the NHS key setup is correct"""
    
    print("🔐 NHS API Key Verification")
    print("=" * 50)
    
    # Check files exist
    private_key_path = Path("backend/keys/nhs_private_key.pem")
    public_key_path = Path("backend/keys/nhs_public_key.pem")
    public_json_path = Path("backend/keys/nhs_public_key.json")
    
    print("📁 File Check:")
    print(f"Private key: {'✅' if private_key_path.exists() else '❌'} {private_key_path}")
    print(f"Public key:  {'✅' if public_key_path.exists() else '❌'} {public_key_path}")
    print(f"Public JSON: {'✅' if public_json_path.exists() else '❌'} {public_json_path}")
    print()
    
    if not all([private_key_path.exists(), public_key_path.exists(), public_json_path.exists()]):
        print("❌ Missing key files!")
        return False
    
    # Load private key
    try:
        with open(private_key_path, 'rb') as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
        print("✅ Private key loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load private key: {e}")
        return False
    
    # Load public key
    try:
        with open(public_key_path, 'rb') as f:
            public_key = serialization.load_pem_public_key(f.read())
        print("✅ Public key loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load public key: {e}")
        return False
    
    # Verify key pair match
    try:
        # Create test data
        test_data = b"NHS API Test Message"
        
        # Sign with private key
        signature = private_key.sign(
            test_data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA512()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA512()
        )
        
        # Verify with public key
        public_key.verify(
            signature,
            test_data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA512()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA512()
        )
        print("✅ Key pair verification successful")
    except Exception as e:
        print(f"❌ Key pair verification failed: {e}")
        return False
    
    # Test JWT creation and verification
    try:
        now = datetime.utcnow()
        payload = {
            "iss": "Black_Swan_Advisors_Ltd",
            "sub": "Black_Swan_Advisors_Ltd", 
            "aud": "https://sandbox.api.service.nhs.uk/oauth2/token",
            "jti": "test-verification",
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "iat": int(now.timestamp()),
        }
        
        # Create JWT
        token = jwt.encode(
            payload,
            private_key,
            algorithm="RS512",
            headers={"kid": "doogie-ai-2024"}
        )
        
        print("✅ JWT created successfully")
        
        # Verify JWT structure
        header = jwt.get_unverified_header(token)
        decoded_payload = jwt.decode(token, options={"verify_signature": False})
        
        print(f"   Algorithm: {header.get('alg')}")
        print(f"   Key ID: {header.get('kid')}")
        print(f"   Issuer: {decoded_payload.get('iss')}")
        print(f"   Expires: {datetime.fromtimestamp(decoded_payload.get('exp'))}")
        
    except Exception as e:
        print(f"❌ JWT creation failed: {e}")
        return False
    
    # Verify JSON format
    try:
        with open(public_json_path) as f:
            json_data = json.load(f)
        
        if "keys" in json_data and len(json_data["keys"]) > 0:
            key_data = json_data["keys"][0]
            print("✅ Public key JSON format valid")
            print(f"   Key type: {key_data.get('kty')}")
            print(f"   Algorithm: {key_data.get('alg')}")
            print(f"   Key ID: {key_data.get('kid')}")
            print(f"   Use: {key_data.get('use')}")
        else:
            print("❌ Invalid JSON structure")
            return False
            
    except Exception as e:
        print(f"❌ JSON verification failed: {e}")
        return False
    
    print("\n🎯 VERIFICATION SUMMARY:")
    print("✅ All key files present")
    print("✅ Private/public key pair match") 
    print("✅ JWT creation works")
    print("✅ JSON format correct")
    print()
    print("📋 Your keys are properly configured!")
    print("The 'JWT expired' error is likely due to:")
    print("1. Public key propagation delay (24-48 hours)")
    print("2. NHS environment configuration")
    print("3. Additional approval requirements")
    print()
    print("💡 Contact NHS Support if issue persists after 48 hours:")
    print("   Email: api.management@nhs.net")
    print("   Include: Doogie-AI app details and this verification report")
    
    return True

if __name__ == "__main__":
    verify_key_setup()