"""The main FastAPI application for the DESDEO API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from desdeo.api.config import AuthDebugConfig, SettingsConfig
from desdeo.api.routers import (
    generic,
    nimbus,
    problem,
    reference_point_method,
    session,
    user_authentication,
    utopia,
)

if SettingsConfig.debug:
    # debug and development stuff

    app = FastAPI(
        title="DESDEO (fast)API",
        version="0.1.0",
        description="A rest API for the DESDEO framework.",
    )

    app.include_router(user_authentication.router)
    app.include_router(problem.router)
    app.include_router(session.router)
    app.include_router(reference_point_method.router)
    app.include_router(nimbus.router)
    app.include_router(generic.router)
    app.include_router(utopia.router)

    origins = AuthDebugConfig.cors_origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

else:
    # deployment stuff
    pass
