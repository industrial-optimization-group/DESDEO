"""This module contains the functions for user authentication."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import BaseModel
from sqlmodel import Session, select

from desdeo.api import SettingsConfig
from desdeo.api.db import get_session
from desdeo.api.models import User, UserPublic, UserRole

# AuthConfig
if SettingsConfig.debug:
    from desdeo.api import AuthDebugConfig

    AuthConfig = AuthDebugConfig
else:
    pass

router = APIRouter()


class Tokens(BaseModel):
    """A model for the authentication token."""

    access_token: str
    refresh_token: str
    token_type: str


# OAuth2PasswordBearer is a class that creates a dependency that will be used to get the token from the request.
# The token will be used to authenticate the user.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


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


def get_user(session: Session, username: str) -> User | None:
    """Get the current user.

    Get the current user based on the username. If no user if found,
    return None.

    Args:
        session (Session): database session.
        username (str): the username of the user.

    Returns:
        User | None: the User. If no user is found, returns None.
    """
    statement = select(User).where(User.username == username)
    return session.exec(statement).first()


def authenticate_user(session: Session, username: str, password: str) -> User | None:
    """Check if a user exists and the password is correct.

    Check if a user exists and the password is correct. If the user exists and the password
    is correct, returns the user.

    Args:
        session (Session): database session.
        username (str): the username of the user.
        password (str): password set for the user.

    Returns:
        User | None: the User. If no user if found, returns None.
    """
    user = get_user(session, username)

    if not user or not verify_password(password, user.password_hash):
        return None

    return user


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    """Get the current user based on a JWT token.

    This function is a dependency for other functions that need to get the current user.

    Args:
        token (Annotated[str, Depends(oauth2_scheme)]): The authentication token.
        session (Annotated[Session, Depends(get_db)]): A database session.

    Returns:
        User: The information of the current user.

    Raises:
        HTTPException: If the token is invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, AuthConfig.authjwt_secret_key, algorithms=[AuthConfig.authjwt_algorithm])
        username = payload.get("sub")
        expire_time: datetime = payload.get("exp")

        if username is None or expire_time is None or expire_time < datetime.now(UTC).timestamp():
            raise credentials_exception

    except ExpiredSignatureError:
        raise credentials_exception from None

    except JWTError:
        raise credentials_exception from JWTError

    user = get_user(session, username=username)

    if user is None:
        raise credentials_exception

    return user


