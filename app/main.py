import uvicorn
from fastapi import FastAPI

from app.api.gate import gate
from app.api.index import index

app = FastAPI()
app.include_router(index, tags=['index'])
app.include_router(gate, prefix='/gate', tags=['gate'])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

