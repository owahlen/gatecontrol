import uvicorn
from fastapi import FastAPI

from app.api.config import config
from app.api.gate_router import gate_router
from app.api.health_router import health_router
from app.api.index import index

app = FastAPI()
app.include_router(index, tags=['index'])
app.include_router(gate_router, prefix='/gate', tags=['gate'])
app.include_router(health_router, prefix='/health', tags=['health'])


def init():
    if __name__ == "__main__":
        uvicorn.run(app, host=config.host, port=int(config.port))

init()
