from fastapi import FastAPI

#from desdeo.api.db import Base

app = FastAPI()
#db = Base


@app.get("/")
async def root():
    return {"message": "Hello World"}
