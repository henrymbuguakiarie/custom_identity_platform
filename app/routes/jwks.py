from fastapi import APIRouter
from jose import jwk
from jose.utils import base64url_encode
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from app.config import settings  # adjust import as needed

router = APIRouter()

@router.get("/.well-known/jwks.json")
def get_jwks():
    # Load PEM public key content (string)
    public_pem = settings.public_key

    # Convert PEM string → RSA public key object
    public_key = serialization.load_pem_public_key(
        public_pem.encode("utf-8"), backend=default_backend()
    )

    # Extract modulus (n) and exponent (e)
    numbers = public_key.public_numbers()
    e = base64url_encode(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")).decode("utf-8")
    n = base64url_encode(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")).decode("utf-8")

    # Build JWK
    jwk_data = {
        "kty": "RSA",
        "use": "sig",
        "kid": "rsa1",  # can be a hash of the key
        "alg": "RS256",
        "n": n,
        "e": e
    }

    return {"keys": [jwk_data]}
