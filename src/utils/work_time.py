# from datetime import datetime, time
# from zoneinfo import ZoneInfo

# MSK = ZoneInfo("Europe/Moscow")


def is_working_time() -> bool:
    # На время тестов ии не может писать в чат самостоятельно.

    # now = datetime.now(MSK)

    # if now.weekday() >= 5:
    #     return False

    # work_start = time(9, 0)
    # work_end = time(18, 0)

    # return work_start <= now.time() < work_end
    return True
