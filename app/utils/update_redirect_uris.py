from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.oauth import OAuthClient
import json

def main():
    db: Session = SessionLocal()
    try:
        # Read client_id from JSON file
        with open("oauth_client.json") as f:
            data = json.load(f)
        client_id = data["client_id"]

        client = db.query(OAuthClient).filter_by(client_id=client_id).first()
        if not client:
            print("Client not found")
            return

        # Update redirect URIs
        client.redirect_uris = "http://127.0.0.1:8000/callback\nhttps://app.example.com/callback"
        db.commit()
        print(f"Updated redirect_uris for client {client_id}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
