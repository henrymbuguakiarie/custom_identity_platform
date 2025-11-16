from fastapi import APIRouter
from jose import jwk
from jose.utils import base64url_encode
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from app.config import settings  # adjust import as needed

router = APIRouter()

@router.get("/.well-known/jwks.json")
def get_jwks():
    with open(settings.public_key_path, "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())
    jwk_key = jwk.construct(public_key, algorithm="RS256")
    return {"keys": [jwk_key.to_dict()]}
