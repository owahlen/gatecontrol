import uvicorn
from fastapi import FastAPI

from app.api.config import config
from app.api.gate import gate
from app.api.index import index

app = FastAPI()
app.include_router(index, tags=['index'])
app.include_router(gate, prefix='/gate', tags=['gate'])

def init():
    if __name__ == "__main__":
        uvicorn.run(app, host=config.host, port=config.port)

init()
