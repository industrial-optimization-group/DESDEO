"""The main FastAPI application for the DESDEO API."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from desdeo.api.routers import NIMBUS, NAUTILUS_navigator, UserAuth, problems, test

app = FastAPI(
    title="DESDEO (fast)API",
    version="0.1.0",
    description="A rest API for the DESDEO framework.",
)

app.include_router(NIMBUS.router)
app.include_router(test.router)
app.include_router(UserAuth.router)
app.include_router(problems.router)
app.include_router(NAUTILUS_navigator.router)

origins = ["http://localhost", "http://localhost:8080", "*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict:
    """Just a simple hello world message."""
    return {"message": "Hello World!"}


if __name__ == "__main__":
    print("Starting server driectly from app.py")
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
