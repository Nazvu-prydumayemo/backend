import asyncio

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


async def hash_password(password: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, pwd_context.hash, password)


async def verify_password(password: str, hashed: str) -> bool:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, pwd_context.verify, password, hashed)
