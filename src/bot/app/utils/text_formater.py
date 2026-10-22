import html


def format_moderation_message(
    chat_id: str,
    user_message: str,
    answer_text: str,
    edited: bool = False,
) -> str:
    user_block = (
        f"<b>Сообщение клиента:</b>\n"
        f"{html.escape(user_message)}\n\n"
        if user_message
        else ""
    )

    answer_title = (
        "Ответ AI (Измененный):"
        if edited
        else "Ответ AI:"
    )

    return (
        "💬 <b>Новый ответ на модерацию</b>\n\n"
        f'<b>Чат Avito:</b> <a href="https://www.avito.ru/profile/messenger/channel/'
        f'{html.escape(str(chat_id), quote=True)}">Открыть чат</a>\n\n'
        f"{user_block}"
        f"<b>{answer_title}</b>\n"
        f"{html.escape(answer_text)}"
    )