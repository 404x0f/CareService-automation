from fastapi import APIRouter

from src.api.endpoints import avito_router

main_router = APIRouter()

main_router.include_router(avito_router, tags=["Avito"])