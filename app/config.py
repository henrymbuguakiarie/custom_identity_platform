from pydantic_settings import BaseSettings
from pathlib import Path
from pydantic import PrivateAttr


class Settings(BaseSettings):
    secret_key: str = "your_secret_key"
    algorithm: str = "HS256"
     # Token expiration times
    access_token_expire_minutes: int = 30   # Access token lifetime
    refresh_token_expire_days: int = 7      # Refresh token lifetime (new)
    database_url: str = "postgresql+psycopg2://postgres:paswword@localhost:5432/identity_db"
    key_id: str = "1"

        # Optional environment-based fields
    private_key_path: str = "/Users/henrymbugua/Documents/01_Microsft_Work/15_personal_learning/identity-platform/private_key.pem"
    public_key_path: str = "/Users/henrymbugua/Documents/01_Microsft_Work/15_personal_learning/identity-platform/public_key.pem"

    # Private attributes (not validated by Pydantic)
    _private_key: str = PrivateAttr(default=None)
    _public_key: str = PrivateAttr(default=None)

    def load_keys(self):
        """Read the PEM files into memory once."""
        private_path = Path(self.private_key_path)
        public_path = Path(self.public_key_path)

        if private_path.exists():
            self._private_key = private_path.read_text()
        else:
            raise FileNotFoundError(f"Private key not found at {private_path}")

        if public_path.exists():
            self._public_key = public_path.read_text()
        else:
            raise FileNotFoundError(f"Public key not found at {public_path}")

    @property
    def private_key(self):
        if not self._private_key:
            self.load_keys()
        return self._private_key

    @property
    def public_key(self):
        if not self._public_key:
            self.load_keys()
        return self._public_key

    class Config:
        env_file = ".env"  # optional, useful if you want to move secrets here later


settings = Settings()