def create_jwt_token(
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
    expire = datetime.now(UTC) + expires_delta
    data.update({"exp": expire, "jti": str(uuid.uuid4())})
    # jti adds an unique identifier so that life is easier

    return jwt.encode(data, secret_key, algorithm=algorithm)


def create_access_token(data: dict, expiration_time: int = AuthConfig.authjwt_access_token_expires) -> str:
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
    return create_jwt_token(data, timedelta(minutes=expiration_time))


def create_refresh_token(data: dict, expiration_time: int = AuthConfig.authjwt_refresh_token_expires) -> str:
    """Creates a JTW refresh token.

    Creates a JWT refresh token with `data and an expiration time.

    Args:
        data (dict): The data to encode in the token.
        expiration_time (int): the expiration time of the refresh token
         in minutes. Defaults to `AuthConfig.authjwt_refresh_token_expires`.

    Returns:
        str: the JWT refresh token.
    """
    refresh_token: str = create_jwt_token(data, timedelta(minutes=expiration_time))

    return refresh_token


def generate_tokens(data: dict) -> Tokens:
    """Generates a and refresh Tokens with `data`.

    Note:
        The expiration times of the tokens in defined in
        `AuthConfig`.

    Args:
        data (dict): The data to encode in the token.

    Returns:
        Tokens: the access and refresh tokens.
    """
    access_token = create_access_token(data)
    refresh_token = create_refresh_token(data)
    return Tokens(access_token=access_token, refresh_token=refresh_token, token_type="bearer")  # noqa: S106


def validate_refresh_token(
    refresh_token: str,
    session: Annotated[Session, Depends(get_session)],
    algorithm: str = AuthConfig.authjwt_algorithm,
    secret_key: str = AuthConfig.authjwt_secret_key,
) -> User:
    """Validate a refresh token and return the associated user if valid.

    Args:
        refresh_token (str): The refresh token to validate.
        session (Annotated[Session, Depends(get_db)]): The database session.
        algorithm (str): the algorithm used to decode the JWT token.
            Defaults to `AuthConfig.authjwt_algorithm`.
        secret_key (str): the secret key used to decode the JWT token.
            Defaults to `AuthConfig.authjwt_secret_key`.

    Returns:
        UserModel: The user associated with the valid refresh token.

    Raises:
        HTTPException: If the refresh token is invalid or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode the refresh token
        payload = jwt.decode(refresh_token, secret_key, algorithms=[algorithm])
        username = payload.get("sub")
        expire_time: datetime = payload.get("exp")

    except Exception as _:
        raise credentials_exception from None

    if username is None or expire_time is None or expire_time < datetime.now(UTC).timestamp():
        raise credentials_exception

    # Validate the user from the database
    user = get_user(session, username=username)
    if user is None:
        raise credentials_exception

    return user


def add_user_to_database(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    role: UserRole,
    session: Annotated[Session, Depends(get_session)],
) -> None:
    """Add a user to database.

    Args:
        form_data Annotated[OAuth2PasswordRequestForm, Depends()]: form with username and password to be added to database
        role UserRole: Role of the user to be added to the database
        session Annotated[Session, Depends(get_session)]: database session

    Returns:
        None

    Raises:
        HTTPException: If username already is in the database or if adding the user to the database failed.
    """

    username = form_data.username
    password = form_data.password

    # Check if a user with requested username is already in the database
    if get_user(session=session, username=username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken.",
        )

    # Create the user model and put it into database
    new_user = User(
        username=username,
        password_hash=get_password_hash(
            password=password,
        ),
        role=role,
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    # Verify that the user actually is in the database
    if not get_user(session=session, username=username):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add user into database.",
        )


@router.get("/user_info")
def get_current_user_info(user: Annotated[User, Depends(get_current_user)]) -> UserPublic:
    """Return information about the current user.

    Args:
        user (Annotated[User, Depends): user dependency, handled by `get_current_user`.

    Returns:
        UserPublic: public information about the current user.
    """
    return user


@router.post("/login", response_model=Tokens)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)],
    cookie_max_age: int = AuthConfig.authjwt_refresh_token_expires,
):
    """Login to get an authentication token.

    Return an access token in the response and a cookie storing a refresh token.

    Args:
        form_data (Annotated[OAuth2PasswordRequestForm, Depends()]):
            The form data to authenticate the user.
        session (Annotated[Session, Depends(get_db)]): The database session.
        cookie_max_age (int): the lifetime of the cookie storing the refresh token.

    """
    user = authenticate_user(session, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tokens = generate_tokens({"id": user.id, "sub": user.username})

    response = JSONResponse(content={"access_token": tokens.access_token})
    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,  # HTTP only cookie, more secure than storing the refresh token in the frontend code.
        secure=False,  # allow http
        samesite="lax",  # cross-origin requests
        max_age=cookie_max_age * 60,  # convert to minutes
        path="/",
    )

    return response


@router.post("/logout")
def logout() -> JSONResponse:
    """Log the current user out. Deletes the refresh token that was set by logging in.

    Args:
        None

    Returns:
        JSONResponse: A response in which the cookies are deleted

    """
    response = JSONResponse(content={"message": "logged out"}, status_code=status.HTTP_200_OK)
    response.delete_cookie("refresh_token")
    return response


@router.post("/refresh")
def refresh_access_token(
    request: Response,
    session: Annotated[Session, Depends(get_session)],
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    """Refresh the access token using the refresh token stored in the cookie.

    Args:
        request (Request): The request containing the cookie.
        session (Annotated[Session, Depends(get_db)]): the database session.
        refresh_token (Annotated[Str | None, Cookie()]): the refresh
            token, which is fetched from a cookie included in the response.

    Returns:
        dict: A dictionary containing the new access token.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = validate_refresh_token(refresh_token, session)

    # Generate a new access token for the user
    access_token = create_access_token({"id": user.id, "sub": user.username})

    return {"access_token": access_token}


@router.post("/add_new_dm")
def add_new_dm(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)],
) -> JSONResponse:
    """Add a new user of the role Decision Maker to the database. Requires no login.

    Args:
        form_data (Annotated[OAuth2PasswordRequestForm, Depends()]): The user credentials to add to the database.
        session (Annotated[Session, Depends(get_session)]): the database session.

    Returns:
        JSONResponse: A JSON response

    Raises:
        HTTPException: if username is already in use or if saving to the database fails for some reason.
    """

    add_user_to_database(
        form_data=form_data,
        role=UserRole.dm,
        session=session,
    )

    return JSONResponse(
        content={"message": 'User with role "decision maker" created.'},
        status_code=status.HTTP_201_CREATED,
    )


@router.post("/add_new_analyst")
def add_new_analyst(
    user: Annotated[User, Depends(get_current_user)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)],
) -> JSONResponse:
    """Add a new user of the role Analyst to the database. Requires a logged in analyst or an admin

    Args:
        user Annotated[User, Depends(get_current_user)]: Logged in user with the role "analyst" or "admin".
        form_data (Annotated[OAuth2PasswordRequestForm, Depends()]): The user credentials to add to the database.
        session (Annotated[Session, Depends(get_session)]): the database session.

    Returns:
        JSONResponse: A JSON response

    Raises:
        HTTPException: if the logged in user is not an analyst or an admin or if
        username is already in use or if saving to the database fails for some reason.

    """

    # Check if the user who tries to create the user is either an analyst or an admin.
    if not (user.role == UserRole.analyst or user.role == UserRole.admin):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Logged in user has insufficient rights.",
        )

    add_user_to_database(
        form_data=form_data,
        role=UserRole.analyst,
        session=session,
    )

    return JSONResponse(
        content={"message": 'User with role "analyst" created.'},
        status_code=status.HTTP_201_CREATED,
    )
