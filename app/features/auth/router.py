from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import AsyncSessionLocal
from app.models import User
from app.core.security import hash_password

router=APIRouter()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

class UserLogin(BaseModel):
    username: str
    password: str

@router.post("/auth/register")
async def register(user: UserLogin, db: AsyncSession=Depends(get_db)):
    """
    Register a new user.

    - **username**: unique username
    - **password**: plain text password (will be hashed)

    Raises 400 if username is already taken.
    """
    
    result = await db.execute(
        select(User).filter(User.username == user.username)
    )
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Username is already taken")

    hashed_password=hash_password(user.password)

    new_user=User(username=user.username, password=hashed_password)

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {"msg": "User registered successfully!"}