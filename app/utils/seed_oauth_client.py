from app.database import SessionLocal
from app.models.oauth import OAuthClient
import secrets, json

db = SessionLocal()
client_id = secrets.token_urlsafe(24)
client = OAuthClient(
    client_id=client_id,
    client_name="Example SPA",
    client_secret=None,  # public client
    redirect_uris="http://127.0.0.1:3000/callback\nhttps://app.example.com/callback",
    is_confidential=False,
)
db.add(client)
db.commit()
print("client_id:", client_id)
db.close()
