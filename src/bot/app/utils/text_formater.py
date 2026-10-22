import html


def format_moderation_message(
    chat_id: str,
    user_message: str,
    answer_text: str,
    edited: bool = False,
) -> str:
    banner = (
        '✏️ <b>Ответ AI изменён - повторная модерация</b>\n\n'
        if edited
        else '💬 <b>Новый ответ на модерацию</b>\n\n'
    )
    user_block = (
        f'<b>Сообщение клиента:</b>\n{html.escape(user_message)}\n\n'
        if user_message
        else ''
    )

    answer_title = 'Измененный ответ:' if edited else 'Ответ AI:'

    return (
        f'{banner}'
        f'<b>Чат Avito:</b> <a href="https://www.avito.ru/profile/messenger/channel/'
        f'{html.escape(str(chat_id), quote=True)}">Открыть чат</a>\n\n'
        f'{user_block}'
        f'<b>{answer_title}</b>\n'
        f'{html.escape(answer_text)}'
    )
