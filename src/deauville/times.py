from datetime import date, datetime, timedelta

from .errors import InvalidError

FESTIVAL_DAY_CHANGE = timedelta(hours=6)
GAP = timedelta(minutes=30)
MIN_MINUTES = 1
MAX_MINUTES = 360


def festival_day_of(moment: datetime) -> date:
    return (moment - FESTIVAL_DAY_CHANGE).date()


def too_close(start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
    return start1 < end2 + GAP and start2 < end1 + GAP


def parse_day(text: str) -> date:
    try:
        return date.fromisoformat(str(text).strip())
    except ValueError:
        raise InvalidError(f"'{text.strip()}' is not a day, use YYYY-MM-DD.") from None


def parse_moment(text: str) -> datetime:
    try:
        moment = datetime.fromisoformat(str(text).strip())
    except ValueError:
        raise InvalidError(f"'{text.strip()}' is not a moment, use YYYY-MM-DDTHH:MM.") from None
    if moment.tzinfo is not None:
        raise InvalidError(f"'{text.strip()}': give a local time without time zone.")
    return moment


def parse_minutes(value: object) -> int:
    try:
        if isinstance(value, bool):
            raise ValueError
        return int(str(value).strip())
    except ValueError:
        raise InvalidError(f"'{value}' is not a number of minutes.") from None
