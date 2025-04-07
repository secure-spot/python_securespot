from passlib.context import CryptContext
from jose import jwt
from config import settings
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def hash_password(password: str) -> str:
    return pwd_context.hash(password)

async def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

async def create_access_token(data: dict):
    data["jti"] = str(uuid.uuid4())
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)