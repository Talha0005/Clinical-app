#!/usr/bin/env python3
"""
NHS API RSA Key Pair Generator
Generates the RSA key pair needed for NHS API authentication
"""

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pathlib import Path
import os

def generate_rsa_keypair():
    """Generate RSA key pair for NHS API authentication"""
    
    print("🔐 Generating RSA Key Pair for NHS API Authentication")
    print("=" * 60)
    
    # Generate private key
    print("Generating 2048-bit RSA private key...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # Get public key
    public_key = private_key.public_key()
    
    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Serialize public key
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    # Create keys directory
    keys_dir = Path("backend/keys")
    keys_dir.mkdir(exist_ok=True)
    
    # Save private key
    private_key_path = keys_dir / "nhs_private_key.pem"
    with open(private_key_path, "wb") as f:
        f.write(private_pem)
    
    # Save public key
    public_key_path = keys_dir / "nhs_public_key.pem"
    with open(public_key_path, "wb") as f:
        f.write(public_pem)
    
    # Set secure permissions on private key
    os.chmod(private_key_path, 0o600)
    
    print(f"✅ Private key saved to: {private_key_path}")
    print(f"✅ Public key saved to: {public_key_path}")
    print()
    
    print("📋 NEXT STEPS:")
    print("1. Upload the PUBLIC key to your NHS Developer Portal:")
    print("   - Log into https://digital.nhs.uk/developer")
    print("   - Go to your application settings")
    print("   - Upload the public key (nhs_public_key.pem)")
    print()
    print("2. The public key content is:")
    print("-" * 40)
    print(public_pem.decode('utf-8'))
    print("-" * 40)
    print()
    print("3. Keep the private key secure and NEVER share it!")
    print("4. The private key will be used automatically by the application")
    
    return private_key_path, public_key_path

if __name__ == "__main__":
    try:
        generate_rsa_keypair()
        print("\n🎉 RSA key pair generated successfully!")
    except Exception as e:
        print(f"❌ Error generating keys: {e}")
        print("Make sure you have the 'cryptography' package installed:")
        print("pip install cryptography")