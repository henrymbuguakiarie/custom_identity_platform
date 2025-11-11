from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: str | None = None
    phone_number: str | None = None
    avatar_url: str | None = None

    model_config = {
        "from_attributes": True
    }

class RefreshTokenRequest(BaseModel):
    refresh_token: str