"""Запускает таймерную обработку чатов отдельным worker-процессом."""

import asyncio
import logging
from uuid import UUID

from src.core.dependencies import session_maker
from src.crud.chats import claim_due_chats, schedule_retry
from src.services.reply_workflow import process_chat


logger = logging.getLogger(__name__)


async def process_safely(chat_id: UUID) -> None:
    """Обработать один чат, не останавливая worker при ошибке."""
    try:
        await process_chat(chat_id)
    except Exception:
        logger.exception("Could not process chat %s", chat_id)
        async with session_maker() as session, session.begin():
            await schedule_retry(session, chat_id)


async def run_worker() -> None:
    """Раз в секунду захватывать чаты с истёкшим waiting_until."""
    while True:
        try:
            # В одной транзакции забираем чаты и обнуляем их таймер.
            async with session_maker() as session, session.begin():
                chat_ids = await claim_due_chats(session)
            await asyncio.gather(*(process_safely(chat_id) for chat_id in chat_ids))
        except Exception:
            logger.exception("Worker iteration failed")
        await asyncio.sleep(1)


async def main() -> None:
    """Запустить только worker; Telegram polling живёт в src.bot.main."""
    logging.basicConfig(level=logging.INFO)
    await run_worker()


if __name__ == "__main__":
    # Команда `python -m src.worker` начинает асинхронный цикл.
    asyncio.run(main())
