from pydantic_settings import BaseSettings
from pathlib import Path
from pydantic import PrivateAttr

class Settings(BaseSettings):
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    database_url: str
    sqlalchemy_url: str
    key_id: str

    private_key_path: str
    public_key_path: str

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
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
