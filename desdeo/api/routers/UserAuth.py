"""This module contains the functions for user authentication."""
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Dict

from desdeo.api import AuthConfig
from desdeo.api.db import get_db
from desdeo.api.db_models import User as UserModel
from desdeo.api.schema import User

router = APIRouter()

SECRET_KEY = AuthConfig.authjwt_secret_key
ALGORITHM = AuthConfig.authjwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = AuthConfig.authjwt_access_token_expires
SALT = bcrypt.gensalt()

REFRESH_TOKEN_EXPIRE_MINUTES = AuthConfig.authjwt_refresh_token_expires

class Token(BaseModel):
    """A model for the authentication token."""

    access_token: str
    refresh_token: str
    token_type: str


# OAuth2PasswordBearer is a class that creates a dependency that will be used to get the token from the request.
# The token will be used to authenticate the user.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, hashed_password):
    """Check if a password matches a hash."""
    password_byte_enc = plain_password.encode("utf-8")
    return bcrypt.checkpw(password=password_byte_enc, hashed_password=hashed_password.encode("utf-8"))


def get_password_hash(password):
    """Hash a password."""
    pwd_bytes = password.encode("utf-8")
    return bcrypt.hashpw(password=pwd_bytes, salt=SALT).decode("utf-8")


def get_user(db: Session, username: str):
    """Get a user from the database."""
    return db.query(UserModel).filter(UserModel.username == username).first()


def authenticate_user(db: Session, username: str, password: str):
    """Check if a user exists and the password is correct."""
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[Session, Depends(get_db)]
) -> UserModel:
    """Get the current user. This function is a dependency for other functions that need to get the current user.

    Args:
        token (Annotated[str, Depends(oauth2_scheme)]): The authentication token.
        db (Annotated[Session, Depends(get_db)]): A database session.

    Returns:
        User: The current user.

    Raises:
        HTTPException: If the token is invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        expire_time: datetime = payload.get("exp")

        if username is None or expire_time is None or expire_time < datetime.now(UTC).timestamp():
            raise credentials_exception
    except jwt.exceptions.ExpiredSignatureError:
        raise credentials_exception
    except JWTError:
        raise credentials_exception from JWTError
    user = get_user(db, username=username)
    if user is None:
        raise credentials_exception
    return User(
        username=user.username,
        index=user.id,
        role=user.role,
        user_group=user.user_group if user.user_group else "",
        privilages=user.privilages,
        password_hash=user.password_hash,
    )

async def create_jwt_token(data: dict, expires_delta: timedelta) -> str:
    """Creates an JWT Token with `data` and `expire_delta`

    Args:
        data (dict): The data to encode in the token.
        expires_delta (timedelta): The time after which the token will expire.

    Returns:
        str: JWT token
    """
    data = data.copy()
    expire = datetime.utcnow() + expires_delta
    data.update({"exp": expire})
    encoded_jwt = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def create_access_token(data: Dict) -> str:
    """Creates an JWT Access Token with `data` and expires after `ACCESS_TOKEN_EXPIRE_MINUTES`

    Args:
        data (dict): The data to encode in the token.

    Returns:
        str: JWT access token
    """
    return await create_jwt_token(data, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

async def create_refresh_token(data: Dict) -> str:
    """Creates an Refresh Token with user `data`

    Args:
        data (dict): The data to encode in the token.

    Returns:
        str: JWT refresh token
    """
    refresh_token: str = await create_jwt_token(data, timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES))

    return refresh_token

async def generate_tokens(data: Dict, refresh_token_needed: bool = False) -> Token:
    """Generates Access and Refresh Token with `data`

    Args:
        data (dict): The data to encode in the token.
        refresh_token_needed (bool, optional): Indicate whether the refresh token is generated. Defaults to False

    Returns:
        Token: a Token class object
    """
    access_token: str = await create_access_token(data)
    refresh_token = ''
    if refresh_token_needed:
        refresh_token: str = await create_refresh_token(data)
    return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

@router.post("/token")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[Session, Depends(get_db)]
) -> Token:
    """Login to get an authentication token.

    Args:
        form_data (Annotated[OAuth2PasswordRequestForm, Depends()]): The form data to authenticate the user.
        db (Annotated[Session, Depends(get_db)]): The database session.

    Returns:
        Token: The authentication token.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await generate_tokens({"id": user.id, "sub": user.username})

