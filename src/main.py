from fastapi import FastAPI

from src.api.routers import api_router
from src.core.settings import settings

app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    openapi_url=f"{settings.api_prefix}/openapi.json"
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    return {"message": "FastAPI Application"}
