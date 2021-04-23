from fastapi import APIRouter
from starlette.responses import RedirectResponse

index = APIRouter()


@index.get('/')
async def redirect_to_gate():
    response = RedirectResponse(url='/gate')
    return response
