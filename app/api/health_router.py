from fastapi import APIRouter

from app.api.health_service import HealthService
from app.api.models import Health

health_router = APIRouter()
health_service = HealthService()


@health_router.get('', response_model=Health)
async def get_health():
    health = await health_service.get_health()
    return health
