import hashlib
import base64
import secrets

def generate_code_verifier(length: int = 64) -> str:
    # returns a high-entropy URL-safe string
    return secrets.token_urlsafe(length)[:128]

def generate_code_challenge_s256(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

def verify_code_challenge(code_verifier: str, code_challenge: str, method: str) -> bool:
    if method is None:
        # if no method was specified, fallback not recommended — enforce S256
        return False
    method = method.upper()
    if method == "S256":
        return generate_code_challenge_s256(code_verifier) == code_challenge
    # plain is discouraged; allow if explicitly supported
    if method == "PLAIN":
        return code_verifier == code_challenge
    return False
