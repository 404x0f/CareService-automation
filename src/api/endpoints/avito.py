import logging
from typing import Any

from fastapi import APIRouter

from src.core.dependencies import SessionDep
from src.schemas.avito_webhook import AvitoMessageEvent
from src.services.avito_webhook import save_webhook_message

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/avito",
)

@router.post("/webhook")
async def avito_webhook(
    data: dict[str, Any],
    session: SessionDep,
):
    logger.info("AVITO WEBHOOK RECEIVED: %s", data)
    event = AvitoMessageEvent.from_webhook(data)
    if event is None:
        return {"ok": True, "status": "ignored"}

    status = await save_webhook_message(session, event)
    return {"ok": True, "status": status}
