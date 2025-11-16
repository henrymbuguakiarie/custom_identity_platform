from fastapi import FastAPI
from app.routes import auth, admin, jwks, authorize, callback
from fastapi import FastAPI
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Custom Identity Platform API", version="0.1.0")
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(jwks.router)
app.include_router(authorize.router)
app.include_router(callback.router)