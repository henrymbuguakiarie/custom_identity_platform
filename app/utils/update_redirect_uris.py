from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.oauth import OAuthClient

def main():
    db: Session = SessionLocal()
    try:
        # Replace with your actual client_id
        client_id = "BHKJZ8S12H-Op4XlrhDWIZscE3vBToxV"
        client = db.query(OAuthClient).filter_by(client_id=client_id).first()
        if not client:
            print("Client not found")
            return

        client.redirect_uris = "http://127.0.0.1:8000/callback\nhttps://app.example.com/callback"
        db.commit()
        print(f"Updated redirect_uris for client {client_id}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
