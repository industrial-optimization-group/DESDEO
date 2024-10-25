"""This module contains the functions for user authentication."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from desdeo.api import AuthConfig
from desdeo.api.db import get_db
from desdeo.api.db_models import User as UserModel
from desdeo.api.schema import User

router = APIRouter()


class Tokens(BaseModel):
    """A model for the authentication token."""

    access_token: str
    refresh_token: str
    token_type: str


# OAuth2PasswordBearer is a class that creates a dependency that will be used to get the token from the request.
# The token will be used to authenticate the user.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if a password matches a hash.

    Args:
        plain_password (str): the plain password.
        hashed_password (str): the hashed password.

    Returns:
        bool: whether the plain password matches the hashed one.
    """
    password_byte_enc = plain_password.encode("utf-8")

    return bcrypt.checkpw(password=password_byte_enc, hashed_password=hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """Hash a password.

    Args:
        password (str): the password to be hashed.

    Returns:
        str: the hashed password.
    """
    pwd_bytes = password.encode("utf-8")

    return bcrypt.hashpw(password=pwd_bytes, salt=bcrypt.gensalt()).decode("utf-8")


def get_user(db: Session, username: str) -> User | None:
    """Get the current user.

    Get the current user based on the username. If no user if found,
    return None.

    Args:
        db (Session): the database to be queried for the user.
        username (str): the username of the user.

    Returns:
        User | None: the User. If no user is found, returns None.
    """
    if user := db.query(UserModel).filter(UserModel.username == username).first():
        return user
    return None


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """Check if a user exists and the password is correct.

    Check if a user exists and the password is correct. If the user exists and the password
    is correct, returns the user.

    Args:
        db (Session): the database to query for the user.
        username (str): the username of the user.
        password (str): password set for the user.

    Returns:
        User | None: the User. If no user if found, returns None.
    """
    user = get_user(db, username)

    if not user or not verify_password(password, user.password_hash):
        return None

    return user


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
    algorithm: str = AuthConfig.authjwt_algorithm,
    secret_key: str = AuthConfig.authjwt_secret_key,
) -> UserModel:
    """Get the current user based on a JWT token.

    This function is a dependency for other functions that need to get the current user.

    Args:
        token (Annotated[str, Depends(oauth2_scheme)]): The authentication token.
        db (Annotated[Session, Depends(get_db)]): A database session.
        algorithm (str): the algorithm used to decode the JWT token.
            Defaults to `AuthConfig.authjwt_algorithm`.
        secret_key (str): the secret key used to decode the JWT token.
            Defaults to `AuthConfig.authjwt_secret_key`.

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
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        username: str = payload.get("sub")
        expire_time: datetime = payload.get("exp")

        if username is None or expire_time is None or expire_time < datetime.now(UTC).timestamp():
            raise credentials_exception

    except jwt.exceptions.ExpiredSignatureError:
        raise credentials_exception from None

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
        privilages=user.privileges,
        password_hash=user.password_hash,
    )


async def create_jwt_token(
    data: dict,
    expires_delta: timedelta,
    algorithm: str = AuthConfig.authjwt_algorithm,
    secret_key: str = AuthConfig.authjwt_secret_key,
) -> str:
    """Creates an JWT Token with `data` and `expire_delta`.

    Args:
        data (dict): The data to encode in the token.
        expires_delta (timedelta): The time after which the token will expire.
        algorithm (str): the algorithms to encode the JWT token.
            Defaults to `AuthConfig.authjwt_algorithm`.
        secret_key (str): the secret key used in encoding the JWT token.
            Defaults to `AuthConfig.authjwt_secret_key`.

    Returns:
        str: the JWT token.
    """
    data = data.copy()
    expire = datetime.utcnow() + expires_delta
    data.update({"exp": expire})
    return jwt.encode(data, secret_key, algorithm=algorithm)


async def create_access_token(data: dict, expiration_time: int = AuthConfig.authjwt_access_token_expires) -> str:
    """Creates a JWT access token.

    Creates a JWT access token with `data`, and an
    expiration time.

    Args:
        data (dict): the data to encode in the token.
        expiration_time (int): the expiration time of the access token
         in minutes. Defaults to `AuthConfig.authjwt_access_token_expires`.

    Returns:
        str: the JWT access token.
    """
    return await create_jwt_token(data, timedelta(minutes=expiration_time))


async def create_refresh_token(data: dict, expiration_time: int = AuthConfig.authjwt_refresh_token_expires) -> str:
    """Creates a JTW refresh token.

    Creates a JWT refresh token with `data and an expiration time.

    Args:
        data (dict): The data to encode in the token.
        expiration_time (int): the expiration time of the refresh token
         in minutes. Defaults to `AuthConfig.authjwt_refresh_token_expires`.

    Returns:
        str: the JWT refresh token.
    """
    refresh_token: str = await create_jwt_token(data, timedelta(minutes=expiration_time))

    return refresh_token


async def generate_tokens(data: dict) -> Tokens:
    """Generates a and refresh Tokens with `data`.

    Note:
        The expiration times of the tokens in defined in
        `AuthConfig`.

    Args:
        data (dict): The data to encode in the token.

    Returns:
        Tokens: the access and refresh tokens.
    """
    access_token = await create_access_token(data)
    refresh_token = await create_refresh_token(data)
    return Tokens(access_token=access_token, refresh_token=refresh_token, token_type="bearer")  # noqa: S106


@router.post("/token")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[Session, Depends(get_db)]
) -> Tokens:
    """Login to get an authentication token.

    Args:
        form_data (Annotated[OAuth2PasswordRequestForm, Depends()]):
            The form data to authenticate the user.
        db (Annotated[Session, Depends(get_db)]): The database of the session.

    Returns:
        Tokens: The authentication tokens.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await generate_tokens({"id": user.id, "sub": user.username})
