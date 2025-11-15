from app.database import SessionLocal
from app.models.oauth import OAuthClient
import secrets, json

db = SessionLocal()

# Check if client already exists
client = db.query(OAuthClient).filter_by(client_name="Example SPA").first()
if not client:
    client_id = secrets.token_urlsafe(24)
    client = OAuthClient(
        client_id=client_id,
        client_name="Example SPA",
        client_secret=None,
        redirect_uris="http://127.0.0.1:3000/callback\nhttps://app.example.com/callback",
        is_confidential=False,
    )
    db.add(client)
    db.commit()
    print("Seeded new OAuth client_id:", client_id)
else:
    client_id = client.client_id
    print("OAuth client already exists:", client_id)

# Update redirect URIs (idempotent)
client.redirect_uris = "http://127.0.0.1:8000/callback\nhttps://app.example.com/callback"
db.commit()
print(f"Updated redirect_uris for client {client_id}")

# Save to JSON for other scripts
with open("oauth_client.json", "w") as f:
    json.dump({"client_id": client_id}, f, indent=2)

db.close()
