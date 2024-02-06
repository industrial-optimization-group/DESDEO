"""The main FastAPI application for the DESDEO API."""
from fastapi import FastAPI

from desdeo.api.routers import NIMBUS

# from desdeo.api.db import Base

app = FastAPI()
# db = Base


app.include_router(NIMBUS.router)


@app.get("/")
async def root():
    """Just a simple hello world message."""
    return {"message": "Hello World"}
