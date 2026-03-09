from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import AsyncSessionLocal
from app.models import User
from app.core.security import verify_password, create_access_token

router = APIRouter()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

class UserLogin(BaseModel):
    username: str
    password: str

@router.post("/auth/login")
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticate a user.

    - **username**: existing username
    - **password**: plain text password

    Raises 401 if username not found or password is incorrect.
    """
    
    result = await db.execute(
        select(User).filter(User.username == user.username)
    )
    existing_user = result.scalars().first()

    if not existing_user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_password(user.password, existing_user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {"msg": "Login successful", "username": existing_user.username}
   