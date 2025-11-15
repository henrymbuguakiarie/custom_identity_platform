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

# Save client_id to a JSON file for later use
with open("oauth_client.json", "w") as f:
    json.dump({"client_id": client_id}, f, indent=2)

print("Seeded OAuth client_id:", client_id)
db.close()
