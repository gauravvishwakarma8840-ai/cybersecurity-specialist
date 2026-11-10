"""
RSA Key Pair Generator for JWT Authentication (RS256)
Generates 2048-bit RSA private and public keys and saves them to the certs directory.
"""
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

CERTS_DIR = Path(__file__).resolve().parent / "certs"


def generate_keys():
    CERTS_DIR.mkdir(parents=True, exist_ok=True)
    private_key_path = CERTS_DIR / "private.pem"
    public_key_path = CERTS_DIR / "public.pem"

    if private_key_path.exists() and public_key_path.exists():
        print(f"[✓] RSA keys already exist in: {CERTS_DIR}")
        return

    print("Generating 2048-bit RSA key pair...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_key_path.write_bytes(private_pem)
    public_key_path.write_bytes(public_pem)

    print(f"[✓] Private key created at: {private_key_path}")
    print(f"[✓] Public key created at: {public_key_path}")


if __name__ == "__main__":
    generate_keys()

