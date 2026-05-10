from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

def hash_password(password: str):
    password = password.strip()

    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password too long (max 72 bytes)")

    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain.strip(), hashed)