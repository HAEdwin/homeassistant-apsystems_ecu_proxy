"""Helper functions."""

from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import SummationPeriod


def slugify(value: str) -> str:
    """Slugify value."""
    return value.replace(" ", "_").lower()


def add_local_timezone(hass: HomeAssistant, timestamp: datetime):
    """Add a timezone by timezone name to timezone unaware timestamp."""
    return timestamp.replace(tzinfo=dt_util.get_time_zone(hass.config.time_zone))


def get_period_start_timestamp(
    summation_period: SummationPeriod, timestamp: datetime
) -> datetime:
    """Get timestamp of start of summation period."""
    if summation_period == SummationPeriod.HOURLY:
        return timestamp.replace(minute=0, second=0)
    if summation_period == SummationPeriod.DAILY:
        return timestamp.replace(hour=0, minute=0, second=0)
    if summation_period == SummationPeriod.WEEKLY:
        return datetime.strptime(
            f"{timestamp.year}-{timestamp.isocalendar()[1]}-1", "%Y-%W-%w"
        )
    if summation_period == SummationPeriod.MONTHLY:
        return timestamp.replace(day=1, hour=0, minute=0, second=0)
    if summation_period == SummationPeriod.YEARLY:
        return timestamp.replace(month=1, day=1, hour=0, minute=0, second=0)
    return datetime.fromtimestamp(0)


def has_changed_period(
    summation_period: SummationPeriod,
    base_timestamp: datetime,
    timestamp: datetime,
) -> bool:
    """Return if period of interval has exceeded."""
    if (
        (
            summation_period == SummationPeriod.HOURLY
            and base_timestamp.hour != timestamp.hour
        )
        or (
            summation_period == SummationPeriod.DAILY
            and base_timestamp.day != timestamp.day
        )
        or (
            summation_period == SummationPeriod.WEEKLY
            and base_timestamp.isocalendar()[1] != timestamp.isocalendar()[1]
        )
        or (
            summation_period == SummationPeriod.MONTHLY
            and base_timestamp.month != timestamp.month
        )
        or (
            summation_period == SummationPeriod.YEARLY
            and base_timestamp.year != timestamp.year
        )
    ):
        return True
    return False
