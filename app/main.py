from fastapi import FastAPI
from app.routes import auth, admin, jwks

app = FastAPI(title="Custom Identity Platform API", version="0.1.0")

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(jwks.router)