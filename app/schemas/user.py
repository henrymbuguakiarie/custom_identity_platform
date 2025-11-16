from pydantic import BaseModel, EmailStr, validator, Field
import re


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters, include uppercase, lowercase, number, and special character")

    @validator("password")
    def password_strength(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must include at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must include at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must include at least one number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must include at least one special character")
        return v

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